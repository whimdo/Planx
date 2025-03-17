import asyncio
import json
import socks
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetHistoryRequest
from telethon.errors import UserAlreadyParticipantError, FloodWaitError
from generateKeyID import normalize_url, url_to_unique_id
import logging
import base64
from io import BytesIO
from config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE,
    PROXY_HOST, PROXY_PORT,
    MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_COLLECTION,
    LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_FILEMODE
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from configurations.kafka_config import KafkaConfig
from mongoUtils.utils import MongoDBHandler
from kafkaUtils.utils import KafkaClient

# # 时间频率设置（集中管理）
# RATE_LIMIT_CONFIG = {
#     "REQUEST_INTERVAL": 5.0,       # 每次 API 请求之间的间隔（秒）
#     "MESSAGE_BATCH_SIZE": 50,      # 每次获取的消息条数（最大 100，这里设为 50 以降低负载）
#     "BATCH_INTERVAL": 10.0,        # 每批消息获取之间的间隔（秒）
#     "JOIN_GROUP_DELAY": 15.0,      # 加入群组后的等待时间（秒）
#     "RETRY_DELAY": 60.0,           # 遇到 FloodWaitError 后的默认重试等待时间（秒）
#     "MAX_MESSAGES_PER_REQUEST": 100  # Telegram API 单次最大消息数限制
# }

RATE_LIMIT_CONFIG = {
    "REQUEST_INTERVAL": 2.0,    # 降低到 2 秒
    "MESSAGE_BATCH_SIZE": 100,  # 提高到 100 条
    "BATCH_INTERVAL": 3.0,     # 降低到 3 秒
    "JOIN_GROUP_DELAY": 5.0,   # 降低到 5 秒
    "RETRY_DELAY": 30.0,       # 降低到 30 秒
    "MAX_MESSAGES_PER_REQUEST": 100
}

# 日志设置
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    filename=os.path.join(LOG_DIR, LOG_FILE),
    filemode=LOG_FILEMODE
)
logger = logging.getLogger(__name__)

# 代理设置
proxy = (socks.SOCKS5, PROXY_HOST, PROXY_PORT)

# 创建 Telegram 客户端
client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH, proxy=proxy)

