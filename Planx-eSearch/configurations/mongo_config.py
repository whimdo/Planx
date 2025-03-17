import os

class MongoConfig:
    # MongoDB 配置
    MONGO_HOST = '192.168.1.204'
    MONGO_PORT = 27017
    MONGO_DB = 'telegram'
    MONGO_COLLECTION = 'groupinfo'


    def __str__(self):
        """返回配置的字符串表示，便于调试"""
        return (
            f"MongoConfig(HOST={self.MONGO_HOST}, "
            f"port=[{self.MONGO_PORT}, "
            f"{self.MONGO_DB}, "
            f"{self.MONGO_COLLECTION}, "
        )