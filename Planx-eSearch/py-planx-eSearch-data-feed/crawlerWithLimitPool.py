import asyncio
import json
import socks
import os
import sys
import random
import logging
import base64
from io import BytesIO
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetHistoryRequest
from telethon.errors import UserAlreadyParticipantError, FloodWaitError
from generateKeyID import normalize_url, url_to_unique_id

# 配置路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from configurations.kafka_config import KafkaConfig
from mongoUtils.utils import MongoDBHandler
from kafkaUtils.utils import KafkaClient
from config import (
    MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_COLLECTION,
)

# 时间频率设置（集中管理，添加随机性）
RATE_LIMIT_CONFIG = {
    "REQUEST_INTERVAL": (3.0, 7.0),    # 随机 3-7 秒
    "MESSAGE_BATCH_SIZE": (20, 50),     # 随机 20-50 条
    "BATCH_INTERVAL": (5.0, 15.0),      # 随机 5-15 秒
    "JOIN_GROUP_DELAY": (10.0, 20.0),   # 随机 10-20 秒
    "RETRY_DELAY": (30.0, 90.0),        # 随机 30-90 秒
    "MAX_MESSAGES_PER_REQUEST": 100     # Telegram API 单次最大消息数限制
}

# 日志设置
# 配置日志，固定输出到 ./log/crawler.log
LOG_DIR = "./log"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

crawler_logger = logging.getLogger('crawler')
crawler_logger.setLevel(logging.INFO)
if crawler_logger.handlers:  # 清除已有处理器，避免重复日志
    crawler_logger.handlers.clear()
