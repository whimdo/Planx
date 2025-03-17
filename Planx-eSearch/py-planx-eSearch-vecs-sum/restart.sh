#!/usr/bin/bash

# 服务信息
SCRIPT_PATH="py-planx-eSearch-vecs-sum/main_with_kafka.py"
PORT="9003"
LOG_DIR="py-planx-eSearch-vecs-sum/logs"  # 注意：原始用的是 logs，统一为 log，如需 logs 请修改
LOG_FILE="$LOG_DIR/app.log"

# 停止服务
stop_service() {
    pid=$(ps aux | grep "[p]ython $SCRIPT_PATH" | awk '{print $2}')
    if [ -n "$pid" ]; then
        echo "Stopping $SCRIPT_PATH (PID: $pid) on port $PORT..."
        kill -9 $pid
        if [ $? -eq 0 ]; then
            echo "Successfully stopped $SCRIPT_PATH"
        else
            echo "Failed to stop $SCRIPT_PATH"
            exit 1
        fi
    else
        echo "No process found for $SCRIPT_PATH on port $PORT"
    fi
}

# 检查端口并启动服务
start_service() {
    if netstat -tuln | grep -q ":$PORT "; then
        echo "Port $PORT is already in use!"
        exit 1
    fi
    mkdir -p "$LOG_DIR"
    echo "Starting $SCRIPT_PATH on port $PORT..."
    nohup python "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &
    if [ $? -eq 0 ]; then
        echo "Successfully started $SCRIPT_PATH (PID: $!)"
    else
        echo "Failed to start $SCRIPT_PATH"
        exit 1
    fi
}

# 执行重启
echo "Restarting $SCRIPT_PATH..."
stop_service
sleep 1
start_service
echo "Restart completed for $SCRIPT_PATH."