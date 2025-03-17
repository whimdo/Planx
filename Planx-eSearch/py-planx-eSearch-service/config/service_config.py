class ServiceConfig:
    def __init__(
        self,
        extract_keywords_url: str = "http://192.168.1.208:9001/extract_keywords/",
        feature_vector_url: str = "http://192.168.1.208:9002/get_feature_vector_and_stats/",
        search_documents_url: str = "http://192.168.1.208:9004/search-documents/"
    ):
        """初始化服务配置类，保存每个服务的完整 URL。

        Args:
            extract_keywords_url (str): 提取关键词服务的完整 URL。
            feature_vector_url (str): 获取特征向量和统计信息的完整 URL。
            search_documents_url (str): 搜索文档的完整 URL。
        """
        self.extract_keywords_url = extract_keywords_url.rstrip('/')
        self.feature_vector_url = feature_vector_url.rstrip('/')
        self.search_documents_url = search_documents_url.rstrip('/')

    def update_urls(
        self,
        extract_keywords_url: str = None,
        feature_vector_url: str = None,
        search_documents_url: str = None
    ):
        """更新指定的服务 URL。

        Args:
            extract_keywords_url (str, optional): 新的提取关键词 URL。
            feature_vector_url (str, optional): 新的特征向量 URL。
            search_documents_url (str, optional): 新的搜索文档 URL。
        """
        if extract_keywords_url:
            self.extract_keywords_url = extract_keywords_url.rstrip('/')
        if feature_vector_url:
            self.feature_vector_url = feature_vector_url.rstrip('/')
        if search_documents_url:
            self.search_documents_url = search_documents_url.rstrip('/')

    def __str__(self):
        """返回配置的字符串表示，便于调试"""
        return (
            f"ServiceConfig(\n"
            f"  extract_keywords_url={self.extract_keywords_url},\n"
            f"  feature_vector_url={self.feature_vector_url},\n"
            f"  search_documents_url={self.search_documents_url}\n"
            f")"
        )