import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from kafka import KafkaConsumer
import json
import logging
import os
from threading import Thread
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configurations.kafka_config import kafka_config
from configurations.milvus_config import milvus_config

# 配置日志
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/milvus_store.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(
    title="Milvus Document Vector Store API",
    description="API for storing, retrieving, and searching document vectors in Milvus",
    version="1.0.0"
)

# 连接 Milvus
logger.info("Connecting to Milvus...")
try:
    connections.connect(host=milvus_config.MILVUS_HOST, port=milvus_config.MILVUS_PORT)
    logger.info("Connected to Milvus successfully")
except Exception as e:
    logger.error(f"Failed to connect to Milvus: {e}")
    raise

# 定义 Milvus 集合（去掉 keywords 字段）
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=255),
    FieldSchema(name="feature_vector", dtype=DataType.FLOAT_VECTOR, dim=300),
    FieldSchema(name="keyword_counts", dtype=DataType.VARCHAR, max_length=2048),  # 存储JSON字符串
    FieldSchema(name="range", dtype=DataType.FLOAT),
    FieldSchema(name="variance", dtype=DataType.FLOAT),
    FieldSchema(name="std_dev", dtype=DataType.FLOAT)
]

schema = CollectionSchema(fields=fields, description="Document vectors with metadata")
if not utility.has_collection(milvus_config.MILVUS_COLLECTION_NAME):
    collection = Collection(milvus_config.MILVUS_COLLECTION_NAME, schema)
    index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
    collection.create_index("feature_vector", index_params)
    logger.info(f"Created Milvus collection: {milvus_config.MILVUS_COLLECTION_NAME}")
else:
    collection = Collection(milvus_config.MILVUS_COLLECTION_NAME)
    logger.info(f"Using existing Milvus collection: {milvus_config.MILVUS_COLLECTION_NAME}")

