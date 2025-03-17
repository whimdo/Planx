import asyncio
import json
import socks
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError
from generateKeyID import normalize_url,url_to_unique_id
# from ..py_mongodb_utils.mongo import MongoDBHandler
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
# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 设置日志记录
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    filename=os.path.join(LOG_DIR, LOG_FILE),
    filemode=LOG_FILEMODE
)
logger = logging.getLogger(__name__)

# 配置 Clash 代理（SOCKS5）
proxy = (socks.SOCKS5, PROXY_HOST, PROXY_PORT)  # 根据你的 Clash 配置

# 创建 Telegram 客户端
client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH, proxy=proxy)


async def join_and_fetch_group_info(group_url,messageNum:int=None):
    try:
        logger.info("正在连接到 Telegram 服务器...")
        await client.start(phone=lambda: TELEGRAM_PHONE)
        logger.info("已成功登录")

        # 判断 URL 类型并提取标识符
        group_handle = None
        if '/+' in group_url:  # 处理私密邀请链接，如 https://t.me/+nldJa3KfsWU5NDg0
            invite_hash = group_url.split('/+')[1]
            logger.debug(f"处理私密邀请链接: hash={invite_hash}")
            try:
                updates = await client(ImportChatInviteRequest(invite_hash))
                group_entity = updates.chats[0]
                logger.info(f"通过邀请链接成功加入群组: {invite_hash}")
            except UserAlreadyParticipantError:
                logger.info(f"用户已加入群组，尝试直接获取实体: {invite_hash}")
                # 用户已加入，尝试通过邀请链接提取的群组标识符获取实体
                # 注意：私密群组可能没有公开用户名，这里使用群组的 ID 或其他方式
                group_entity = await client.get_entity(group_url)  # 直接使用 URL 尝试获取
            group_handle = group_entity.username or f"private_{invite_hash[:8]}"
        else:  # 处理公开链接和短链接
            # 将短链接转换为公开链接格式
            if group_url.startswith('https://t.me/') and '/+' not in group_url:
                group_url = group_url.replace('https://t.me/', 'https://web.telegram.org/k/#@')
                logger.debug(f"转换短链接为公开链接: {group_url}")
            
            # 提取群组标识符
            if '#@' in group_url:
                group_handle = group_url.split('#@')[1]
            else:
                group_handle = group_url.split('t.me/')[1]  # 兜底处理，确保兼容
            
            logger.debug(f"处理公开链接: @{group_handle}")
            group_entity = await client.get_entity('@' + group_handle)
            #await client(JoinChannelRequest(group_entity))

        logger.info(f"获取群组实体成功: {group_handle}")
        logger.info(f"已成功加入 {group_handle}")

        # 判断类型（群组或频道）
        group_type = "channel" if group_entity.broadcast else "group"

        # 获取群聊名称
        group_name = group_entity.title

        # 获取群聊成员数量
        full_channel = await client(GetFullChannelRequest(channel=group_entity))
        member_count = full_channel.full_chat.participants_count
        
        # 获取消息列表
        messages_str = ""
        if messageNum is not None:
            # 如果提供了 messageNum，按指定数量获取
            messages = await client.get_messages(group_entity, limit=messageNum)
            filtered_messages = [
                msg.text for msg in messages 
                if msg.text and len(msg.text.split()) >= 5
            ]
            messages_str = " ".join(filtered_messages)
        else:
            # 如果未提供 messageNum，持续获取直到总字符数超过 15000
            total_length = 0
            offset_id = 0
            batch_size = 100  # 每次获取 100 条消息
            all_messages = []
            while total_length <= 15000:
                messages = await client.get_messages(group_entity, limit=batch_size, offset_id=offset_id)
                if not messages:  # 没有更多消息
                    logger.info("已获取所有消息，停止轮询")
                    break
                filtered_messages = [
                    msg.text for msg in messages 
                    if msg.text and len(msg.text.split()) >= 5
                ]
                batch_text = " ".join(filtered_messages)
                all_messages.extend(messages)
                total_length += len(batch_text)
                offset_id = messages[-1].id  # 更新 offset_id 为最后一条消息的 ID
                logger.debug(f"当前消息总长度: {total_length}")
            filtered_messages = [
                msg.text for msg in all_messages 
                if msg.text and len(msg.text.split()) >= 5
            ]
            messages_str = " ".join(filtered_messages)

        # 获取群组头像并直接转换为 Base64（不保存文件）
        avatar_base64 = None
        try:
            # 下载头像到内存（BytesIO）
            avatar_bytes = await client.download_profile_photo(group_entity, file=BytesIO())
            if avatar_bytes:
                avatar_bytes.seek(0)  # 重置缓冲区指针
                avatar_base64 = base64.b64encode(avatar_bytes.read()).decode('utf-8')
                logger.info(f"成功获取群组头像并转换为 Base64")
        except Exception as e:
            logger.warning(f"获取头像失败: {e}")
        keyid = url_to_unique_id(normalize_url(group_url),17)
        # 构建 JSON 数据，包含 url 字段
        result = {
            "doc_id": keyid,
            "type": group_type,
            "name": group_name,
            "member_count": member_count,
            "url": group_url,
            "avatar": avatar_base64,
            "messages": messages_str
        }
        result1 = {
            "doc_id": keyid,
            "content": messages_str
        }
        # 将 JSON 数据转换为字符串
        result_str = json.dumps(result, ensure_ascii=False, indent=4)

        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        del result["messages"]
        # 保存到 MongoDB
        mongo = MongoDBHandler(host=MONGO_HOST, port=MONGO_PORT, database=MONGO_DB, collection=MONGO_COLLECTION)
        mongo.insert_data(result)
        mongo.close()

        return result1
    except Exception as e:
        logger.error(f"发生错误: {e}")

