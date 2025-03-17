# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import logging
import os
from getUrlList import get_google_search_urls  # 导入搜索模块
from crawlerToTxt import join_and_fetch_group_info,split_content_into_blocks

# 确保 log 目录存在
log_dir = "log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(log_dir, 'crawler.log'),
    filemode='a'  
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 实例
app = FastAPI(
    title="Crawler API",
    description="一个用于搜索和爬取的API服务",
    version="1.0.0"
)

# 定义搜索请求的 Pydantic 模型
class SearchRequest(BaseModel):
    query: str
    num_results: int = 10

# 定义请求体的 Pydantic 模型
class CrawlRequest(BaseModel):
    url: str
    messageNum: int = 10

class SplitRequest(BaseModel):
    doc_id: str
    content: str
    max_block_size: int = 7000
class Block(BaseModel):
    block_id: int
    content: str
# 定义输出数据模型
class SplitResponse(BaseModel):
    doc_id: str
    total_blocks: int
    blocks: List[Block]

class StreamRequest(BaseModel):
    url: str
    messageNum: int=None
    max_block_size: int=5000
# 搜索接口
@app.post("/search", response_model=List[str])
async def search_urls(request: SearchRequest):
    """
    根据用户提供的JSON数据搜索Google并返回URL列表
    :param request: JSON请求体，包含query和num_results
    :return: URL列表 (list of strings)
    """
    if not request.query:
        logger.error("搜索关键词为空")
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    
    if request.num_results <= 0:
        logger.error(f"无效的结果数量: {request.num_results}")
        raise HTTPException(status_code=400, detail="结果数量必须大于0")

    result_urls = get_google_search_urls(request.query, request.num_results)
    
    if not result_urls:
        logger.warning(f"未找到任何结果: query={request.query}, num_results={request.num_results}")
    
    return result_urls

#获取信息接口
@app.post("/crawl")
async def crawl_telegram(request: CrawlRequest):
    """
    根据用户提供的JSON数据爬取Telegram群组信息
    :param request: JSON请求体，包含url和messageNum
    :return: JSON格式的字符串
    """
    if not request.url:
        logger.error("URL为空")
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    if request.messageNum <= 0:
        logger.error(f"无效的消息条数: {request.messageNum}")
        raise HTTPException(status_code=400, detail="消息条数必须大于0")

    try:
        logger.info(f"开始爬取: url={request.url}, messageNum={request.messageNum}")
        result = await join_and_fetch_group_info(request.url, request.messageNum)
        logger.info(f"爬取完成: url={request.url}")
        return result
    except Exception as e:
        logger.error(f"爬取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")

# 定义 API 端点
@app.post("/split")
async def split_content_endpoint(request: SplitRequest):
    """
    将输入的内容按指定大小分块。
    
    参数:
        input_data: 包含 doc_id 和 content 的 JSON 数据
    
    返回:
        分块后的结构化数据
    """
    if not request.doc_id:
        logger.error("doc_id 为空")
        raise HTTPException(status_code=400, detail="doc_id 不能为空")
    
    if not request.content:
        logger.error("content 为空")
        raise HTTPException(status_code=400, detail="content 不能为空")
    
    if request.max_block_size <= 0:
        logger.error(f"无效的分块大小: {request.max_block_size}")
        raise HTTPException(status_code=400, detail="分块大小必须大于0")

    try:
        logger.info(f"开始分块: doc_id={request.doc_id}, max_block_size={request.max_block_size}")
        # 将请求转换为字典并调用分块函数
        data_dict = request.model_dump()
        result = split_content_into_blocks(data_dict, max_block_size=request.max_block_size)
        logger.info(f"分块完成: doc_id={request.doc_id}, total_blocks={result['blocks']}")
        return result
    except Exception as e:
        logger.error(f"分块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分块失败: {str(e)}")

# 合并crawler和split接口
@app.post("/stream")
async def stream_endpoint(request: StreamRequest):
    """
    先爬取 Telegram 群组信息，然后将结果按指定大小分块。
    doc_id 由爬取函数生成。
    
    参数:
        request: JSON 请求体，包含 url, messageNum 和 max_block_size
    
    返回:
        分块后的结构化数据
    """
    # 验证参数
    if not request.url:
        logger.error("URL 为空")
        raise HTTPException(status_code=400, detail="URL 不能为空")
    
    if  request.messageNum is not None and request.messageNum <= 0:
        logger.error(f"无效的消息条数: {request.messageNum}")
        raise HTTPException(status_code=400, detail="消息条数必须大于0")
    
    if request.max_block_size <= 0:
        logger.error(f"无效的分块大小: {request.max_block_size}")
        raise HTTPException(status_code=400, detail="分块大小必须大于0")

    try:
        # 第一步：爬取 Telegram 数据
        logger.info(f"开始爬取: url={request.url}, messageNum={request.messageNum}")
        crawl_result = await join_and_fetch_group_info(request.url, request.messageNum)
        logger.info(f"爬取完成: url={request.url}")

        # 验证爬取结果
        if "doc_id" not in crawl_result or not crawl_result["doc_id"]:
            logger.error("爬取结果中 doc_id 为空")
            raise HTTPException(status_code=500, detail="爬取结果中 doc_id 为空")
        
        if "content" not in crawl_result or not crawl_result["content"]:
            logger.error("爬取结果中 content 为空")
            raise HTTPException(status_code=500, detail="爬取结果中 content 为空")

        # 第二步：准备分块数据
        split_data = {
            "doc_id": crawl_result["doc_id"],  # 从爬取结果中获取 doc_id
            "content": crawl_result["content"],
            "max_block_size": request.max_block_size
        }

        # 第三步：执行分块
        logger.info(f"开始分块: doc_id={split_data['doc_id']}, max_block_size={request.max_block_size}")
        result = split_content_into_blocks(split_data, max_block_size=request.max_block_size)
        logger.info(f"分块完成: doc_id={split_data['doc_id']}, total_blocks={len(result['blocks'])}")
        return result

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

# 运行服务
if __name__ == "__main__":
    import uvicorn
    logger.info("启动 FastAPI 服务...")
    uvicorn.run(app, host="0.0.0.0", port=9099)