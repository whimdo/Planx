from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer,KafkaConsumer
import json
import numpy as np
from gensim.models import KeyedVectors
from sklearn.metrics.pairwise import cosine_similarity
import logging


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
KAFKA_TOPIC = "kywrd2vec"
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
    # 文档移到类文档字符串中
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
        raise ValueError("All keywords are not in the Word2Vec model!")
    logger.info(f"Computed feature vector for {len(vectors)} keywords out of {len(keywords)}")
    return np.mean(vectors, axis=0)

# 计算相似性统计
def compute_similarity_stats(vectors: list[np.ndarray]) -> tuple[float, float, float]:
    similarities = cosine_similarity(vectors)
    upper_triangle = similarities[np.triu_indices(len(vectors), k=1)]
    if len(upper_triangle) == 0:
        logger.warning("Not enough vectors to compute similarity stats (need at least 2 keywords)")
        return 0.0, 0.0, 0.0
    range_val = float(np.max(upper_triangle) - np.min(upper_triangle))
    variance_val = float(np.var(upper_triangle))
    std_dev_val = float(np.std(upper_triangle))
    logger.info(f"Similarity stats: range={range_val}, variance={variance_val}, std_dev={std_dev_val}")
    return range_val, variance_val, std_dev_val

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
            try:
                vectors = [word2vec_model[word] for word in keywords if word in word2vec_model]
                if not vectors:
                    raise ValueError(f"No keywords found in Word2Vec model for block {block['block_id']}")
                
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
            except ValueError as e:
                logger.error(f"Block {block['block_id']} processing failed: {e}")
                raise
            
        response = {
            "doc_id": request.doc_id,
            "total_blocks": request.total_blocks,
            "blocks": output_blocks
        }
        
        producer.send('vectors2Sum', value=response)
        logger.info(f"Processed and sent to Kafka: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 启动函数
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8001)