#!/bin/bash

PID_FILE="bot.pid"
LOG_FILE="bot.log"

# 이미 실행 중인지 확인
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Bot is already running with PID: $PID"
        exit 1
    else
        echo "PID file exists but process is not running. Removing stale PID file."
        rm "$PID_FILE"
    fi
fi

echo "Starting bot..."
nohup uv run -m bot > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

# 프로세스가 바로 죽는지 확인하기 위해 잠시 대기
sleep 2
if ps -p $PID > /dev/null 2>&1; then
    echo "Bot started successfully (PID: $PID)"
    echo "Logs are being written to $LOG_FILE"
else
    echo "Bot failed to start. Check $LOG_FILE for details."
    rm "$PID_FILE"
    exit 1
fi
