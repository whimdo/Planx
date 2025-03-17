from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from kafka import KafkaProducer,KafkaConsumer
import numpy as np
from collections import Counter
import logging
import os

# 配置日志
LOG_DIR = "/home/intern/public/Planx-eSearch/py-planx-eSearch-vecs-sum/logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(f"{LOG_DIR}/url2uid.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Kafka 配置
KAFKA_TOPIC = "vectors2Sum"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

# Kafka 生产者配置
producer = KafkaProducer(
    bootstrap_servers= KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    max_request_size=10485760  # 10MB
)

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers= KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='my-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)


# 初始化 FastAPI
app = FastAPI(
    title="Document Blocks Processor",
    description="Process document blocks and generate integrated features",
    version="1.0.0"
)

# 输入模型
class Block(BaseModel):
    block_id: int
    keywords: list[str]
    feature_vector: list[float]
    similarity_stats: dict[str, float]
    processed_keywords: list[str]

class DocumentRequest(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[Block]

# 输出模型
class DocumentResponse(BaseModel):
    doc_id: str
    keywords: list[str]
    keyword_counts: dict[str, int]
    feature_vector: list[float]
    similarity_stats: dict[str, float]

def compute_similarity_stats(vector):
    """计算特征向量的统计信息"""
    vector = np.array(vector)
    return {
        "range": float(np.max(vector) - np.min(vector)),
        "variance": float(np.var(vector)),
        "std_dev": float(np.std(vector))
    }

def integrate_blocks(blocks):
    """整合块信息：去重关键词并保留频率，频率加权生成特征向量"""
    all_keywords = []
    all_vectors = []
    
    for block in blocks:
        all_keywords.extend(block["keywords"])
        all_vectors.append(np.array(block["feature_vector"]))
    
    # 统计关键词频率
    keyword_counts = Counter(all_keywords)
    final_keywords = list(keyword_counts.keys())
    
    # 频率加权：块权重基于关键词总频率
    weights = [sum(keyword_counts[kw] for kw in block["keywords"]) for block in blocks]
    final_vector = np.average(all_vectors, axis=0, weights=weights)
    similarity_stats = compute_similarity_stats(final_vector)
    
    return final_keywords, keyword_counts, final_vector, similarity_stats

# 处理接口
@app.post("/process-blocks/", response_model=DocumentResponse)
async def process_blocks(request: DocumentRequest):
    """
    处理文档块信息，生成整合结果并存入 Kafka
    """
    logger.info(f"Received request for doc_id: {request.doc_id}")
    
    try:
        # 验证输入
        if len(request.blocks) != request.total_blocks:
            raise ValueError("Number of blocks does not match total_blocks")
        
        # 整合块信息
        blocks = [block.model_dump() for block in request.blocks]
        final_keywords, keyword_counts, final_vector, similarity_stats = integrate_blocks(blocks)
        
        # 构造输出
        response = {
            "doc_id": request.doc_id,
            "keywords": final_keywords,
            "keyword_counts": dict(keyword_counts),
            "feature_vector": final_vector.tolist(),
            "similarity_stats": similarity_stats
        }
        
        # 发送到 Kafka
        producer.send('SumVec', value=response)
        logger.info(f"Processed and sent to Kafka: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 根路径
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Document Blocks Processor API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)