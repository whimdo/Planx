#!/usr/bin/bash

# 函数：停止指定脚本的进程
stop_service() {
    script_path=$1
    port=$2
    # 查找运行该脚本的进程 ID（PID）
    pid=$(ps aux | grep "[p]ython $script_path" | awk '{print $2}')
    if [ -n "$pid" ]; then
        echo "Stopping $script_path (PID: $pid) on port $port..."
        kill -9 $pid
        if [ $? -eq 0 ]; then
            echo "Successfully stopped $script_path"
        else
            echo "Failed to stop $script_path"
        fi
    else
        echo "No process found for $script_path on port $port"
    fi
}

# 停止每个服务
stop_service "py-llm-eSearch-keywrd-gen/main_with_kafka.py" "9001"
stop_service "py-planx-eSearch-wrd2vec/main_with_kafka.py" "9002"
stop_service "py-planx-eSearch-vecs-sum/main_with_kafka.py" "9003"
stop_service "py-planx-eSearch-milvus-cli/main_with_kafka.py" "9004"

echo "All services stopped."