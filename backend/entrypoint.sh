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
    
    # 停止调度器 (Python scheduler)
    if [ -f "/tmp/d2c_scheduler.pid" ]; then
        local scheduler_pid=$(cat "/tmp/d2c_scheduler.pid")
        if kill -0 "$scheduler_pid" 2>/dev/null; then
            print_info "停止Python调度器进程 (PID: $scheduler_pid)"
            kill -TERM "$scheduler_pid" 2>/dev/null || true
            wait "$scheduler_pid" 2>/dev/null || true
        fi
        rm -f "/tmp/d2c_scheduler.pid"
    fi
    
    # 停止系统cron
    if pgrep cron >/dev/null 2>&1; then
        print_info "停止系统cron服务"
        # Use killall for cron to be safe, or direct pkill
        # service cron stop # This might not work in busybox/slim images. pkill is more direct.
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

# 去掉CRON值开头和结尾的双引号 (如果存在)
CRON=$(echo "$CRON" | sed 's/^"\|"$//g')

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

# --- 调度器启动逻辑 START ---

# 获取当前时间作为目录名（年月日时分）- 即使是定时任务，也可能需要一个输出目录
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M")
export OUTPUT_DIR="/app/compose/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR" # 确保输出目录创建

# 验证CRON表达式格式
validate_cron() {
    local cron_expr="$1"
    local field_count=$(echo "$cron_expr" | awk '{print NF}')
    if [ "$field_count" -ne 5 ] && [ "$field_count" -ne 6 ]; then
        return 1
    fi
    for field in $cron_expr; do
#        if ! echo "$field" | grep -q '^[0-9*/,?-]*$' 2>/dev/null; then
        if ! echo "$field" | grep -qE '^[0-9A-Za-z*/,\-?]+$' 2>/dev/null; then
            return 1
        fi
    done
    return 0
}


if [ "$CRON" = "once" ]; then
    print_info "执行一次性任务..."
    python3 /app/d2c.py
    print_success "一次性任务完成，输出目录: $OUTPUT_DIR"
    # 对于一次性任务，不需要启动长期运行的调度器
    print_info "调度器模式: 一次性任务，不会启动定时调度器。"
else
    # 验证CRON表达式格式
    if ! validate_cron "$CRON"; then
        print_error "无效的CRON表达式格式: ${CRON}，调度器将不会启动。"
        # 可以选择退出或继续，这里选择继续，但调度器不会运行
        # exit 1 
    else
        print_info "定时任务配置: $CRON"

        field_count=$(echo "$CRON" | awk '{print NF}')
        if [ "$field_count" -eq 6 ]; then
            print_info "检测到6位CRON格式: $CRON"
            print_info "自动选择Python精确调度器以支持秒级调度。"

            # 停止现有的系统cron任务 (如果存在)
            if [ -f "/etc/cron.d/d2c-cron" ]; then
                rm -f "/etc/cron.d/d2c-cron"
                print_info "已移除系统cron任务文件。"
            fi

            # 启动Python调度器
            print_info "正在启动Python精确调度器..."
            nohup python3 /app/scheduler.py --config "$CONFIG_FILE" > /app/logs/scheduler.log 2>&1 &
            SCHEDULER_PID=$!
            echo $SCHEDULER_PID > "/tmp/d2c_scheduler.pid"
            print_success "Python调度器已启动 (PID: $SCHEDULER_PID)，PID已保存到 /tmp/d2c_scheduler.pid"
            
        else # 5位CRON格式
            print_info "检测到5位CRON格式: $CRON"
            print_info "使用系统cron调度器。"

            # 确保没有Python调度器在运行 (如果之前是6位切换过来)
            if [ -f "/tmp/d2c_scheduler.pid" ]; then
                PID_TO_KILL=$(cat "/tmp/d2c_scheduler.pid")
                if ps -p "$PID_TO_KILL" > /dev/null; then
                    print_info "停止旧的Python调度器 (PID: $PID_TO_KILL)..."
                    kill -TERM "$PID_TO_KILL" 2>/dev/null || true
                    sleep 2
                    if ps -p "$PID_TO_KILL" > /dev/null; then
                        kill -KILL "$PID_TO_KILL" 2>/dev/null || true
                    fi
                fi
                rm -f "/tmp/d2c_scheduler.pid"
            fi

            # 创建cron任务文件
            cat > /etc/cron.d/d2c-cron << EOF
# 设置环境变量
NAS=\${NAS:-debian}
NETWORK=\${NETWORK:-true}
TZ=\${TZ:-Asia/Shanghai}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 定时任务 (原始格式: ${CRON})
${CRON} root cd /app && export OUTPUT_DIR="/app/compose/\$(date +"%Y_%m_%d_%H_\%M")" && /usr/local/bin/python3 /app/d2c.py >> /app/logs/cron.log 2>&1
EOF
            chmod 0644 /etc/cron.d/d2c-cron
            print_success "cron任务文件 /etc/cron.d/d2c-cron 已创建/更新。"

            # 创建日志文件
            touch /app/logs/cron.log

            # 启动cron服务
            print_info "正在启动cron服务..."
            service cron start >/dev/null 2>&1 || cron # Try service, fallback to direct cron
            
            # 检查cron服务状态
            sleep 2 # Give cron a moment to start
            if pgrep cron >/dev/null 2>&1; then
                print_success "系统CRON服务启动成功"
            else
                print_error "系统CRON服务启动失败，请检查容器权限或cron配置。任务可能不会按时执行。"
            fi
        fi
    fi
fi
# --- 调度器启动逻辑 END ---

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
        print_error "Web UI进程异常退出，尝试重新启动..."
        cd /app
        python3 /app/web_ui.py &
        WEB_UI_PID=$!
        print_info "Web UI重新启动 (PID: $WEB_UI_PID)"
    fi
    
    # 重要的说明：调度器（无论是系统cron还是Python调度器）应该由 `entrypoint.sh` 启动一次，并独立运行。
    # 这里的循环主要是为了确保Web UI进程的存活，以及保持entrypoint.sh这个PID 1进程的活跃。
    # 我们不在这里重复启动调度器，以避免创建多个实例。
    
    # 等待一段时间再检查
    sleep 30
done
