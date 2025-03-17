import os

class KafkaConfig:
    """Kafka 相关配置"""
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.1.206:9092")
    
    # Kafka 主题名
    KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS = "document-to-keywords"  # 文档到关键词
    KAFKA_TOPIC_KEYWORDS_TO_VECTORS = "keywords-to-vectors"    # 关键词到向量
    KAFKA_TOPIC_VECTORS_TO_SUMMARY = "vectors-to-summary"      # 向量到汇总
    KAFKA_TOPIC_SUMMARY_VECTORS = "summary-vectors"            # 汇总向量

    def __str__(self):
        """返回配置的字符串表示，便于调试"""
        return (
            f"KafkaConfig(bootstrap_servers={self.KAFKA_BOOTSTRAP_SERVERS}, "
            f"topics=[{self.KAFKA_TOPIC_DOCUMENT_TO_KEYWORDS}, "
            f"{self.KAFKA_TOPIC_KEYWORDS_TO_VECTORS}, "
            f"{self.KAFKA_TOPIC_VECTORS_TO_SUMMARY}, "
            f"{self.KAFKA_TOPIC_SUMMARY_VECTORS}])"
        )

# 全局 Kafka 配置实例
kafka_config = KafkaConfig()