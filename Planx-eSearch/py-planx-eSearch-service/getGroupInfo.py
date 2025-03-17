from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # 导入 CORS 中间件
from pydantic import BaseModel
import requests
import logging
from pymongo import MongoClient
from config.service_config import ServiceConfig
from config.llm_config import llm_Config
from typing import Union, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("query_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(title="Group ID Query Service", description="Query group IDs and group info based on text input")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，可以指定具体域名，如 ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法（GET, POST 等）
    allow_headers=["*"],  # 允许所有头部
)

# 初始化服务配置和 LLM 配置
service_config = ServiceConfig()
llm_config = llm_Config(keyWordCount=20, sys_prompt=None)

# MongoDB 处理类
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
            document = self.collection.find_one({"key_id": doc_id})
            
            if document:
                document.pop("_id", None)
                logger.info(f"查询成功: doc_id={doc_id}, 找到记录")
                return document
            else:
                logger.warning(f"未找到记录: doc_id={doc_id}")
                return None
        except Exception as e:
            logger.error(f"查询失败: doc_id={doc_id}, 错误: {e}")
            raise

    def close(self):
        """关闭 MongoDB 连接"""
        self.client.close()
        logger.info("MongoDB 连接已关闭")

# 定义请求模型
class QueryRequest(BaseModel):
    text: str
    keyword_count: int = 20  # 默认提取 20 个关键词
    top_k: int = 5          # 默认返回 5 个组群 ID

class GroupInfoRequest(BaseModel):
    group_ids: list[str]    # 查询多个 group_ids 的请求

# 定义响应模型
class QueryResponse(BaseModel):
    group_ids: list[str]

class GroupInfoResponse(BaseModel):
    group_ids: List[str]
    group_info: List[Union[dict, None]]  # 使用 Union 表示 dict 或 None

# 初始化 MongoDB 客户端
mongo_handler = MongoDBHandler()

# Step 1: 提取关键词
def extract_keywords(text: str, keyword_count: int):
    logger.info("Step 1 - Extract Keywords")
    logger.info(f"Input: text='{text}', keyword_count={keyword_count}")
    
    payload = {
        "text": text,
        "sys_prompt": llm_config.sys_prompt,
        "keyword_count": keyword_count
    }
    response = requests.post(service_config.extract_keywords_url, json=payload)
    if response.status_code == 200:
        keywords = response.json()["keywords"]
        logger.info(f"Output: keywords={keywords}")
        return keywords
    else:
        logger.error(f"Failed to extract keywords: {response.text}")
        raise HTTPException(status_code=response.status_code, detail=f"Failed to extract keywords: {response.text}")

# Step 2: 获取特征向量
def get_feature_vector(keywords: list[str]):
    logger.info("Step 2 - Get Feature Vector")
    logger.info(f"Input: keywords={keywords}")
    
    payload = {
        "keywords": keywords
    }
    response = requests.post(service_config.feature_vector_url, json=payload)
    if response.status_code == 200:
        feature_vector = response.json()["feature_vector"]
        logger.info(f"Output: feature_vector (length={len(feature_vector)})=[{feature_vector[0]}, {feature_vector[1]}, ...]")
        return feature_vector
    else:
        logger.error(f"Failed to get feature vector: {response.text}")
        raise HTTPException(status_code=response.status_code, detail=f"Failed to get feature vector: {response.text}")

# Step 3: 搜索相关文档并获取组群 ID
def search_group_ids(feature_vector: list[float], top_k: int):
    logger.info("Step 3 - Search Group IDs")
    logger.info(f"Input: feature_vector (length={len(feature_vector)})=[{feature_vector[0]}, {feature_vector[1]}, ...], top_k={top_k}")
    
    payload = {
        "query_vector": feature_vector,
        "top_k": top_k
    }
    response = requests.post(service_config.search_documents_url, json=payload)
    if response.status_code == 200:
        results = response.json()
        group_ids = [result["doc_id"] for result in results]
        logger.info(f"Output: group_ids={group_ids}")
        return group_ids
    else:
        logger.error(f"Failed to search documents: {response.text}")
        raise HTTPException(status_code=response.status_code, detail=f"Failed to search documents: {response.text}")

# 查询组群 ID 接口（保持不变）
@app.post("/query_group_ids/", response_model=QueryResponse)
async def query_group_ids(request: QueryRequest):
    """
    根据用户输入的文本查询相关组群 ID。
    
    Args:
        request: 包含 text、keyword_count 和 top_k 的请求体
    
    Returns:
        QueryResponse: 包含组群 ID 列表的响应
    """
    try:
        keywords = extract_keywords(request.text, request.keyword_count)
        feature_vector = get_feature_vector(keywords)
        group_ids = search_group_ids(feature_vector, request.top_k)
        
        logger.info(f"Final group IDs: {group_ids}")
        return {"group_ids": group_ids}
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 新增路由：根据 group_ids 查询组群信息
# 新增路由：根据文本查询组群信息
@app.post("/query_group_info/", response_model=GroupInfoResponse)
async def query_group_info(request: QueryRequest):  # 使用 QueryRequest 而非 GroupInfoRequest
    """
    根据用户输入的文本查询相关组群 ID 和对应的组群信息。
    
    Args:
        request: 包含 text、keyword_count 和 top_k 的请求体
    
    Returns:
        GroupInfoResponse: 包含组群 ID 列表和组群信息的响应
    """
    try:
        # Step 1: 提取关键词
        keywords = extract_keywords(request.text, request.keyword_count)
        
        # Step 2: 获取特征向量
        feature_vector = get_feature_vector(keywords)
        
        # Step 3: 搜索组群 ID
        group_ids = search_group_ids(feature_vector, request.top_k)
        
        # Step 4: 查询组群信息
        group_info = []
        for doc_id in group_ids:
            info = mongo_handler.find_by_doc_id(doc_id)
            group_info.append(info)
        
        logger.info(f"Queried group IDs: {group_ids}")
        #logger.info(f"Group info retrieved: {group_info}")
        return {"group_ids": group_ids, "group_info": group_info}
    except Exception as e:
        logger.error(f"Query group info failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to query group info: {str(e)}")


# 示例启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9006)