handler = logging.FileHandler(os.path.join(LOG_DIR, "crawler.log"), encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
crawler_logger.addHandler(handler)
crawler_logger.propagate = False  # 禁用传播

# 创建 Telegram 客户端
async def join_and_fetch_group_info(client, group_url, messageNum: int = None, logger=None):
    # 使用固定的 crawler_logger，而不是传入的 logger
    try:
        crawler_logger.info("已成功登录")
        await asyncio.sleep(random.uniform(*RATE_LIMIT_CONFIG["REQUEST_INTERVAL"]))

        group_entity = None
        group_handle = None
        if '/+' in group_url:
            invite_hash = group_url.split('/+')[1]
            crawler_logger.debug(f"处理私密邀请链接: hash={invite_hash}")
            try:
                updates = await client(ImportChatInviteRequest(invite_hash))
                group_entity = updates.chats[0]
                crawler_logger.info(f"通过邀请链接成功加入群组: {invite_hash}")
            except UserAlreadyParticipantError:
                crawler_logger.info(f"用户已加入群组，尝试直接获取实体")
                group_entity = await client.get_entity(invite_hash)
            group_handle = group_entity.username or f"private_{invite_hash[:8]}"
        else:
            group_handle = group_url.split('t.me/')[-1].strip('/')
            crawler_logger.debug(f"处理公开链接: @{group_handle}")
            group_entity = await client.get_entity('@' + group_handle)
            crawler_logger.info(f"获取群组实体成功: {group_handle}")

        await asyncio.sleep(random.uniform(*RATE_LIMIT_CONFIG["JOIN_GROUP_DELAY"]))
        crawler_logger.info(f"已成功加入 {group_handle}")

        group_type = "channel" if group_entity.broadcast else "group"
        group_name = group_entity.title
        full_channel = await client(GetFullChannelRequest(channel=group_entity))
        member_count = full_channel.full_chat.participants_count
        await asyncio.sleep(random.uniform(*RATE_LIMIT_CONFIG["REQUEST_INTERVAL"]))

        messages_str = ""
        if messageNum is not None:
            crawler_logger.info(f"获取指定数量消息: {messageNum}")
            remaining = min(messageNum, RATE_LIMIT_CONFIG["MAX_MESSAGES_PER_REQUEST"] * 4)
            offset_id = 0
            all_messages = []
            while remaining > 0:
                batch_size = min(remaining, random.randint(*RATE_LIMIT_CONFIG["MESSAGE_BATCH_SIZE"]))
                try:
                    messages = await client.get_messages(group_entity, limit=batch_size, offset_id=offset_id)
                    if not messages:
                        crawler_logger.info("没有更多消息可获取")
                        break
                    all_messages.extend(messages)
                    offset_id = messages[-1].id
                    remaining -= batch_size
                    await asyncio.sleep(random.uniform(*RATE_LIMIT_CONFIG["BATCH_INTERVAL"]))
                    if random.random() < 0.05:
                        pause_time = random.uniform(30.0, 60.0)
                        crawler_logger.info(f"模拟用户阅读，暂停 {pause_time} 秒")
                        await asyncio.sleep(pause_time)
                except FloodWaitError as e:
                    crawler_logger.warning(f"get_messages&FloodWaitError: {e} ")
                    raise
            filtered_messages = [msg.text for msg in all_messages if msg.text]
            messages_str = " ".join(filtered_messages)
        else:
            crawler_logger.info("未指定消息数量，获取直到 15000 字符或 200 条")
            total_length = 0
            offset_id = 0
            all_messages = []
            max_messages = 200
            while total_length <= 15000 and len(all_messages) < max_messages:
                batch_size = random.randint(*RATE_LIMIT_CONFIG["MESSAGE_BATCH_SIZE"])
                try:
                    messages = await client.get_messages(group_entity, limit=batch_size, offset_id=offset_id)
                    if not messages:
                        crawler_logger.info("已获取所有消息，停止轮询")
                        break
                    filtered_messages = [msg.text for msg in messages if msg.text]
                    batch_text = " ".join(filtered_messages)
                    all_messages.extend(messages)
                    total_length += len(batch_text)
                    offset_id = messages[-1].id
                    crawler_logger.debug(f"当前消息总长度: {total_length}")
                    await asyncio.sleep(random.uniform(*RATE_LIMIT_CONFIG["BATCH_INTERVAL"]))
                    if random.random() < 0.05:
                        pause_time = random.uniform(30.0, 60.0)
                        crawler_logger.info(f"模拟用户阅读，暂停 {pause_time} 秒")
                        await asyncio.sleep(pause_time)
                except FloodWaitError as e:
                    crawler_logger.warning(f"get_messages&FloodWaitError: {e} ")
                    raise
            messages_str = " ".join([msg.text for msg in all_messages if msg.text])

        avatar_base64 = None
        try:
            avatar_bytes = await client.download_profile_photo(group_entity, file=BytesIO())
            if avatar_bytes:
                avatar_bytes.seek(0)
                avatar_base64 = base64.b64encode(avatar_bytes.read()).decode('utf-8')
                crawler_logger.info("成功获取群组头像并转换为 Base64")
        except Exception as e:
            crawler_logger.warning(f"获取头像失败: {e}")

        keyid = url_to_unique_id(normalize_url(group_url), 17)
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
        result_str = json.dumps(result, ensure_ascii=False, indent=4)

        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        mongo = MongoDBHandler(host=MONGO_HOST, port=MONGO_PORT, database=MONGO_DB, collection=MONGO_COLLECTION)
        del result["messages"]
        mongo.insert_data(result)
        mongo.close()

        return result1

    except FloodWaitError as e:
        wait_time = e.seconds
        crawler_logger.warning(f"FloodWaitError in join_and_fetch_group_info: 等待 {wait_time} 秒")
        raise  # 重新抛出 FloodWaitError，让 worker 捕获
    except Exception as e:
        crawler_logger.error(f"处理 {group_url} 失败: {e}")
        return None

def split_content_into_blocks(data, max_block_size=5000, logger=None):
    # 使用固定的 crawler_logger
    input_doc_id = data.get("doc_id", "")
    content = data.get("content", "")
    if not content:
        crawler_logger.info(f"No content to split for doc_id: {input_doc_id}")
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


async def main():
    # 读取 URL 文件
    with open("group_urls.txt", "r", encoding="utf-8") as f:
        group_urls = [line.strip() for line in f if line.strip()]
    

if __name__ == "__main__":
    asyncio.run(main())
