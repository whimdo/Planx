#!/usr/bin/bash

# 函数：检查端口是否被占用
check_port() {
    port=$1
    if netstat -tuln | grep -q ":$port "; then
        echo "Port $port is already in use!"
        exit 1
    fi
}

# 函数：启动服务
start_service() {
    script_path=$1
    port=$2
    log_dir=$(dirname "$script_path")/log
    log_file="$log_dir/app.log"
    
    # 创建日志目录（如果不存在）
    mkdir -p "$log_dir"
    
    # 检查端口
    check_port "$port"
    
    echo "Starting $script_path on port $port..."
    nohup python "$script_path" > "$log_file" 2>&1 &
    if [ $? -eq 0 ]; then
        echo "Successfully started $script_path (PID: $!)"
    else
        echo "Failed to start $script_path"
        exit 1
    fi
}

# 启动每个服务
start_service "py-llm-eSearch-keywrd-gen/main_with_kafka.py" "9001"
start_service "py-planx-eSearch-wrd2vec/main_with_kafka.py" "9002"
start_service "py-planx-eSearch-vecs-sum/main_with_kafka.py" "9003"
start_service "py-planx-eSearch-milvus-cli/main_with_kafka.py" "9004"

echo "All services started."