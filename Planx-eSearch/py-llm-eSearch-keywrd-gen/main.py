import ast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import time
import re
import json
from kafka import KafkaProducer,KafkaConsumer
from config.llm_config import llm_Config as Config
from config.llm_config import setup_logging

# 初始化日志
logger = setup_logging(log_file="keyword_extraction.log", log_level="INFO")

# 初始化 FastAPI 应用和 Config
app = FastAPI(
    title="Keyword Extraction API",
    description="API for extracting keywords from text using a language model",
    version="1.0.0"
)
config = Config()
client = OpenAI(base_url=config.openai_base_url, api_key=config.openai_api_key)




# 定义请求数据模型，扩展支持所有参数
class ExtractRequest(BaseModel):
    text: str
    keyword_count: int = config.keyWordCount
    model: str = config.openai_model
    use_stream: bool = config.openai_use_stream
    sys_prompt: str = config.sys_prompt
    temp: float = config.openai_temp
    max_tokens: int = config.openai_max_tokens

# 定义请求数据模型（新路由：处理块类型）
class BlockInput(BaseModel):
    block_id: int
    content: str
    

class DocumentInput(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: list[BlockInput]
    keyword_count: int = config.keyWordCount
    model: str = config.openai_model
    use_stream: bool = config.openai_use_stream
    sys_prompt: str = config.sys_prompt
    temp: float = config.openai_temp
    max_tokens: int = config.openai_max_tokens

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
    model: str = config.openai_model,
    client: OpenAI = client,
    use_stream: bool = config.openai_use_stream,
    sys_prompt: str = config.sys_prompt,
    req_prompt: str = "tell me a story",
    temp: float = config.openai_temp,
    max_tokens: int = config.openai_max_tokens
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
# 提取并过滤关键词的函数
def filter_keywords(response: str, n: int = config.keyWordCount) -> list[str]:
    if response:
        try:
            list_pattern = r"\['.*?'\](?=\s|$)"
            match = re.search(list_pattern, response, re.DOTALL)
            if not match:
                logger.warning(f"No Python list format found in response: {response}")
                return ["error"] * n
            
            list_str = match.group(0)
            # keywords = eval(list_str)  # 注意：建议用 ast.literal_eval 替代 eval
            keywords = ast.literal_eval(list_str)
            if not isinstance(keywords, list):
                logger.error(f"Parsed result is not a list: {list_str}")
                return ["error"] * n

            filtered_keywords = []
            for word in keywords:
                if not isinstance(word, str):
                    continue
                word = word.strip().lower()
                if re.match(r'^[a-z0-9]+$', word):
                    filtered_keywords.append(word)
            
            if len(filtered_keywords) < n:
                logger.info(f"Insufficient keywords ({len(filtered_keywords)}/{n}): {filtered_keywords}")
                filtered_keywords.extend(["default"] * (n - len(filtered_keywords)))
            logger.info(f"Filtered keywords: {filtered_keywords}")
            return filtered_keywords[:n]
            
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            return ["error"] * n
    logger.warning("No response provided, returning default keywords")
    return ["default"] * n

# 调用大模型生成关键字的函数，将所有参数传递
def query_llm(
    req_prompt: str,
    keyword_count: int = config.keyWordCount,
    model: str = config.openai_model,
    client: OpenAI = client,
    use_stream: bool = config.openai_use_stream,
    sys_prompt: str = config.sys_prompt,
    temp: float = config.openai_temp,
    max_tokens: int = config.openai_max_tokens
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
    req_prompt = f"Extract the top {request.keyword_count} keywords from this text: {request.text}"
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
    
    if keywords == ["error"] * request.keyword_count:
        logger.error("Keyword extraction failed")
        raise HTTPException(status_code=500, detail="Failed to extract keywords from the model")
    
    logger.info(f"Returning keywords: {keywords}")
    return {"keywords": keywords}

# 新路由：处理块类型并提取关键词
@app.post("/extract-block-keywords/", response_model=DocumentOutput)
async def extract_block_keywords(request: DocumentInput):
    """
    从分块文本中提取关键词并存入 Kafka
    """
    logger.info(f"Received request for doc_id: {request.doc_id}")
    
    try:
        if len(request.blocks) != request.total_blocks:
            raise ValueError("Number of blocks does not match total_blocks")
        
        blocks = [block.model_dump() for block in request.blocks]
        output_blocks = []
        
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
            if keywords == ["error"] * config.keyWordCount:
                raise ValueError(f"Failed to extract keywords for block {block['block_id']}")
            
            output_blocks.append({
                "block_id": block["block_id"],
                "keywords": keywords
            })
        
        response = {
            "doc_id": request.doc_id,
            "total_blocks": request.total_blocks,
            "blocks": output_blocks
        }
        
        #producer.send('kywrd2vec', value=response)
        logger.info(f"Processed and sent to Kafka: {request.doc_id}")
        
        return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    


# 启动函数（用于本地测试）
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8002)