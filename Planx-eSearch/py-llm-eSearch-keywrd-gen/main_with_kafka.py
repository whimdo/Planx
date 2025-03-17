import ast
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import time
import re
import json
from kafka import KafkaProducer, KafkaConsumer
from config.llm_config import llm_Config
from config.llm_config import setup_logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configurations.kafka_config import kafka_config

# 初始化日志
logger = setup_logging(log_file="keyword_extraction.log", log_level="INFO")

# 初始化 FastAPI 应用和 Config
app = FastAPI(
    title="Keyword Extraction API",
    description="API for extracting keywords from text using a language model",
    version="1.0.0"
)
llm_config = llm_Config()
client = OpenAI(base_url=llm_config.openai_base_url, api_key=llm_config.openai_api_key)

# Kafka 配置
# kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS = "doc2kywrd"  # 输入主题
# kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS = "kywrd2vec"  # 输出主题
# kafka_config.KAFKA_BOOTSTRAP_SERVERS = "192.168.1.206:9092"

# Kafka 生产者配置
producer = KafkaProducer(
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    max_request_size=10485760  # 10MB
)

# Kafka 消费者配置
consumer = KafkaConsumer(
    kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS,
    bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='keyword_extraction_group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# 定义请求数据模型，扩展支持所有参数
class ExtractRequest(BaseModel):
    text: str
    keyword_count: int = llm_config.keyWordCount
    model: str = llm_config.openai_model
    use_stream: bool = llm_config.openai_use_stream
    sys_prompt: str = llm_config.sys_prompt
    temp: float = llm_config.openai_temp
    max_tokens: int = llm_config.openai_max_tokens

# 定义请求数据模型（新路由：处理块类型）
class BlockInput(BaseModel):
    block_id: int
    content: str

class DocumentInput(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[BlockInput]
    keyword_count: int = llm_config.keyWordCount
    model: str = llm_config.openai_model
    use_stream: bool = llm_config.openai_use_stream
    sys_prompt: str = llm_config.sys_prompt
    temp: float = llm_config.openai_temp
    max_tokens: int = llm_config.openai_max_tokens

# 定义输出数据模型（新路由）
class BlockOutput(BaseModel):
    block_id: int
    keywords: list[str]

class DocumentOutput(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[BlockOutput]

# 获取 OpenAI 客户端
def get_openai_client(base_url: str, api_key: str) -> OpenAI:
    logger.info(f"Initializing OpenAI client with base_url: {base_url}")
    return OpenAI(base_url=base_url, api_key=api_key)

# 获取 AI 响应的函数
def get_ai_response(
    model: str = llm_config.openai_model,
    client: OpenAI = client,
    use_stream: bool = llm_config.openai_use_stream,
    sys_prompt: str = llm_config.sys_prompt,
    req_prompt: str = "tell me a story",
    temp: float = llm_config.openai_temp,
    max_tokens: int = llm_config.openai_max_tokens
) -> str:
    logger.info(f"Requesting AI response with model: {model}, stream: {use_stream}")
    try:
        request_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": req_prompt}
            ],
            "temperature": temp,
            "max_tokens": max_tokens,
            "stream": use_stream
        }
        logger.debug(f"Request params: {request_params}")
        response = client.chat.completions.create(**request_params, timeout=300)
        logger.info("AI response received successfully")
        if use_stream:
            full_response = []
            for chunk in response:
                if chunk.choices[0].delta.content:
                    chunk_text = chunk.choices[0].delta.content
                    logger.debug(f"Stream chunk: {chunk_text}")
                    full_response.append(chunk_text)
            return ''.join(full_response)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Request failed, error type: {type(e).__name__}, details: {str(e)}")
        if isinstance(e, (ConnectionError, TimeoutError)):
            logger.warning("Connection error detected, attempting to reconnect...")
            time.sleep(2)
            return get_ai_response(model, client, use_stream, sys_prompt, req_prompt, temp, max_tokens)
        return None

# 提取并过滤关键词的函数
# def filter_keywords(response: str, n: int = llm_config.keyWordCount) -> list[str]:
#     if response:
#         try:
#             list_pattern = r"\['.*?'\](?=\s|$)"
#             match = re.search(list_pattern, response, re.DOTALL)
#             if not match:
#                 logger.warning(f"No Python list format found in response: {response}")
#                 return ["error"] * n
            
#             list_str = match.group(0)
#             keywords = ast.literal_eval(list_str)
#             if not isinstance(keywords, list):
#                 logger.error(f"Parsed result is not a list: {list_str}")
#                 return ["error"] * n

#             filtered_keywords = []
#             for word in keywords:
#                 if not isinstance(word, str):
#                     continue
#                 word = word.strip().lower()
#                 if re.match(r'^[a-z0-9]+$', word):
#                     filtered_keywords.append(word)
            
#             if len(filtered_keywords) < n:
#                 logger.info(f"Insufficient keywords ({len(filtered_keywords)}/{n}): {filtered_keywords}")
#                 filtered_keywords.extend(["default"] * (n - len(filtered_keywords)))
#             logger.info(f"Filtered keywords: {filtered_keywords}")
#             return filtered_keywords[:n]
#         except Exception as e:
#             logger.error(f"Parsing failed: {e}")
#             return ["error"] * n
#     logger.warning("No response provided, returning default keywords")
#     return ["default"] * n
def filter_keywords(response: str, n: int = llm_config.keyWordCount) -> list[str]:
    if not response:
        logger.warning("No response provided, returning empty list")
        return []
    
    try:
        list_pattern = r"\['.*?'\](?=\s|$)"
        match = re.search(list_pattern, response, re.DOTALL)
        if not match:
            logger.warning(f"No Python list format found in response: {response}")
            return []
        
        list_str = match.group(0)
        keywords = ast.literal_eval(list_str)
        if not isinstance(keywords, list):
            logger.error(f"Parsed result is not a list: {list_str}")
            return []

        filtered_keywords = []
        for word in keywords:
            if not isinstance(word, str):
                continue
            word = word.strip().lower()
            if re.match(r'^[a-z0-9]+$', word):
                filtered_keywords.append(word)
        
        logger.info(f"Filtered keywords: {filtered_keywords[:n]}")
        return filtered_keywords[:n]  # 只返回前 n 个有效关键词，不补齐 default
    
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        return []

# 调用大模型生成关键字的函数
def query_llm(
    req_prompt: str,
    keyword_count: int = llm_config.keyWordCount,
    model: str = llm_config.openai_model,
    client: OpenAI = client,
    use_stream: bool = llm_config.openai_use_stream,
    sys_prompt: str = llm_config.sys_prompt,
    temp: float = llm_config.openai_temp,
    max_tokens: int = llm_config.openai_max_tokens
) -> list[str]:
    logger.info(f"Querying LLM with prompt: {req_prompt[:50]}... and keyword_count: {keyword_count}")
    response = get_ai_response(
        model=model,
        client=client,
        use_stream=use_stream,
        sys_prompt=sys_prompt,
        req_prompt=req_prompt,
        temp=temp,
        max_tokens=max_tokens
    )
    if response is None:
        logger.error(f"LLM query failed, returning {keyword_count} error keywords")
        return ["error"] * keyword_count
    return filter_keywords(response, n=keyword_count)

# FastAPI 路由：提取关键词，支持所有参数
@app.post("/extract_keywords/", response_model=dict)
async def extract_keywords(request: ExtractRequest):
    logger.info(f"Received request: text length={len(request.text)}, keyword_count={request.keyword_count}")
    req_prompt = f"Extract the top {request.keyword_count} keywords from this text: {request.text}in a Python flist format, e.g., ['key1', 'key2', 'key3', ...]."
    keywords = query_llm(
        req_prompt=req_prompt,
        keyword_count=request.keyword_count,
        model=request.model,
        client=client,
        use_stream=request.use_stream,
        sys_prompt=request.sys_prompt,
        temp=request.temp,
        max_tokens=request.max_tokens
    )
    
    if keywords == [] :
        logger.error("Keyword extraction failed")
        raise HTTPException(status_code=500, detail="Failed to extract keywords from the model")
    
    logger.info(f"Returning keywords: {keywords}")
    return {"keywords": keywords}

# # 新路由：处理块类型并提取关键词
# @app.post("/extract-block-keywords/", response_model=DocumentOutput)
# async def extract_block_keywords(request: DocumentInput):
#     """
#     从分块文本中提取关键词并存入 Kafka
#     """
#     logger.info(f"Received request for doc_id: {request.doc_id}")
    
#     try:
#         if len(request.blocks) != request.total_blocks:
#             raise ValueError("Number of blocks does not match total_blocks")
        
#         blocks = [block.model_dump() for block in request.blocks]
#         output_blocks = []
        
#         for block in blocks:
#             req_prompt = f"Extract the top {request.keyword_count} keywords from this text: {block['content']}"
#             keywords = query_llm(
#                 req_prompt=req_prompt,
#                 keyword_count=request.keyword_count,
#                 model=request.model,
#                 client=client,
#                 use_stream=request.use_stream,
#                 sys_prompt=request.sys_prompt,
#                 temp=request.temp,
#                 max_tokens=request.max_tokens
#             )
#             if keywords == ["error"] * request.keyword_count:
#                 raise ValueError(f"Failed to extract keywords for block {block['block_id']}")
            
#             output_blocks.append({
#                 "block_id": block["block_id"],
#                 "keywords": keywords
#             })
        
#         response = {
#             "doc_id": request.doc_id,
#             "total_blocks": request.total_blocks,
#             "blocks": output_blocks
#         }
        
#         producer.send(kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS, value=response)
#         logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: {request.doc_id}")
        
#         return response
    
#     except ValueError as e:
#         logger.error(f"Validation error: {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"Internal error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/extract-block-keywords/", response_model=DocumentOutput)
async def extract_block_keywords(request: DocumentInput):
    """
    从分块文本中提取关键词并存入 Kafka，跳过无效 block 并调整 total_blocks
    """
    logger.info(f"Received request for doc_id: {request.doc_id}")
    
    try:
        if len(request.keys) != request.total_blocks:
            raise ValueError("Number of blocks does not match total_blocks")
        
        blocks = [block.model_dump() for block in request.keys]
        output_blocks = []
        valid_block_count = request.total_blocks  # 初始化为原始总数
        
        for block in blocks:
            req_prompt = f"Extract the top {request.keyword_count} keywords from this text: {block['content']}"
            keywords = query_llm(
                req_prompt=req_prompt,
                keyword_count=request.keyword_count,
                model=request.model,
                client=client,
                use_stream=request.use_stream,
                sys_prompt=request.sys_prompt,
                temp=request.temp,
                max_tokens=request.max_tokens
            )
            # 如果 keywords 为空（即未生成合法数组），跳过该 block 并减少计数
            if not keywords:
                logger.warning(f"Skipping block {block['block_id']} due to invalid or empty keyword list")
                valid_block_count -= 1  # 跳过后减少有效 block 总数
                continue
            
            output_blocks.append({
                "block_id": block["block_id"],
                "keywords": keywords
            })
        
        if not output_blocks:
            logger.warning(f"No valid blocks processed for doc_id: {request.doc_id}")
            raise ValueError("No valid blocks with keywords extracted")
        
        response = {
            "doc_id": request.doc_id,
            "total_blocks": valid_block_count,  # 使用调整后的有效 block 数
            "blocks": output_blocks
        }
        
        producer.send(kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS, value=response)
        logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# # Kafka 生产者：发送分块文本数据
# def produce_block_data(doc_id: str, blocks: list[dict]):
#     data = {
#         "doc_id": doc_id,
#         "total_blocks": len(blocks),
#         "blocks": blocks
#     }
#     producer.send(kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS, value=data)
#     logger.info(f"Produced data to Kafka topic {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}: {doc_id}")

# # Kafka 消费者：处理分块文本并生产关键词数据
# def consume_and_process():
#     logger.info(f"Starting Kafka consumer for topic: {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}")
#     for message in consumer:
#         data = message.value
#         logger.info(f"Consumed message from Kafka topic {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}: doc_id={data['doc_id']}")
        
#         try:
#             if len(data["blocks"]) != data["total_blocks"]:
#                 raise ValueError("Number of blocks does not match total_blocks")
            
#             output_blocks = []
#             for block in data["blocks"]:
#                 req_prompt = f"Extract the top {llm_config.keyWordCount} keywords from this text: {block['content']}"
#                 keywords = query_llm(req_prompt)
#                 if keywords == ["error"] * llm_config.keyWordCount:
#                     raise ValueError(f"Failed to extract keywords for block {block['block_id']}")
                
#                 output_blocks.append({
#                     "block_id": block["block_id"],
#                     "keywords": keywords
#                 })
            
#             response = {
#                 "doc_id": data["doc_id"],
#                 "total_blocks": data["total_blocks"],
#                 "blocks": output_blocks
#             }
            
#             producer.send(kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS, value=response)
#             logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: {data['doc_id']}")
        
#         except ValueError as e:
#             logger.error(f"Processing error for doc_id {data['doc_id']}: {str(e)}")
#         except Exception as e:
#             logger.error(f"Internal error for doc_id {data['doc_id']}: {str(e)}")

# Kafka 生产者：发送分块文本数据
def produce_block_data(doc_id: str, blocks: list[dict]):
    # 过滤掉无效的 block（例如 content 为空的情况），并计算有效 block 数量
    valid_blocks = [block for block in blocks if block.get("content")]  # 假设 content 是必须字段
    data = {
        "doc_id": doc_id,
        "total_blocks": len(valid_blocks),  # 使用实际有效 block 数量
        "blocks": valid_blocks
    }
    producer.send(kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS, value=data)
    logger.info(f"Produced data to Kafka topic {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}: {doc_id}, total_blocks={len(valid_blocks)}")

# Kafka 消费者：处理分块文本并生产关键词数据
def consume_and_process():
    logger.info(f"Starting Kafka consumer for topic: {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}")
    for message in consumer:
        data = message.value
        logger.info(f"Consumed message from Kafka topic {kafka_config.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}: doc_id={data['doc_id']}")
        
        try:
            if len(data["blocks"]) != data["total_blocks"]:
                raise ValueError("Number of blocks does not match total_blocks")
            
            output_blocks = []
            valid_block_count = data["total_blocks"]  # 初始化为原始总数
            
            for block in data["blocks"]:
                req_prompt = f"Extract the top {llm_config.keyWordCount} keywords from this text: {block['content']}"
                keywords = query_llm(req_prompt)
                # 如果 keywords 为空（与之前的 filter_keywords 逻辑一致），跳过该 block
                if not keywords:
                    logger.warning(f"Skipping block {block['block_id']} due to invalid or empty keyword list")
                    valid_block_count -= 1  # 跳过后减少有效 block 总数
                    continue
                
                output_blocks.append({
                    "block_id": block["block_id"],
                    "keywords": keywords
                })
            
            if not output_blocks:
                logger.warning(f"No valid blocks processed for doc_id: {data['doc_id']}")
                continue  # 如果没有有效 block，跳过本次消息处理
            
            response = {
                "doc_id": data["doc_id"],
                "total_blocks": valid_block_count,  # 使用调整后的有效 block 数
                "blocks": output_blocks
            }
            
            producer.send(kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS, value=response)
            logger.info(f"Processed and sent to Kafka topic {kafka_config.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}: {data['doc_id']}, total_blocks={valid_block_count}")
        
        except ValueError as e:
            logger.error(f"Validation error for doc_id {data['doc_id']}: {str(e)}")
        except Exception as e:
            logger.error(f"Internal error for doc_id {data['doc_id']}: {str(e)}")

# 启动函数（用于本地测试）
# main_with_kafka.py
if __name__ == "__main__":
    import uvicorn
    from threading import Thread
    
    # 示例生产者数据
    # sample_blocks = [
    #     {"block_id": 1, "content": "AI and machine learning are transforming tech."},
    #     {"block_id": 2, "content": "Machine learning news is trending today."},
    #     {"block_id": 3, "content": "Tech data drives innovation."}
    # ]
    # produce_block_data("doc_001", sample_blocks)
    
    # 启动消费者线程
    consumer_thread = Thread(target=consume_and_process)
    consumer_thread.daemon = True
    consumer_thread.start()
    
    # 启动 FastAPI 服务
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=9001)