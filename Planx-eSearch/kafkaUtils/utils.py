from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self, bootstrap_servers='192.168.6.188:9092'):
        """
        初始化 Kafka 客户端
        :param bootstrap_servers: Kafka 服务器地址，默认为
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self._monitor_consumer = None  # 存储 monitor_topic 的消费者实例
        self._monitoring = False  # 用于控制 monitor_topic 的运行状态

    def initialize_admin_client(self):
        """初始化 Kafka Admin 客户端，用于管理主题等操作"""
        try:
            self.admin_client = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
            logger.info("Kafka Admin Client initialized successfully.")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka Admin Client: {e}")
            raise

    def create_topic(self, topic_name, num_partitions=1, replication_factor=1):
        """
        创建 Kafka 主题
        :param topic_name: 主题名称
        :param num_partitions: 分区数
        :param replication_factor: 副本因子
        """
        if not self.admin_client:
            self.initialize_admin_client()

        topic_list = [NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor)]
        try:
            self.admin_client.create_topics(new_topics=topic_list, validate_only=False)
            logger.info(f"Topic '{topic_name}' created successfully.")
        except KafkaError as e:
            logger.error(f"Failed to create topic '{topic_name}': {e}")
            raise

    def initialize_producer(self, value_serializer=lambda x: json.dumps(x).encode('utf-8')):
        """
        初始化 Kafka 生产者
        :param value_serializer: 值序列化方法，默认将字典转为 JSON 字符串并编码为 UTF-8
        """
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=value_serializer
            )
            logger.info("Kafka Producer initialized successfully.")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            raise

    def send_message(self, topic, value, key=None):
        """
        发送消息到指定主题
        :param topic: 目标主题
        :param value: 消息值
        :param key: 消息键，可选
        """
        if not self.producer:
            self.initialize_producer()

        try:
            # 如果提供了 key，则需要将其编码为字节
            key_bytes = key.encode('utf-8') if key else None
            future = self.producer.send(topic, value=value, key=key_bytes)
            result = future.get(timeout=10)  # 等待消息发送完成
            logger.info(f"Message sent to {topic}, key: {key}, partition: {result.partition}")
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            raise

    def initialize_consumer(self, topics, group_id=None, auto_offset_reset='earliest'):
        """
        初始化 Kafka 消费者
        :param topics: 要订阅的主题列表
        :param group_id: 消费者组 ID，可选
        :param auto_offset_reset: 偏移量重置策略，'earliest' 或 'latest'
        """
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info(f"Kafka Consumer initialized for topics: {topics}")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka Consumer: {e}")
            raise

    def consume_messages(self):
        """
        消费消息并打印
        :return: 生成器，逐条返回消息
        """
        if not self.consumer:
            raise ValueError("Consumer not initialized. Call initialize_consumer first.")

        try:
            for message in self.consumer:
                yield {
                    'topic': message.topic,
                    'partition': message.partition,
                    'offset': message.offset,
                    'key': message.key.decode('utf-8') if message.key else None,
                    'value': message.value
                }
        except KafkaError as e:
            logger.error(f"Error while consuming messages: {e}")
            raise

    def monitor_topic(self, topic, callback=None, partition=None, group_id=None, auto_offset_reset='latest'):
        """
        实时监测指定主题或分区的新消息，并立即消费
        :param topic: 要监测的主题
        :param callback: 处理 message 的回调函数，可选
        :param partition: 指定分区号（可选），若不指定则监测整个主题
        :param group_id: 消费者组 ID，默认 None
        :param auto_offset_reset: 偏移量重置策略，默认 'latest'（只消费新消息）
        """
        if self._monitoring:
            logger.warning("Already monitoring a topic. Call stop_monitoring() first.")
            return

        def safe_deserialize(bytes_data):
            """安全反序列化字节数据，失败时返回原始数据"""
            if bytes_data is None:
                logger.warning("Received message with None value")
                return None
            try:
                return json.loads(bytes_data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to deserialize message as JSON: {bytes_data!r}, error: {e}")
                # 尝试解码为字符串，失败则返回原始字节
                try:
                    return bytes_data.decode('utf-8')
                except UnicodeDecodeError:
                    return bytes_data

        try:
            # 初始化消费者，使用安全的反序列化函数
            self._monitor_consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=safe_deserialize
            )
            logger.info(f"Starting to monitor topic: {topic}, partition: {partition if partition is not None else 'all'}")

            # 如果指定了分区，则只订阅该分区
            if partition is not None:
                from kafka import TopicPartition
                tp = TopicPartition(topic, partition)
                self._monitor_consumer.assign([tp])
                logger.info(f"Assigned to partition {partition} of topic {topic}")

            # 设置监测标志
            self._monitoring = True

            # 持续轮询新消息，直到被停止
            while self._monitoring:
                messages = self._monitor_consumer.poll(timeout_ms=1000)  # 每秒轮询一次
                if not messages:
                    logger.debug(f"No new messages in {topic}")
                    continue

                for tp, msg_list in messages.items():
                    for message in msg_list:
                        msg_info = {
                            'topic': message.topic,
                            'partition': message.partition,
                            'offset': message.offset,
                            'key': message.key.decode('utf-8') if message.key else None,
                            'value': message.value  # 使用 safe_deserialize 的结果
                        }
                        logger.info(f"New message received: {msg_info}")
                        print(f"Consumed new message: {msg_info}")
                        value = message.value
                    if isinstance(value, dict) and "message" in value:
                        message_content = value["message"]
                    else:
                        message_content = value
                    if callback:
                        callback(message_content)

        except KafkaError as e:
            logger.error(f"Error while monitoring topic {topic}: {e}")
            raise
        finally:
            if self._monitor_consumer:
                self._monitor_consumer.close()
                self._monitor_consumer = None
            self._monitoring = False
            logger.info("Monitor consumer closed.")

    def stop_monitoring(self):
        """
        停止 monitor_topic 的监测
        """
        if not self._monitoring:
            logger.info("No monitoring in progress.")
            return

        self._monitoring = False
        logger.info("Stopping topic monitoring...")

    def close(self):
        """关闭生产者和消费者连接"""
        try:
            logger.info("Closing all Kafka connections...")
            # 停止 monitor_topic（如果正在运行）
            if self._monitoring:
                self.stop_monitoring()
                # 等待 monitor_topic 的 finally 块执行完成
                import time
                time.sleep(1)  # 短暂等待，确保消费者关闭

            # 关闭生产者
            if self.producer:
                self.producer.close()
                self.producer = None
                logger.info("Kafka Producer closed.")

            # 关闭消费者
            if self.consumer:
                self.consumer.close()
                self.consumer = None
                logger.info("Kafka Consumer closed.")

            # 关闭 Admin 客户端
            if self.admin_client:
                self.admin_client.close()
                self.admin_client = None
                logger.info("Kafka Admin Client closed.")

            logger.info("All Kafka connections closed.")
        except:
            logger.error("All Kafka connections failed to close.")
            raise

# 使用示例
if __name__ == "__main__":
    # 创建 Kafka 客户端实例
    kafka = KafkaClient(bootstrap_servers='192.168.1.206:9092')

    # # 创建一个主题
    # kafka.create_topic("useact", num_partitions=2, replication_factor=1)

    # # 初始化生产者并发送消息
    # kafka.initialize_producer()
    # kafka.send_message("useact", {"message": "Hello Kafka!"}, key="key1")
    # kafka.send_message("useact", {"message": "Another message"}, key="key2")

    # # 初始化消费者并消费消息
    # kafka.initialize_consumer(["useact"], group_id="my-group")
    # for msg in kafka.consume_messages():
    #     print(f"Received: {msg}")
    def handle_message(msg):
        print(f"Handling: {msg}")
    kafka.monitor_topic("useact",handle_message)

    # 关闭连接
    kafka.close()