async def join_and_fetch_group_info(group_url, messageNum: int = None):
    try:
        logger.info(f"处理群组: {group_url}")
        await client.start(phone=lambda: TELEGRAM_PHONE)
        await asyncio.sleep(RATE_LIMIT_CONFIG["REQUEST_INTERVAL"])

        # 清理 URL
        if '?' in group_url:
            group_url = group_url.split('?')[0]
        group_handle = None
        if '/+' in group_url:
            invite_hash = group_url.split('/+')[1]
            try:
                updates = await client(ImportChatInviteRequest(invite_hash))
                group_entity = updates.chats[0]
            except UserAlreadyParticipantError:
                group_entity = await client.get_entity(group_url)
            group_handle = group_entity.username or f"private_{invite_hash[:8]}"
        else:
            group_handle = group_url.split('t.me/')[1]
            group_entity = await client.get_entity('@' + group_handle)

        await asyncio.sleep(RATE_LIMIT_CONFIG["JOIN_GROUP_DELAY"])

        group_type = "channel" if group_entity.broadcast else "group"
        group_name = group_entity.title
        full_channel = await client(GetFullChannelRequest(channel=group_entity))
        member_count = full_channel.full_chat.participants_count
        await asyncio.sleep(RATE_LIMIT_CONFIG["REQUEST_INTERVAL"])

        messages_str = ""
        if messageNum is not None:
            total_messages = []
            offset_id = 0
            remaining = messageNum
            while remaining > 0:
                batch_size = min(remaining, RATE_LIMIT_CONFIG["MESSAGE_BATCH_SIZE"])
                try:
                    messages = await client(GetHistoryRequest(
                        peer=group_entity,
                        limit=batch_size,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    if not messages.messages:
                        break
                    total_messages.extend(messages.messages)
                    offset_id = messages.messages[-1].id
                    remaining -= batch_size
                    await asyncio.sleep(RATE_LIMIT_CONFIG["BATCH_INTERVAL"])
                except FloodWaitError as e:
                    wait_time = e.seconds if e.seconds else RATE_LIMIT_CONFIG["RETRY_DELAY"]
                    logger.warning(f"FloodWaitError: 等待 {wait_time} 秒")
                    await asyncio.sleep(wait_time)
            messages_str = " ".join([msg.message for msg in total_messages if msg.message])

        avatar_base64 = None
        try:
            avatar_bytes = await client.download_profile_photo(group_entity, file=BytesIO())
            if avatar_bytes:
                avatar_bytes.seek(0)
                avatar_base64 = base64.b64encode(avatar_bytes.read()).decode('utf-8')
        except Exception as e:
            logger.warning(f"获取头像失败: {e}")

        keyid = url_to_unique_id(normalize_url(group_url), 16)
        result = {
            "doc_id": keyid,
            "type": group_type,
            "name": group_name,
            "member_count": member_count,
            "url": group_url,
            "avatar": avatar_base64,
            "messages": messages_str
        }
        result1 = {"doc_id": keyid, "content": messages_str}

        mongo = MongoDBHandler(host=MONGO_HOST, port=MONGO_PORT, database=MONGO_DB, collection=MONGO_COLLECTION)
        del result["messages"]
        mongo.insert_data(result)
        mongo.close()

        return result1

    except Exception as e:
        logger.error(f"处理 {group_url} 失败: {e}")
        return None

def split_content_into_blocks(data, max_block_size=7000):
    input_doc_id = data.get("doc_id", "")
    content = data.get("content", "")
    if not content:
        return {"doc_id": input_doc_id, "total_blocks": 0, "blocks": []}
    blocks = []
    block_id = 1
    for i in range(0, len(content), max_block_size):
        block_content = content[i:i + max_block_size]
        blocks.append({"block_id": block_id, "content": block_content})
        block_id += 1
    result = {"doc_id": input_doc_id, "total_blocks": block_id - 1, "blocks": blocks}
    kafka = KafkaClient()
    kafka.initialize_producer()
    kafka.send_message(KafkaConfig.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS, result)
    kafka.close()
    return result

async def process_urls_in_batches(urls, batch_size=50):
    total_urls = len(urls)
    logger.info(f"总共有 {total_urls} 个 URL 需要处理")
    processed_urls = set()  # 记录已处理的 URL

    # 从文件中恢复进度（如果上次中断）
    progress_file = "processed_urls.txt"
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            processed_urls = set(line.strip() for line in f if line.strip())
        logger.info(f"已恢复 {len(processed_urls)} 个已处理 URL")

    for i in range(0, total_urls, batch_size):
        batch = urls[i:i + batch_size]
        tasks = []
        for url in batch:
            if url not in processed_urls:
                tasks.append(join_and_fetch_group_info(url, 30))  # 每组抓取 30 条消息

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for url, result in zip(batch, results):
                if result and not isinstance(result, Exception):
                    split_content_into_blocks(result)
                    processed_urls.add(url)
                    # 记录进度
                    with open(progress_file, "a", encoding="utf-8") as f:
                        f.write(f"{url}\n")
                else:
                    logger.error(f"跳过 {url}，处理结果: {result}")
            logger.info(f"完成批次 {i // batch_size + 1}，已处理 {len(processed_urls)}/{total_urls}")
            await asyncio.sleep(60)  # 每批次间隔 60 秒

async def main():
    # 读取 URL 文件
    with open("group_urls.txt", "r", encoding="utf-8") as f:
        group_urls = [line.strip() for line in f if line.strip()]
    
    # 批量处理
    await process_urls_in_batches(group_urls, batch_size=50)

if __name__ == "__main__":
    asyncio.run(main())
