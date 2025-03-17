import requests
import time
import json
import logging
import os

# 配置参数
URL_FILE = "url.txt"        # 存储URL的文本文件路径
API_URL = "http://192.168.1.208:9099/stream/"
SEND_INTERVAL = 1          # 请求间隔时间（秒）
MAX_BLOCK_SIZE = 5000       # 固定参数

headers = {
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Host': '192.168.1.208:9099',
    'Connection': 'keep-alive',
    'Referer': 'http://192.168.1.208:9099/stream/'
}

# 配置日志
log_dir = "log"  # 日志文件夹名称
log_file = os.path.join(log_dir, "scripts.log")  # 日志文件路径：log/scripts.log

# 如果 log 文件夹不存在，则创建
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    logging.info(f"创建日志目录: {log_dir}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # 输出到 log/scripts.log 文件
        logging.StreamHandler()         # 同时输出到终端
    ]
)

def load_urls(filename):
    """从文本文件加载URL列表"""
    try:
        with open(filename, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
            logging.info(f"成功加载 {len(urls)} 个URL")
            return urls
    except FileNotFoundError:
        logging.error(f"错误：文件 {filename} 未找到")
        exit(1)

def save_urls(filename, urls):
    """将剩余的URL保存回文件"""
    with open(filename, 'w') as f:
        for url in urls:
            f.write(url + '\n')

def send_request(url):
    """发送POST请求"""
    payload = {
        "url": url,
        "max_block_size": MAX_BLOCK_SIZE
    }
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        logging.info(f"请求成功 | URL: {url} | 状态码: {response.status_code}")
        return True  # 返回成功标志
    except Exception as e:
        logging.error(f"请求失败 | URL: {url} | 错误: {str(e)}")
        return False  # 返回失败标志

if __name__ == "__main__":
    urls = load_urls(URL_FILE)
    
    while urls:  # 当urls列表不为空时继续循环
        url = urls[0]  # 取第一个URL
        if send_request(url):  # 如果请求成功
            urls.pop(0)  # 删除已使用的URL
            save_urls(URL_FILE, urls)  # 更新文件内容
            logging.info(f"剩余URL数量: {len(urls)}")
        time.sleep(SEND_INTERVAL)  # 每次请求后等待指定时间
    
    logging.info("所有URL已处理完成")