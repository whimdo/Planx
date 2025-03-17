# `KafkaClient`使用

目前包装了初始化admin、producer、consumer客户端，生产消息，消费消息，轮询监测消费新消息等功能。

## 初始化kafkaClient类

```python
kafka = KafkaClient(bootstrap_servers='192.168.1.206:9092')
```

**参数**：bootstrap_servers:kafka服务器地址，默认设置为192.168.1.206:9092

## 类的方法

### initialize_admin_client

```python
def initialize_admin_client(self: Self@KafkaClient) -> None
```

**参数**：无

**返回值**：无

**功能**：初始化 Kafka Admin 客户端，用于管理主题等操作

### create_topic

```python
def create_topic(
    self: Self@KafkaClient,
    topic_name: Any,
    num_partitions: int = 1,
    replication_factor: int = 1
) -> None
```

**参数**：

topic_name:主题名字  

num_partitions:分区数 

replication_factor:副本数

**返回值**：无

**功能**：创建一个新的kafka主题

### initialize_producer

```python
def initialize_producer(
    self: Self@KafkaClient,
    value_serializer: Any = lambda x: json.dumps(x).encode('utf-8')
) -> None
```

**参数**：

value_serializer：规定序列化方法，默认将字典转换为json格式

**返回值**：无

**功能**：初始化生产者

### send_message

```python
def send_message(
    self: Self@KafkaClient,
    topic: Any,
    value: Any,
    key: Any | None = None
) -> None
```

**参数**：

 topic: 目标主题

 value: 消息值

 key: 消息键，可选

**返回值**：无

**功能**：发送消息到指定主题

### initialize_consumer

```python
def initialize_consumer(
    self: Self@KafkaClient,
    topics: Any,
    group_id: Any | None = None,
    auto_offset_reset: str = 'earliest'
) -> None
```

**参数**：

topics: 要订阅的主题列表

group_id: 消费者组 ID，可选

auto_offset_reset: 偏移量重置策略，'earliest' 或 'latest'，可选，默认为earliest

**返回值**：无

**功能**： 初始化 Kafka 消费者

### consume_messages

```python
def consume_messages(self: Self@KafkaClient) -> Generator[dict[str, Any], Any, None]
```

**参数**：无

**返回值**：生成器，逐条返回消息

**功能**：消费消息并打印

### monitor_topic

```python
def monitor_topic(
    self: Self@KafkaClient,
    topic: Any,
    callback: Any | None = None,
    partition: Any | None = None,
    group_id: Any | None = None,
    auto_offset_reset: str = 'latest'
) -> Any
```

**参数**：

topic: 要监测的主题

callback: 处理 message 的回调函数，可选，默认不使用则不做处理

partition: 指定分区号（可选），若不指定则监测整个主题

group_id: 消费者组 ID，默认 None

auto_offset_reset: 偏移量重置策略，默认 'latest'（只消费新消息）

**返回值**：无

**功能**：实时监测指定主题或者分区的新消息，并立即进行消费。

### stop_monitoring

```python
def stop_monitoring(self: Self@KafkaClient) -> None
```

**参数**：无

**返回值**：无

**功能**：停止检测

### close

```python
close(self: Self@KafkaClient) -> None
```

**参数**：无

**返回值**：无

**功能**：关闭生产者、消费者、admin，也可以终止检测。

## 使用案例

基本的生产者与消费者

```python
    kafka = KafkaClient(bootstrap_servers='192.168.1.206:9092')
    # 创建一个主题
    kafka.create_topic("useact", num_partitions=2, replication_factor=1)

    # 初始化生产者并发送消息
    kafka.initialize_producer()
    kafka.send_message("useact", {"message": "Hello Kafka!"}, key="key1")
    kafka.send_message("useact", {"message": "Another message"}, key="key2")

    # 初始化消费者并消费消息
    kafka.initialize_consumer(["useact"], group_id="my-group")
    for msg in kafka.consume_messages():
        print(f"Received: {msg}")
    kafka.close()
```

监测新消息并处理

```python
	# 创建 Kafka 客户端实例
    kafka = KafkaClient(bootstrap_servers='192.168.1.206:9092')
    def handle_message(msg):
       print(f"Handling: {msg}")
    kafka.monitor_topic("useact",handle_message)
    # 关闭连接
    kafka.close()
```

