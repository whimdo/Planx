from googlesearch import search
import sys

def get_google_search_urls(query, num_results=10):
    """
    从Google搜索中获取前num_results条结果的URL
    :param query: 搜索关键词 (string)
    :param num_results: 获取的结果数量，默认10
    :return: URL列表 (list of strings)
    """
    try:
        # 使用googlesearch库进行搜索
        urls = []
        for url in search(query, num_results=num_results, lang="en"):
            urls.append(url)
        
        return urls
    
    except Exception as e:
        print(f"发生错误: {str(e)}", file=sys.stderr)
        return []

# 示例使用
if __name__ == "__main__":
    # 搜索关键词
    search_query = "site:t.me crypto https://t.me"
    
    # 获取搜索结果URL
    result_urls = get_google_search_urls(search_query)
    
    # 打印结果
    print("前10条搜索结果URL:")
    for i, url in enumerate(result_urls, 1):
        print(f"{i}. {url}")
    
    # 验证结果是一个字符串数组
    print("\n结果类型:", type(result_urls))
    print("第一个元素类型:", type(result_urls[0]) if result_urls else None)