def split_content_into_blocks(data, max_block_size=5000):
    """
    将输入的内容按指定大小分块并返回结构化数据。
    
    参数:
        data (dict): 输入数据，包含 "doc_id" 和 "content"
        max_block_size (int): 每块的最大字符数，默认为 7000
    
    返回:
        dict: 包含 doc_id, total_blocks 和 blocks 的结构化数据
    """
    # 提取输入数据
    input_doc_id = data.get("doc_id", "")
    content = data.get("content", "")
    
    # 如果 content 为空，返回空块
    if not content:
        return {
            "doc_id": input_doc_id,
            "total_blocks": 0,
            "blocks": []
        }
    # 计算分块
    blocks = []
    block_id = 1
    for i in range(0, len(content), max_block_size):
        block_content = content[i:i + max_block_size]
        blocks.append({
            "block_id": block_id,
            "content": block_content
        })
        block_id += 1
    # 构造返回数据
    result = {
        "doc_id": input_doc_id,
        "total_blocks": block_id-1,
        "blocks": blocks
    }
    kafka = KafkaClient()
    kafka.initialize_producer()
    kafka.send_message(KafkaConfig.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS,result)
    kafka.close()
    return result

async def process_telegram_url(url: str, message_num=None, max_block_size: int = 1000):
    """
    处理单个 Telegram URL 的完整流程
    
    参数:
        url: Telegram 群组链接
        message_num: 要爬取的消息数量，默认100
        max_block_size: 最大分块大小，默认1000
    
    返回:
        分块后的结构化数据
    """
    # 验证参数
    if not url:
        logger.error("URL 为空")
        raise ValueError("URL 不能为空")
    
    if message_num <= 0:
        logger.error(f"无效的消息条数: {message_num}")
        raise ValueError("消息条数必须大于0")
    
    if max_block_size <= 0:
        logger.error(f"无效的分块大小: {max_block_size}")
        raise ValueError("分块大小必须大于0")

    try:
        # 第一步：爬取 Telegram 数据
        logger.info(f"开始爬取: url={url}, messageNum={message_num}")
        crawl_result = await join_and_fetch_group_info(url, message_num)
        logger.info(f"爬取完成: url={url}")

        # 验证爬取结果
        if "doc_id" not in crawl_result or not crawl_result["doc_id"]:
            logger.error("爬取结果中 doc_id 为空")
            raise ValueError("爬取结果中 doc_id 为空")
        
        if "content" not in crawl_result or not crawl_result["content"]:
            logger.error("爬取结果中 content 为空")
            raise ValueError("爬取结果中 content 为空")

        # 第二步：准备分块数据
        split_data = {
            "doc_id": crawl_result["doc_id"],
            "content": crawl_result["content"],
            "max_block_size": max_block_size
        }

        # 第三步：执行分块
        logger.info(f"开始分块: doc_id={split_data['doc_id']}, max_block_size={max_block_size}")
        result = split_content_into_blocks(split_data, max_block_size=max_block_size)
        logger.info(f"分块完成: doc_id={split_data['doc_id']}, total_blocks={len(result['blocks'])}")
        return result

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise


async def main():
    group_url = input("请输入群组链接 (如 https://web.telegram.org/k/#@CryptoComOfficial 或 @username): ")
    await join_and_fetch_group_info(group_url,30)

if __name__ == "__main__":
    asyncio.run(main())