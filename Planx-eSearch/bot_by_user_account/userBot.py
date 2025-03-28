# telegram_bot.py
import asyncio
from telethon import TelegramClient, events
from collections import defaultdict
import os
import sys
import signal
from pymongo import MongoClient
from datetime import datetime,timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from configurations.tele_config import TeleConfig
from configurations.mongo_config import MongoConfig
from mcpAI.client import MCPClient  # 导入独立的 MCPClient 类

api_id = TeleConfig.TELEGRAM_API_ID
api_hash = TeleConfig.TELEGRAM_API_HASH
phone = '+60142003454'
session_file = f"{phone}"

# MongoDB 配置
MONGO_URI = MongoConfig.MONGO_HOST 
DB_NAME = MongoConfig.MONGO_DB_BOT
COLLECTION_NAME = MongoConfig.MONGO_COLLECTION_BOT

# 创建 Telegram 客户端
client = TelegramClient(session_file, api_id, api_hash)

# 存储每个用户的 MCPClient 实例
mcp_clients = defaultdict(MCPClient)

# 初始化 MongoDB 客户端
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

# 设置 TTL 索引（1 天 = 86400 秒）
def setup_ttl_index():
    collection.create_index("timestamp", expireAfterSeconds=86400)
    print("TTL 索引已设置，上下文将在 1 天后自动过期")

# 从 MongoDB 加载上下文
def load_context(sender_id):
    doc = collection.find_one({"sender_id": str(sender_id)})
    return doc["messages"] if doc else []

# 保存上下文到 MongoDB
def save_context(sender_id, messages):
    collection.update_one(
        {"sender_id": str(sender_id)},
        {
            "$set": {
                "messages": messages,
                "timestamp": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )

# 初始化 MCPClient 并加载上下文
async def initialize_mcp_client(sender_id):
    if sender_id not in mcp_clients:
        mcp_client = MCPClient()
        await mcp_client.connect_to_server("../mcpAI/server.py")
        mcp_client.messages = load_context(sender_id)
        mcp_clients[sender_id] = mcp_client
    return mcp_clients[sender_id]

# 处理新消息的事件
@client.on(events.NewMessage)
async def handle_message(event):
    sender = await event.get_sender()
    sender_id = sender.id if sender else event.chat_id
    message_text = event.message.text
    
    me = await client.get_me()
    my_username = f"@{me.username}" if me.username else None
    
    should_reply = False
    target = None
    reply_to = None
    
    if event.is_private:
        should_reply = True
        target = sender_id
    elif event.is_group and my_username and my_username in message_text:
        should_reply = True
        target = event.chat_id
        reply_to = event.message.id
    
    if should_reply and message_text:
        mcp_client = await initialize_mcp_client(sender_id)
        reply = await mcp_client.process_query(message_text)
        await client.send_message(
            target,
            reply,
            reply_to=reply_to if event.is_group else None
        )
        save_context(sender_id, mcp_client.messages)

# 清理所有 MCPClient 实例
async def cleanup_all():
    for mcp_client in mcp_clients.values():
        try:
            await mcp_client.cleanup()
        except Exception as e:
            print(f"清理 MCPClient 时出错: {e}")
    mongo_client.close()
    if client.is_connected():
        await client.disconnect()

# 异步 main 函数
async def main():
    setup_ttl_index()
    await client.start(phone)
    print("Telegram 客户端已启动，监听消息中...")
    try:
        await client.run_until_disconnected()
    finally:
        await cleanup_all()
        print("所有 MCPClient 和 MongoDB 连接已清理")

if __name__ == "__main__":
    asyncio.run(main())