# Kafka 消费者配置
consumer = KafkaConsumer(
    kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS,
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='milvus_storage_group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# 输入模型（存储，去掉 keywords）
class DocumentInput(BaseModel):
    doc_id: str
    keyword_counts: dict[str, int]
    feature_vector: list[float]
    similarity_stats: dict[str, float]

# 输出模型（存储，去掉 keywords）
class DocumentOutput(BaseModel):
    doc_id: str
    keyword_counts: dict[str, int]
    feature_vector: list[float]
    similarity_stats: dict[str, float]

# 输入模型（查询）
class QueryRequest(BaseModel):
    doc_id: str

# 输出模型（查询，去掉 keywords）
class QueryResponse(BaseModel):
    doc_id: str
    keyword_counts: dict[str, int]
    feature_vector: list[float]
    similarity_stats: dict[str, float]

# 输入模型（搜索）
class SearchRequest(BaseModel):
    query_vector: list[float]
    top_k: int = 10

# 输出模型（搜索，去掉 keywords）
class SearchResult(BaseModel):
    id: int
    doc_id: str
    distance: float
    keyword_counts: dict[str, int]

# 存储路由
@app.post("/store-document/", response_model=DocumentOutput)
async def store_document(request: DocumentInput):
    """
    将文档向量和元数据存入 Milvus
    """
    logger.info(f"Received store request for doc_id: {request.doc_id}")
    
    try:
        if len(request.feature_vector) != 300:
            raise ValueError("Feature vector must be 300-dimensional")
        
        data = request.model_dump()
        
        milvus_data = {
            "doc_id": [data["doc_id"]],
            "feature_vector": [data["feature_vector"]],
            "keyword_counts": [json.dumps(data["keyword_counts"])],
            "range": [data["similarity_stats"]["range"]],
            "variance": [data["similarity_stats"]["variance"]],
            "std_dev": [data["similarity_stats"]["std_dev"]]
        }
        
        collection.insert([
            milvus_data["doc_id"],
            milvus_data["feature_vector"],
            milvus_data["keyword_counts"],
            milvus_data["range"],
            milvus_data["variance"],
            milvus_data["std_dev"]
        ])
        collection.load()
        logger.info(f"Inserted document into Milvus for doc_id: {request.doc_id}")
        
        return data
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 查询路由
@app.post("/query-document/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """
    从 Milvus 中查询文档向量和元数据
    """
    logger.info(f"Received query request for doc_id: {request.doc_id}")
    
    try:
        collection.load()
        expr = f"doc_id == '{request.doc_id}'"
        results = collection.query(
            expr=expr,
            output_fields=["doc_id", "feature_vector", "keyword_counts", "range", "variance", "std_dev"]
        )
        
        if not results:
            logger.warning(f"No data found for doc_id: {request.doc_id}")
            raise HTTPException(status_code=404, detail="No matching data found")
        
        result = results[0]
        response = {
            "doc_id": result["doc_id"],
            "keyword_counts": json.loads(result["keyword_counts"]),
            "feature_vector": result["feature_vector"],
            "similarity_stats": {
                "range": result["range"],
                "variance": result["variance"],
                "std_dev": result["std_dev"]
            }
        }
        
        logger.info(f"Queried document for doc_id: {request.doc_id}")
        return response
    
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 搜索路由
@app.post("/search-documents/", response_model=list[SearchResult])
async def search_documents(request: SearchRequest):
    """
    在 Milvus 中搜索与查询向量最相似的文档向量
    """
    logger.info(f"Received search request with top_k: {request.top_k}")
    
    try:
        if len(request.query_vector) != 300:
            raise ValueError("Query vector must be 300-dimensional")
        
        collection.load()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[request.query_vector],
            anns_field="feature_vector",
            param=search_params,
            limit=request.top_k,
            output_fields=["doc_id", "keyword_counts"]
        )
        
        response = []
        for hits in results:
            for hit in hits:
                response.append({
                    "id": hit.id,
                    "doc_id": hit.entity.get("doc_id"),
                    "distance": hit.distance,
                    "keyword_counts": json.loads(hit.entity.get("keyword_counts"))
                })
        
        if not response:
            logger.warning("No similar vectors found")
            return []
        
        logger.info(f"Found {len(response)} similar documents")
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Kafka 消费者：从 SumVec 获取数据并存入 Milvus（去掉 keywords）
def consume_and_store_to_milvus():
    logger.info(f"Starting Kafka consumer for topic: {kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS}")
    for message in consumer:
        data = message.value
        logger.info(f"Consumed message from Kafka topic {kafka_config.KAFKA_TOPIC_SUMMARY_VECTORS}: doc_id={data['doc_id']}")
        
        try:
            if len(data["feature_vector"]) != 300:
                raise ValueError("Feature vector must be 300-dimensional")
            
            # 准备 Milvus 数据（去掉 keywords）
            milvus_data = {
                "doc_id": [data["doc_id"]],
                "feature_vector": [data["feature_vector"]],
                "keyword_counts": [json.dumps(data["keyword_counts"])],
                "range": [data["similarity_stats"]["range"]],
                "variance": [data["similarity_stats"]["variance"]],
                "std_dev": [data["similarity_stats"]["std_dev"]]
            }
            
            # 插入 Milvus
            collection.insert([
                milvus_data["doc_id"],
                milvus_data["feature_vector"],
                milvus_data["keyword_counts"],
                milvus_data["range"],
                milvus_data["variance"],
                milvus_data["std_dev"]
            ])
            collection.load()
            logger.info(f"Inserted document into Milvus for doc_id: {data['doc_id']}")
        
        except ValueError as e:
            logger.error(f"Validation error for doc_id {data['doc_id']}: {str(e)}")
        except Exception as e:
            logger.error(f"Storage error for doc_id {data['doc_id']}: {str(e)}")

# 根路径
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Milvus Document Vector Store API"}

if __name__ == "__main__":
    import uvicorn
    
    # 启动消费者线程
    consumer_thread = Thread(target=consume_and_store_to_milvus)
    consumer_thread.daemon = True
    consumer_thread.start()
    
    # 启动 FastAPI 服务
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=9004)