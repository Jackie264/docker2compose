#!/bin/bash

# D2C 容器启动脚本
# 解决PID 1进程管理问题，确保Web UI和调度器都能稳定运行

set -e

# 颜色输出函数
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# 信号处理函数
cleanup() {
    print_info "接收到终止信号，正在清理..."
    
    # 停止Web UI
    if [ -n "$WEB_UI_PID" ] && kill -0 "$WEB_UI_PID" 2>/dev/null; then
        print_info "停止Web UI进程 (PID: $WEB_UI_PID)"
        kill -TERM "$WEB_UI_PID" 2>/dev/null || true
        wait "$WEB_UI_PID" 2>/dev/null || true
    fi
    
    # 停止调度器
    if [ -f "/tmp/d2c_scheduler.pid" ]; then
        local scheduler_pid=$(cat "/tmp/d2c_scheduler.pid")
        if kill -0 "$scheduler_pid" 2>/dev/null; then
            print_info "停止调度器进程 (PID: $scheduler_pid)"
            kill -TERM "$scheduler_pid" 2>/dev/null || true
            wait "$scheduler_pid" 2>/dev/null || true
        fi
        rm -f "/tmp/d2c_scheduler.pid"
    fi
    
    # 停止系统cron
    if pgrep cron >/dev/null 2>&1; then
        print_info "停止系统cron服务"
        pkill cron 2>/dev/null || true
    fi
    
    print_success "清理完成"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT SIGQUIT

print_info "启动D2C容器..."

# 创建必要的目录
mkdir -p /app/config /app/compose /app/logs /app/templates /app/static/css /app/static/js

# 确保配置文件存在
if [ ! -f "/app/config/config.json" ]; then
    print_info "创建默认配置文件"
    python3 -c "
import json
import os

config = {
    'CRON': os.environ.get('CRON', 'once'),
    'TZ': os.environ.get('TZ', 'Asia/Shanghai'),
    'NAS': os.environ.get('NAS', 'debian'),
    'NETWORK': os.environ.get('NETWORK', 'true')
}

with open('/app/config/config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print('配置文件创建完成')
"
fi

# 读取配置
CRON=$(python3 -c "
import json
try:
    with open('/app/config/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(config.get('CRON', 'once'))
except:
    print('once')
")

TZ_CONFIG=$(python3 -c "
import json
try:
    with open('/app/config/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(config.get('TZ', 'Asia/Shanghai'))
except:
    print('Asia/Shanghai')
")

print_info "当前CRON设置: $CRON"
print_info "当前时区设置: $TZ_CONFIG"

# 设置系统时区
if [ -f "/usr/share/zoneinfo/$TZ_CONFIG" ]; then
    print_info "设置系统时区为: $TZ_CONFIG"
    ln -sf "/usr/share/zoneinfo/$TZ_CONFIG" /etc/localtime
    echo "$TZ_CONFIG" > /etc/timezone
    export TZ="$TZ_CONFIG"
    print_success "时区设置完成: $(date)"
else
    print_warning "时区文件不存在: /usr/share/zoneinfo/$TZ_CONFIG，使用默认UTC时区"
fi

# 如果是一次性任务，执行后启动Web UI
if [ "$CRON" = "once" ]; then
    print_info "执行一次性任务..."
    TIMESTAMP=$(date +"%Y_%m_%d_%H_%M")
    export OUTPUT_DIR="/app/compose/${TIMESTAMP}"
    mkdir -p "$OUTPUT_DIR"
    python3 /app/d2c.py
    print_success "一次性任务完成，输出目录: $OUTPUT_DIR"
else
    print_info "定时任务配置: $CRON (调度器将由Web UI管理)"
fi

# 启动Web UI（在后台）
print_info "启动Web UI服务..."
cd /app
python3 /app/web_ui.py &
WEB_UI_PID=$!

print_success "Web UI已启动 (PID: $WEB_UI_PID)"
print_info "服务访问地址: http://localhost:5000"

# 等待Web UI启动
sleep 5

# 检查Web UI是否正常运行
if ! kill -0 "$WEB_UI_PID" 2>/dev/null; then
    print_error "Web UI启动失败"
    exit 1
fi

print_success "D2C容器启动完成"
print_info "进程状态:"
print_info "  Web UI PID: $WEB_UI_PID"
if [ -f "/tmp/d2c_scheduler.pid" ]; then
    SCHEDULER_PID=$(cat "/tmp/d2c_scheduler.pid")
    print_info "  调度器 PID: $SCHEDULER_PID"
fi

# 主循环 - 监控子进程
while true; do
    # 检查Web UI进程
    if ! kill -0 "$WEB_UI_PID" 2>/dev/null; then
        print_error "Web UI进程异常退出，重新启动..."
        cd /app
        python3 /app/web_ui.py &
        WEB_UI_PID=$!
        print_info "Web UI重新启动 (PID: $WEB_UI_PID)"
    fi
    
    # 注意: 调度器由Web UI根据需要管理，entrypoint.sh专注于PID 1进程管理
    
    # 等待一段时间再检查
    sleep 30
done