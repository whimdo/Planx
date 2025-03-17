import os

class MilvusConfig:
    """Milvus 相关配置"""
    MILVUS_HOST = os.getenv("MILVUS_HOST", "192.168.1.209")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION_NAME = "documentvectors310"

    def __str__(self):
        """返回配置的字符串表示，便于调试"""
        return (
            f"MilvusConfig(host={self.MILVUS_HOST}, "
            f"port={self.MILVUS_PORT}, "
            f"collection_name={self.MILVUS_COLLECTION_NAME})"
        )

# 全局 Milvus 配置实例
milvus_config = MilvusConfig()