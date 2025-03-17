from pydantic import BaseModel
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode
import base62
import logging
import os

# 配置日志
LOG_DIR = "log"  # 日志目录，可根据需要修改
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/keyid.log"),  # 输出到文件
        logging.StreamHandler()  # 同时输出到终端（可选）
    ]
)
logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """
    规范化 URL，确保相同语义的 URL 生成一致的标识符，包括片段部分。
    """
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL: scheme or netloc missing")
    
    # 规范化 scheme 和 netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.endswith(':80') and scheme == 'http':
        netloc = netloc[:-3]
    elif netloc.endswith(':443') and scheme == 'https':
        netloc = netloc[:-4]
    
    # 规范化 path，去除末尾斜杠
    path = parsed.path.rstrip('/')
    
    # 规范化 query，按参数排序
    query_dict = parse_qs(parsed.query)
    sorted_query = urlencode(sorted(query_dict.items()), doseq=True)
    
    # 规范化 fragment，保留原始值
    fragment = parsed.fragment
    
    # 构建规范化 URL
    normalized = f"{scheme}://{netloc}{path}"
    if sorted_query:
        normalized += f"?{sorted_query}"
    if fragment:
        normalized += f"#{fragment}"
    
    return normalized

def url_to_unique_id(url: str, length: int = 8) -> str:
    """
    将 URL 转换为唯一标识符。
    """
    normalized_url = normalize_url(url)
    md5_hash = hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
    hash_int = int(md5_hash, 16)
    unique_id = base62.encode(hash_int)
    return unique_id[:length].rjust(length, '0')