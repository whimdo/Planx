import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer, KafkaConsumer
import json
import numpy as np
from collections import Counter
import logging
import os
from threading import Thread
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configurations.kafka_config import kafka_config


# 配置日志
LOG_DIR = "/home/intern/public/Planx-eSearch/py-planx-eSearch-vecs-sum/logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(f"{LOG_DIR}/vectorsum.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Kafka 配置
# kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY = "vectors2Sum"  # 输入主题（分块数据）
# kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS = "SumVec"  # 输出主题（文档级别数据）
# kafka_config.KAFKA_BOOTSTRAP_SERVERS = "192.168.1.206:9092"

# Kafka 生产者配置
producer = KafkaProducer(
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    max_request_size=10485760  # 10MB
)

# Kafka 消费者配置
consumer = KafkaConsumer(
    kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY,
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='doc_processing_group',
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

# 计算相似性统计
def compute_similarity_stats(vector):
    """计算特征向量的统计信息"""
    vector = np.array(vector)
    return {
        "range": float(np.max(vector) - np.min(vector)),
        "variance": float(np.var(vector)),
        "std_dev": float(np.std(vector))
    }

# 整合块信息
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
        if len(request.blocks) != request.total_blocks:
            raise ValueError("Number of blocks does not match total_blocks")
        
        blocks = [block.model_dump() for block in request.blocks]
        final_keywords, keyword_counts, final_vector, similarity_stats = integrate_blocks(blocks)
        
        response = {
            "doc_id": request.doc_id,
            "keywords": final_keywords,
            "keyword_counts": dict(keyword_counts),
            "feature_vector": final_vector.tolist(),
            "similarity_stats": similarity_stats
        }
        
        producer.send(kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS, value=response)
        logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS}: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Kafka 生产者：发送分块数据
def produce_block_data(doc_id: str, blocks: list[dict]):
    data = {
        "doc_id": doc_id,
        "total_blocks": len(blocks),
        "blocks": blocks
    }
    producer.send(kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY, value=data)
    logger.info(f"Produced data to Kafka topic {kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY}: {doc_id}")

# Kafka 消费者：处理分块数据并生产文档级别数据
def consume_and_process():
    logger.info(f"Starting Kafka consumer for topic: {kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY}")
    for message in consumer:
        data = message.value
        logger.info(f"Consumed message from Kafka topic {kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY}: doc_id={data['doc_id']}")
        
        try:
            if len(data["blocks"]) != data["total_blocks"]:
                raise ValueError("Number of blocks does not match total_blocks")
            
            blocks = data["blocks"]
            all_keywords = []
            all_vectors = []
            
            # 整合所有关键词和向量
            for block in blocks:
                all_keywords.extend(block["keywords"])
                all_vectors.append(np.array(block["feature_vector"]))
            
            # 计算关键词频率
            keyword_counts = Counter(all_keywords)
            
            # 计算文档级特征向量
            weights = [sum(keyword_counts[kw] for kw in block["keywords"]) for block in blocks]
            final_vector = np.average(all_vectors, axis=0, weights=weights)
            similarity_stats = compute_similarity_stats(final_vector)
            
            # 构造输出数据
            response = {
                "doc_id": data["doc_id"],
                "keyword_counts": dict(keyword_counts),
                "feature_vector": final_vector.tolist(),
                "similarity_stats": similarity_stats
            }
            
            producer.send(kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS, value=response)
            logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS}: {data['doc_id']}")
        
        except ValueError as e:
            logger.error(f"Processing error for doc_id {data['doc_id']}: {str(e)}")
        except Exception as e:
            logger.error(f"Internal error for doc_id {data['doc_id']}: {str(e)}")

# 根路径
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Document Blocks Processor API"}

if __name__ == "__main__":
    import uvicorn
    
    # # 示例生产者数据
    # sample_blocks = [
    #     {
    #         "block_id": 1,
    #         "keywords": ["ai", "machine"],
    #         "feature_vector": [1, 2, 3],
    #         "similarity_stats": {"range": 0.1, "variance": 0.01, "std_dev": 0.1},
    #         "processed_keywords": ["ai", "machine"]
    #     },
    #     {
    #         "block_id": 2,
    #         "keywords": ["machine", "news"],
    #         "feature_vector": [4, 5, 6],
    #         "similarity_stats": {"range": 0.2, "variance": 0.02, "std_dev": 0.2},
    #         "processed_keywords": ["machine", "news"]
    #     },
    #     {
    #         "block_id": 3,
    #         "keywords": ["tech", "data"],
    #         "feature_vector": [7, 8, 9],
    #         "similarity_stats": {"range": 0.3, "variance": 0.03, "std_dev": 0.3},
    #         "processed_keywords": ["tech", "data"]
    #     }
    # ]
    # produce_block_data("doc_001", sample_blocks)
    
    # 启动消费者线程
    consumer_thread = Thread(target=consume_and_process)
    consumer_thread.daemon = True
    consumer_thread.start()
    
    # 启动 FastAPI 服务
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=9003)