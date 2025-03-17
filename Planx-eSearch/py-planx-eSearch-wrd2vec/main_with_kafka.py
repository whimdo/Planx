import os
import sys
from typing import List, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer, KafkaConsumer
import json
import numpy as np
from gensim.models import KeyedVectors
from sklearn.metrics.pairwise import cosine_similarity
import logging
from threading import Thread
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configurations.kafka_config import kafka_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("feature_vector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Kafka 配置
# kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS = "kywrd2vec"  # 输入主题（关键词）
# kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY = "vec2Sum"  # 输出主题（特征向量）
# kafka_config.KAFKA_BOOTSTRAP_SERVERS = "192.168.1.206:9092"

# Kafka 生产者配置
producer = KafkaProducer(
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    max_request_size=10485760  # 10MB
)

# Kafka 消费者配置
consumer = KafkaConsumer(
    kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS,
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='vector_processing_group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# 初始化 FastAPI 应用
app = FastAPI(
    title="Word2Vec Feature Vector and Similarity API",
    description="API for computing feature vectors and similarity stats of keywords using Word2Vec",
    version="1.0.0"
)

# 加载 Word2Vec 模型
WORD2VEC_PATH = "/home/intern/public/GoogleNews-vectors-negative300.bin.gz"
logger.info("Loading Word2Vec model...")
try:
    word2vec_model = KeyedVectors.load_word2vec_format(WORD2VEC_PATH, binary=True)
    logger.info("Word2Vec model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Word2Vec model: {e}")
    raise

# 定义请求数据模型
class KeywordsRequest(BaseModel):
    keywords: list[str]
    """List of keywords to compute feature vector and similarity stats for"""

# 定义请求数据模型（新路由：处理块类型）
class BlockInput(BaseModel):
    block_id: int
    keywords: list[str]

class DocumentInput(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[BlockInput]

# 定义输出数据模型（新路由）
class BlockOutput(BaseModel):
    block_id: int
    keywords: list[str]
    feature_vector: list[float]
    similarity_stats: dict[str, float]
    processed_keywords: list[str]

class DocumentOutput(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[BlockOutput]

# 获取特征向量
def get_feature_vector(keywords: list[str]) -> np.ndarray:
    vectors = [word2vec_model[word] for word in keywords if word in word2vec_model]
    if not vectors:
        logger.error("All keywords not found in Word2Vec model")
        return np.zeros(300)  # 返回零向量
    logger.info(f"Computed feature vector for {len(vectors)} keywords out of {len(keywords)}")
    return np.mean(vectors, axis=0)

# 计算相似性统计
def compute_similarity_stats(vectors: List[np.ndarray]) -> Tuple[float, float, float]:
    if not isinstance(vectors, list) or not vectors:
        logger.warning("Invalid input: vectors must be a non-empty list")
        return 0.0, 0.0, 0.0
    if len(vectors) < 2:
        logger.warning(f"Not enough vectors ({len(vectors)}) to compute similarity stats")
        return 0.0, 0.0, 0.0
    try:
        similarities = cosine_similarity(vectors)
        upper_triangle = similarities[np.triu_indices(len(vectors), k=1)]
        if upper_triangle.size == 0:
            logger.warning("No valid similarity values extracted")
            return 0.0, 0.0, 0.0
        range_val = float(np.max(upper_triangle) - np.min(upper_triangle))
        variance_val = float(np.var(upper_triangle))
        std_dev_val = float(np.std(upper_triangle))
        logger.debug(f"Similarity stats: range={range_val:.4f}, variance={variance_val:.4f}, std_dev={std_dev_val:.4f}")
        return range_val, variance_val, std_dev_val
    except Exception as e:
        logger.error(f"Error computing similarity stats: {str(e)}", exc_info=True)
        return 0.0, 0.0, 0.0



# FastAPI 路由：获取特征向量和相似性统计
@app.post("/get_feature_vector_and_stats/", response_model=dict)
async def get_feature_vector_and_stats(request: KeywordsRequest):
    logger.info(f"Received request with keywords: {request.keywords}")
    try:
        vectors = [word2vec_model[word] for word in request.keywords if word in word2vec_model]
        if not vectors:
            logger.error("No keywords found in Word2Vec model")
            raise HTTPException(status_code=400, detail="No keywords found in Word2Vec model")
        
        feature_vector = np.mean(vectors, axis=0).tolist()
        range_val, variance_val, std_dev_val = compute_similarity_stats(vectors)
        
        processed_keywords = [word for word in request.keywords if word in word2vec_model]
        response = {
            "feature_vector": feature_vector,
            "similarity_stats": {
                "range": range_val,
                "variance": variance_val,
                "std_dev": std_dev_val
            },
            "processed_keywords": processed_keywords
        }
        logger.info(f"Returning response: feature_vector_length={len(feature_vector)}, similarity_stats={response['similarity_stats']}")
        return response
    except ValueError as e:
        logger.error(f"Vector computation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 新路由：处理块类型关键词并生成特征向量
@app.post("/process-block-keywords/", response_model=DocumentOutput)
async def process_block_keywords(request: DocumentInput):
    """
    处理分块关键词，生成特征向量和相似性统计，并存入 Kafka
    """
    logger.info(f"Received request for doc_id: {request.doc_id}")
    
    try:
        if len(request.blocks) != request.total_blocks:
            raise ValueError("Number of blocks does not match total_blocks")
        
        blocks = [block.model_dump() for block in request.blocks]
        output_blocks = []
        
        for block in blocks:
            keywords = block["keywords"]
            vectors = [word2vec_model[word] for word in keywords if word in word2vec_model]
            if not vectors:
                logger.warning(f"No keywords found in Word2Vec model for block {block['block_id']}")
                feature_vector = np.zeros(300).tolist()
                range_val, variance_val, std_dev_val = 0.0, 0.0, 0.0
                processed_keywords = []
            else:
                feature_vector = np.mean(vectors, axis=0).tolist()
                range_val, variance_val, std_dev_val = compute_similarity_stats(vectors)
                processed_keywords = [word for word in keywords if word in word2vec_model]
                
            output_blocks.append({
                "block_id": block["block_id"],
                "keywords": keywords,
                "feature_vector": feature_vector,
                "similarity_stats": {
                    "range": range_val,
                    "variance": variance_val,
                    "std_dev": std_dev_val
                },
                "processed_keywords": processed_keywords
            })
        
        response = {
            "doc_id": request.doc_id,
            "total_blocks": request.total_blocks,
            "blocks": output_blocks
        }
        
        producer.send(kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY, value=response)
        logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY}: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Kafka 生产者：发送分块关键词数据
def produce_keyword_data(doc_id: str, blocks: list[dict]):
    data = {
        "doc_id": doc_id,
        "total_blocks": len(blocks),
        "blocks": blocks
    }
    producer.send(kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS, value=data)
    logger.info(f"Produced data to Kafka topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: {doc_id}")

def consume_and_process():
    logger.info(f"Starting Kafka consumer for topic: {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}")
    
    for message in consumer:
        data = message.value
        doc_id = data.get("doc_id", "unknown")
        logger.info(f"Consumed message from topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: doc_id={doc_id}")
        
        try:
            # 验证输入数据完整性
            if "blocks" not in data or "total_blocks" not in data:
                raise ValueError("Missing 'blocks' or 'total_blocks' in message")
            if len(data["blocks"]) != data["total_blocks"]:
                raise ValueError(f"Number of blocks ({len(data['blocks'])}) does not match total_blocks ({data['total_blocks']})")
            
            output_blocks = []
            for block in data["blocks"]:
                block_id = block.get("block_id", "unknown")
                keywords = block.get("keywords", [])
                
                if not keywords:
                    logger.warning(f"Empty keywords list for block {block_id} in doc_id {doc_id}")
                    feature_vector = np.zeros(300).tolist()
                    range_val, variance_val, std_dev_val = 0.0, 0.0, 0.0
                    processed_keywords = []
                else:
                    # 批量查询 Word2Vec 模型，提高效率
                    vectors = [word2vec_model[word] for word in keywords if word in word2vec_model]
                    processed_keywords = [word for word in keywords if word in word2vec_model]
                    
                    if not vectors:
                        logger.warning(f"No keywords found in Word2Vec model for block {block_id}: {keywords}")
                        feature_vector = np.zeros(300).tolist()
                        range_val, variance_val, std_dev_val = 0.0, 0.0, 0.0
                    else:
                        # 计算特征向量和统计指标
                        feature_vector = np.mean(vectors, axis=0).tolist()
                        range_val, variance_val, std_dev_val = compute_similarity_stats(vectors)
                        logger.debug(f"Block {block_id} stats: range={range_val}, variance={variance_val}, std_dev={std_dev_val}")
                
                output_blocks.append({
                    "block_id": block_id,
                    "keywords": keywords,
                    "feature_vector": feature_vector,
                    "similarity_stats": {
                        "range": range_val,
                        "variance": variance_val,
                        "std_dev": std_dev_val
                    },
                    "processed_keywords": processed_keywords
                })
            
            # 构造响应
            response = {
                "doc_id": doc_id,
                "total_blocks": data["total_blocks"],
                "blocks": output_blocks
            }
            
            # 发送到下游主题
            producer.send(kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY, value=response)
            logger.info(f"Processed and sent to topic {kafka_config.KAFKA_TOPIC_VECTORS_TO_SUMMARY}: doc_id={doc_id}, blocks={len(output_blocks)}")
        
        except ValueError as e:
            logger.error(f"Validation error for doc_id {doc_id}: {str(e)}")
            # 可选：发送部分结果或跳过
        except Exception as e:
            logger.error(f"Internal error for doc_id {doc_id}: {str(e)}", exc_info=True)
            # 可选：记录失败消息到死信队列

# 启动函数
if __name__ == "__main__":
    import uvicorn
    
    # 示例生产者数据
    # sample_blocks = [
    #     {"block_id": 1, "keywords": ["keyword1", "keyword2", "keyword3"]},
    #     {"block_id": 2, "keywords": ["keyword4", "keyword5", "keyword6"]},
    #     {"block_id": 3, "keywords": ["keyword7", "keyword8", "keyword9"]}
    # ]
    # produce_keyword_data("doc_001", sample_blocks)
    
    # 启动消费者线程
    consumer_thread = Thread(target=consume_and_process)
    consumer_thread.daemon = True
    consumer_thread.start()
    
    # 启动 FastAPI 服务
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=9002)