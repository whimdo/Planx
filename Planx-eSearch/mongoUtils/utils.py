from pymongo import MongoClient
import logging

# 设置日志
logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self, host='192.168.1.204', port=27017, database='telegram', collection='groupinfo'):
        """初始化 MongoDB 客户端"""
        try:
            self.client = MongoClient(host, port)
            self.db = self.client[database]
            self.collection = self.db[collection]
            logger.info(f"成功连接到 MongoDB: {host}:{port}, 数据库: {database}, 集合: {collection}")
        except Exception as e:
            logger.error(f"连接 MongoDB 失败: {e}")
            raise

    def insert_data(self, data):
        """将数据插入 MongoDB"""
        try:
            # 检查是否已存在相同的 key_id，若存在则更新，否则插入
            result = self.collection.update_one(
                {"key_id": data["doc_id"]},  # 根据 key_id 查找
                {"$set": data},              # 更新或设置数据
                upsert=True                  # 若不存在则插入
            )
            if result.upserted_id:
                logger.info(f"成功插入新记录，key_id: {data['doc_id']}")
            elif result.modified_count > 0:
                logger.info(f"成功更新记录，key_id: {data['doc_id']}")
            else:
                logger.info(f"记录已存在，未修改，key_id: {data['doc_id']}")
            return result
        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            raise
    def find_by_doc_id(self, doc_id: str) -> dict:
        """
        根据 doc_id 查询 MongoDB 并返回完整的 JSON 格式数据。
        
        参数:
            doc_id (str): 要查询的文档 ID
            
        返回:
            dict: 匹配的文档（JSON 格式），若未找到则返回 None
        """
        try:
            logger.info(f"开始查询: doc_id={doc_id}")
            # 查询集合，使用 key_id 字段匹配 doc_id
            document = self.collection.find_one({"key_id": doc_id})
            
            if document:
                # 移除 MongoDB 自动添加的 _id 字段（可选，根据需求保留或删除）
                document.pop("_id", None)
                logger.info(f"查询成功: doc_id={doc_id}, 找到记录")
                return document
            else:
                logger.warning(f"未找到记录: doc_id={doc_id}")
                return None  # 或抛出异常，见下文
        except Exception as e:
            logger.error(f"查询失败: doc_id={doc_id}, 错误: {e}")
            raise

    def close(self):
        """关闭 MongoDB 连接"""
        self.client.close()
        logger.info("MongoDB 连接已关闭")