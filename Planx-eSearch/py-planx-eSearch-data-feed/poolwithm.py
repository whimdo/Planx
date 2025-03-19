import os
import sys
import asyncio
import logging
import multiprocessing as mp
from queue import Empty
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from filelock import FileLock
import random
import time
from typing import List
from crawlerWithLimitPool import join_and_fetch_group_info, split_content_into_blocks
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH

# 配置
SESSION_DIR = "./sessions"
URL_FILE = "url.txt"
LOG_DIR = "./log"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(session_file):
    session_name = os.path.basename(session_file).replace('.session', '')
    log_file = os.path.join(LOG_DIR, f"{session_name}.log")
    logger = logging.getLogger(session_name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(handler)
    return logger

class TelegramPool:
    def __init__(self, session_files: List[str], url_file: str):
        self.pool = mp.Queue()
        self.session_files = session_files
        self.url_file = url_file
        self.lock = FileLock(f"{url_file}.lock")
        # 等待队列，用于 Monitor 管理 FloodWaitError
        self.wait_queue = mp.Queue()

        for session in session_files:
            self.pool.put(session)

        # 启动 Monitor 进程
        self.monitor_process = mp.Process(target=self.monitor, daemon=True)
        self.monitor_process.start()

    def _get_next_url(self):
        with self.lock:
            if not os.path.exists(self.url_file) or os.stat(self.url_file).st_size == 0:
                return None
            with open(self.url_file, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            if not urls:
                return None
            url = urls[0]
            with open(self.url_file, "w", encoding="utf-8") as f:
                f.write("\n".join(urls[1:]) + "\n" if len(urls) > 1 else "")
            return url

    def monitor(self):
        """Monitor 进程：管理 FloodWaitError 的等待"""
        wait_tasks = []  # 存储 (session_file, end_time)
        monitor_logger = logging.getLogger("monitor")
        monitor_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(LOG_DIR, "monitor.log"), encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        monitor_logger.addHandler(handler)

        while True:
            # 一次性读取 wait_queue 中的所有数据
            new_tasks = 0
            while True:
                try:
                    session_file, wait_time = self.wait_queue.get_nowait()
                    end_time = time.time() + wait_time
                    wait_tasks.append((session_file, end_time))
                    new_tasks += 1
                    monitor_logger.info(f"Received {session_file} with wait time {wait_time}s")
                except Empty:
                    break  # 队列为空，退出内层循环
            if new_tasks > 0:
                monitor_logger.info(f"Processed {new_tasks} new tasks from wait_queue")

            # 检查是否有任务等待完成
            current_time = time.time()
            completed = []
            for session_file, end_time in wait_tasks:
                if current_time >= end_time:
                    monitor_logger.info(f"FloodWait completed for {session_file}, returning to pool")
                    self.pool.put(session_file)
                    completed.append((session_file, end_time))

            # 移除已完成的任务
            for task in completed:
                wait_tasks.remove(task)
            if completed:
                monitor_logger.info(f"Completed {len(completed)} tasks, remaining {len(wait_tasks)} tasks")

            # 每 10 秒检查一次
            time.sleep(30)

    async def worker(self, session_file: str):
        logger = setup_logger(session_file)
        phone_number = os.path.basename(session_file).replace('.session', '')
        client = TelegramClient(session_file, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        try:
            await client.start(phone=lambda: phone_number)
            while True:
                url = self._get_next_url()
                if not url:
                    logger.info(f"No more URLs for {session_file}, returning to pool")
                    self.pool.put(session_file)
                    break

                logger.info(f"Processing {url} with {session_file} (phone: {phone_number})")
                crawl_result = await join_and_fetch_group_info(client, url, None, logger=logger)
                if "doc_id" not in crawl_result or not crawl_result["doc_id"]:
                    logger.error("爬取结果中 doc_id 为空")
                    
                if "content" not in crawl_result or not crawl_result["content"]:
                    logger.error("爬取结果中 content 为空")
                
                if crawl_result:
                    split_data = {
                        "doc_id": crawl_result["doc_id"],
                        "content": crawl_result["content"],
                        "max_block_size": 5000
                    }
                    split_content_into_blocks(split_data, logger=logger)
                    logger.info(f"Successfully processed {url}")
                else:
                    logger.error(f"Failed to process {url}")
                    self.pool.put(session_file)
                    break

        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"FloodWaitError for {session_file}, delegating to monitor with wait time {wait_time}s")
            # 交给 Monitor 管理等待
            self.wait_queue.put((session_file, wait_time))
            return  # 立即终止进程
        except Exception as e:
            logger.error(f"Error in worker {session_file}: {e}")
            self.pool.put(session_file)
        finally:
            await client.disconnect()

    def start_pool(self):
        processes = {}
        main_logger = logging.getLogger(__name__)
        main_logger.info("Starting Telegram connection pool")

        while True:
            for pid in list(processes.keys()):
                if not processes[pid].is_alive():
                    processes.pop(pid)

            while not self.pool.empty() and len(processes) < len(self.session_files):
                try:
                    session_file = self.pool.get_nowait()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    process = mp.Process(
                        target=lambda: loop.run_until_complete(self.worker(session_file))
                    )
                    process.start()
                    processes[process.pid] = process
                    main_logger.info(f"Started process {process.pid} for {session_file}")
                except Empty:
                    break

            time.sleep(5)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    main_logger = logging.getLogger(__name__)

    session_files = [os.path.join(SESSION_DIR, f) for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not session_files:
        main_logger.error("No .session files found in ./sessions directory")
        return

    main_logger.info(f"Found {len(session_files)} session files")
    pool = TelegramPool(session_files, URL_FILE)
    pool.start_pool()

if __name__ == "__main__":
    main()