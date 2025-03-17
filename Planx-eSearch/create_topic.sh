#!/bin/bash

# Kafka Broker 地址和端口
BOOTSTRAP_SERVER="localhost:9092"
KAFKA_BIN="/path/to/kafka/bin"  # 替换为你的 Kafka bin 目录路径

# Topic 配置
PARTITIONS=3
REPLICATION_FACTOR=1

# 定义 Topic 名称
TOPICS=(
  "document-to-keywords"
  "keywords-to-vectors"
  "vectors-to-summary"
  "summary-vectors"
)

# 创建 Topic
for TOPIC in "${TOPICS[@]}"; do
  echo "Creating topic: $TOPIC"
  $KAFKA_BIN/kafka-topics.sh --create \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --replication-factor $REPLICATION_FACTOR \
    --partitions $PARTITIONS \
    --topic $TOPIC
done

# 验证 Topic 是否创建成功
echo "Listing all topics:"
$KAFKA_BIN/kafka-topics.sh --list --bootstrap-server $BOOTSTRAP_SERVER