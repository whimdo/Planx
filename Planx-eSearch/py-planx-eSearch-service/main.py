from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import logging
from config.service_config import ServiceConfig
from config.llm_config import llm_Config  # 修正类名一致性

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("query_service.log"),  # 输出到文件
        logging.StreamHandler()                    # 输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(title="Group ID Query Service", description="Query group IDs based on text input")

# 初始化服务配置和 LLM 配置
service_config = ServiceConfig()
llm_config = llm_Config(keyWordCount=20, sys_prompt=None)

# 定义请求模型
class QueryRequest(BaseModel):
    text: str
    keyword_count: int = 20  # 默认提取 20 个关键词
    top_k: int = 5          # 默认返回 5 个组群 ID

# 定义响应模型
class QueryResponse(BaseModel):
    group_ids: list[str]

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

# 查询接口
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
        # Step 1: 提取关键词
        keywords = extract_keywords(request.text, request.keyword_count)
        
        # Step 2: 获取特征向量
        feature_vector = get_feature_vector(keywords)
        
        # Step 3: 搜索组群 ID
        group_ids = search_group_ids(feature_vector, request.top_k)
        
        logger.info(f"Final group IDs: {group_ids}")
        return {"group_ids": group_ids}
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 示例启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9005)