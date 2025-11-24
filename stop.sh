#!/bin/bash

PID_FILE="bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping bot (PID: $PID)..."
        kill $PID
        
        # 프로세스 종료 대기
        count=0
        while ps -p $PID > /dev/null 2>&1; do
            sleep 1
            count=$((count+1))
            if [ $count -ge 10 ]; then
                echo "Force killing bot..."
                kill -9 $PID
                break
            fi
        done
        
        echo "Bot stopped."
        rm "$PID_FILE"
    else
        echo "Process $PID not found. Cleaning up PID file."
        rm "$PID_FILE"
    fi
else
    echo "PID file not found. Trying to find process by name..."
    # pkill을 사용할 때 전체 커맨드라인 매칭을 위해 -f 사용, 더 정확한 매칭 시도
    if pgrep -f "uv run -m bot" > /dev/null; then
        pkill -f "uv run -m bot"
        echo "Bot stopped (via pkill)."
    else
        echo "No running bot process found."
    fi
fi
