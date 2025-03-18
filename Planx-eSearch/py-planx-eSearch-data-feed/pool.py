import os
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
from config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH,
)
# 配置

SESSION_DIR = "./sessions"
URL_FILE = "urls.txt"
LOG_DIR = "./log"

# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(session_file):
    """为每个 session 文件配置独立的日志"""
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

        # 初始化池
        for session in session_files:
            self.pool.put(session)

    def _get_next_url(self):
        """线程安全地读取并删除文件中的第一个 URL"""
        with self.lock:
            if not os.path.exists(self.url_file) or os.stat(self.url_file).st_size == 0:
                return None
            with open(self.url_file, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            if not urls:
                return None
            url = urls[0]  # 取第一个 URL
            # 重写文件，移除已读取的 URL
            with open(self.url_file, "w", encoding="utf-8") as f:
                f.write("\n".join(urls[1:]) + "\n" if len(urls) > 1 else "")
            return url

    async def worker(self, session_file: str):
        """工作进程逻辑"""
        logger = setup_logger(session_file)  # session 专用日志
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
                crawl_result = await join_and_fetch_group_info(client, url, messageNum=30, logger=logger)
                # 验证爬取结果
                if "doc_id" not in crawl_result or not crawl_result["doc_id"]:
                    logger.error("爬取结果中 doc_id 为空")
                    
                if "content" not in crawl_result or not crawl_result["content"]:
                    logger.error("爬取结果中 content 为空")
                
                if crawl_result:
                    # 第二步：准备分块数据
                    split_data = {
                        "doc_id": crawl_result["doc_id"],  # 从爬取结果中获取 doc_id
                        "content": crawl_result["content"],
                        "max_block_size": 7000
                    }

                    split_content_into_blocks(split_data, logger=logger)
                    logger.info(f"Successfully processed {url}")
                else:
                    logger.error(f"Failed to process {url}")
                    self.pool.put(session_file)
                    break

        except FloodWaitError as e:
            wait_time = e.seconds or random.uniform(60, 120)
            logger.warning(f"FloodWaitError for {session_file}, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            self.pool.put(session_file)
        except Exception as e:
            logger.error(f"Error in worker {session_file}: {e}")
            self.pool.put(session_file)
        finally:
            await client.disconnect()

    def start_pool(self):
        """启动连接池"""
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
    # 主进程日志
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