#!/bin/bash
# D2C Python调度器管理脚本

SCHEDULER_PID_FILE="/tmp/d2c_scheduler.pid"
SCHEDULER_SCRIPT="/app/scheduler.py"
CONFIG_FILE="/app/config/config.json"
CRON_UTILS_SCRIPT="/app/cron_utils.py"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取CRON表达式
get_cron_expression() {
    if [ -f "$CONFIG_FILE" ]; then
        python3 "$CRON_UTILS_SCRIPT" --config "$CONFIG_FILE" --json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('original', '*/5 * * * *'))" 2>/dev/null || echo "*/5 * * * *"
    else
        echo "*/5 * * * *"
    fi
}

# 从配置文件获取时区设置
get_timezone_from_config() {
    if [ -f "$CONFIG_FILE" ]; then
        # 从配置文件读取TZ设置
        local tz=$(grep '"TZ"' "$CONFIG_FILE" | sed 's/.*"TZ"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        if [ -n "$tz" ] && [ "$tz" != "TZ" ]; then
            echo "$tz"
        else
            echo "Asia/Shanghai"
        fi
    else
        echo "Asia/Shanghai"
    fi
}

# 检查是否为6位CRON表达式
is_6_field_cron() {
    local cron_expr="$1"
    if [ -z "$cron_expr" ] || [ "$cron_expr" = "once" ]; then
        return 1
    fi
    
    local result=$(python3 "$CRON_UTILS_SCRIPT" --cron "$cron_expr" --analyze --json 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); exit(0 if data.get('is_6_field', False) else 1)" 2>/dev/null
        return $?
    fi
    return 1
}

# 验证CRON表达式
validate_cron_expression() {
    local cron_expr="$1"
    python3 "$CRON_UTILS_SCRIPT" --cron "$cron_expr" --validate --json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); exit(0 if data.get('valid', False) else 1)" 2>/dev/null
    return $?
}

# 检查调度器是否运行
check_scheduler_status() {
    if [ -f "$SCHEDULER_PID_FILE" ]; then
        local pid=$(cat "$SCHEDULER_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # 运行中
        else
            rm -f "$SCHEDULER_PID_FILE"  # 清理无效的PID文件
            return 1  # 未运行
        fi
    else
        return 1  # 未运行
    fi
}

# 检查系统CRON是否运行
check_system_cron_status() {
    if [ -f "/etc/cron.d/d2c-cron" ]; then
        if pgrep cron >/dev/null 2>&1; then
            return 0  # 系统cron运行中
        fi
    fi
    return 1  # 系统cron未运行
}

# 启动系统CRON
start_system_cron() {
    local cron_expr="$1"
    local converted_cron="$2"
    
    print_info "启动系统CRON调度器..."
    
    # 创建cron任务文件
    cat > /etc/cron.d/d2c-cron << EOF
# 设置环境变量
NAS=\${NAS:-debian}
NETWORK=\${NETWORK:-true}
TZ=\${TZ:-Asia/Shanghai}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 定时任务 (原始格式: ${cron_expr})
${converted_cron} root cd /app && export TZ_CONFIG=\$(grep '"TZ"' /app/config/config.json | sed 's/.*"TZ"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || echo 'Asia/Shanghai') && export OUTPUT_DIR="/app/compose/\$(TZ=\$TZ_CONFIG date +\%Y_\%m_\%d_\%H_\%M)" && python3 /app/d2c.py >> /app/logs/cron.log 2>&1
EOF
    chmod 0644 /etc/cron.d/d2c-cron
    
    # 创建日志文件
    mkdir -p /app/logs
    touch /app/logs/cron.log
    
    # 启动cron服务
    print_info "启动cron服务..."
    service cron start >/dev/null 2>&1 || cron
    
    sleep 2
    
    # 检查cron服务状态
    if pgrep cron >/dev/null 2>&1; then
        print_success "系统CRON启动成功"
        print_info "CRON表达式: $converted_cron"
        print_info "日志文件: /app/logs/cron.log"
        return 0
    else
        print_error "系统CRON启动失败"
        return 1
    fi
}

# 启动调度器
start_scheduler() {
    print_info "检查调度器状态..."
    
    # 检查是否已有调度器运行
    if check_scheduler_status; then
        print_warning "Python调度器已经在运行中"
        show_status
        return 1
    fi
    
    if check_system_cron_status; then
        print_warning "系统CRON调度器已经在运行中"
        show_status
        return 1
    fi
    
    # 检查必要文件
    if [ ! -f "$SCHEDULER_SCRIPT" ]; then
        print_error "调度器脚本不存在: $SCHEDULER_SCRIPT"
        return 1
    fi
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    if [ ! -f "$CRON_UTILS_SCRIPT" ]; then
        print_error "CRON工具脚本不存在: $CRON_UTILS_SCRIPT"
        return 1
    fi
    
    # 获取CRON表达式
    local cron_expr=$(get_cron_expression)
    print_info "当前CRON表达式: $cron_expr"
    
    # 检查是否为一次性任务
    if [ "$cron_expr" = "once" ]; then
        print_info "检测到一次性任务，直接执行..."
        local tz=$(get_timezone_from_config)
        local timestamp=$(TZ="$tz" date +"%Y_%m_%d_%H_%M")
        export OUTPUT_DIR="/app/compose/${timestamp}"
        mkdir -p "$OUTPUT_DIR"
        python3 /app/d2c.py
        print_success "一次性任务执行完成，输出目录: $OUTPUT_DIR"
        return 0
    fi
    
    # 验证CRON表达式
    if ! validate_cron_expression "$cron_expr"; then
        print_error "无效的CRON表达式: $cron_expr"
        return 1
    fi
    
    # 检查是否为6位CRON表达式
    if is_6_field_cron "$cron_expr"; then
        print_info "检测到6位CRON格式，启动Python精确调度器..."
        
        # 停止系统cron任务
        if [ -f "/etc/cron.d/d2c-cron" ]; then
            rm -f "/etc/cron.d/d2c-cron"
            print_info "已移除系统cron任务"
        fi
        
        # 启动Python调度器
        nohup python3 "$SCHEDULER_SCRIPT" --config "$CONFIG_FILE" > /tmp/d2c_scheduler.log 2>&1 &
        local pid=$!
        
        # 等待一下确保启动成功
        sleep 2
        
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid" > "$SCHEDULER_PID_FILE"
            print_success "Python精确调度器启动成功 (PID: $pid)"
            print_info "支持完整的6位CRON格式: $cron_expr"
            print_info "日志文件: /tmp/d2c_scheduler.log"
        else
            print_error "Python调度器启动失败"
            return 1
        fi
    else
        print_info "检测到5位CRON格式，启动系统CRON调度器..."
        
        # 停止Python调度器（如果在运行）
        if check_scheduler_status; then
            stop_scheduler
        fi
        
        # 启动系统CRON
        start_system_cron "$cron_expr" "$cron_expr"
    fi
}

# 停止系统CRON
stop_system_cron() {
    print_info "停止系统CRON调度器..."
    
    # 移除cron任务文件
    if [ -f "/etc/cron.d/d2c-cron" ]; then
        rm -f "/etc/cron.d/d2c-cron"
        print_success "已移除系统cron任务"
    else
        print_warning "系统cron任务文件不存在"
    fi
    
    # 注意：不停止整个cron服务，因为可能有其他任务在使用
    print_info "系统CRON调度器已停止"
}

# 停止调度器
stop_scheduler() {
    local stopped_any=false
    
    # 停止Python调度器
    if check_scheduler_status; then
        print_info "停止Python调度器..."
        
        local pid=$(cat "$SCHEDULER_PID_FILE")
        
        # 发送TERM信号
        kill -TERM "$pid" 2>/dev/null
        
        # 等待进程退出
        local count=0
        while [ $count -lt 10 ]; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                break
            fi
            sleep 1
            count=$((count + 1))
        done
        
        # 如果还在运行，强制杀死
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "正常停止失败，强制终止进程"
            kill -KILL "$pid" 2>/dev/null
            sleep 1
        fi
        
        # 清理PID文件
        rm -f "$SCHEDULER_PID_FILE"
        
        if ! ps -p "$pid" > /dev/null 2>&1; then
            print_success "Python调度器已停止"
            stopped_any=true
        else
            print_error "无法停止Python调度器"
            return 1
        fi
    fi
    
    # 停止系统CRON
    if check_system_cron_status; then
        stop_system_cron
        stopped_any=true
    fi
    
    if [ "$stopped_any" = false ]; then
        print_warning "没有运行中的调度器"
        return 1
    fi
}

# 重启调度器
restart_scheduler() {
    print_info "重启Python调度器..."
    stop_scheduler
    sleep 2
    start_scheduler
}

# 显示状态
show_status() {
    print_info "=== D2C 调度器状态 ==="
    
    # 获取CRON表达式
    local cron_expr=$(get_cron_expression)
    local is_6_field=false
    
    # 检查是否为6位CRON
    if is_6_field_cron "$cron_expr"; then
        is_6_field=true
    fi
    
    # 显示CRON配置信息
    print_info "CRON表达式: $cron_expr"
    if [ "$is_6_field" = true ]; then
        print_info "CRON格式: 6位 (秒级精度)"
        print_info "推荐调度器: Python精确调度器"
    else
        print_info "CRON格式: 5位 (分钟级精度)"
        print_info "兼容调度器: 系统CRON / Python调度器"
    fi
    
    # 计算下次执行时间
    local next_time_result=$(python3 "$CRON_UTILS_SCRIPT" --cron "$cron_expr" --next-time --json 2>/dev/null)
    if [ $? -eq 0 ]; then
        local next_time=$(echo "$next_time_result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('next_time', '未知'))" 2>/dev/null)
        if [ "$next_time" != "未知" ] && [ -n "$next_time" ]; then
            print_info "下次执行时间: $next_time"
        fi
    fi
    
    echo
    
    # 检查Python调度器状态
    if check_scheduler_status; then
        local pid=$(cat "$SCHEDULER_PID_FILE")
        print_success "Python调度器: 运行中 (PID: $pid)"
        
        # 显示进程信息
        local process_info=$(ps -p "$pid" -o pid,ppid,cmd --no-headers 2>/dev/null)
        if [ -n "$process_info" ]; then
            print_info "进程信息: $process_info"
        fi
        
        # 显示最近日志
        if [ -f "/tmp/d2c_scheduler.log" ]; then
            print_info "最近日志 (最后5行):"
            tail -5 "/tmp/d2c_scheduler.log" | while read line; do
                echo "  $line"
            done
        fi
    else
        print_warning "Python调度器: 未运行"
    fi
    
    echo
    
    # 检查系统CRON状态
    if check_system_cron_status; then
        print_success "系统CRON: 运行中"
        print_info "cron任务文件: /etc/cron.d/d2c-cron"
        
        # 显示cron任务内容
        local cron_content=$(grep -v '^#' /etc/cron.d/d2c-cron | grep -v '^$' | tail -1)
        if [ -n "$cron_content" ]; then
            print_info "当前任务: $cron_content"
        fi
        
        # 显示最近日志
        if [ -f "/app/logs/cron.log" ]; then
            print_info "最近日志 (最后5行):"
            tail -5 "/app/logs/cron.log" | while read line; do
                echo "  $line"
            done
        fi
    else
        print_warning "系统CRON: 未运行"
    fi
    
    echo
    
    # 显示文件状态
    print_info "=== 文件状态 ==="
    if [ -f "$CONFIG_FILE" ]; then
        print_success "配置文件: 存在 ($CONFIG_FILE)"
    else
        print_error "配置文件: 不存在 ($CONFIG_FILE)"
    fi
    
    if [ -f "$SCHEDULER_SCRIPT" ]; then
        print_success "调度器脚本: 存在 ($SCHEDULER_SCRIPT)"
    else
        print_error "调度器脚本: 不存在 ($SCHEDULER_SCRIPT)"
    fi
    
    if [ -f "$CRON_UTILS_SCRIPT" ]; then
        print_success "CRON工具脚本: 存在 ($CRON_UTILS_SCRIPT)"
    else
        print_error "CRON工具脚本: 不存在 ($CRON_UTILS_SCRIPT)"
    fi
    
    # 显示建议
    echo
    print_info "=== 建议 ==="
    if [ "$is_6_field" = true ]; then
        if check_scheduler_status; then
            print_success "当前配置最优: 6位CRON + Python精确调度器"
        else
            print_warning "建议启动Python调度器以支持6位CRON的秒级精度"
        fi
    else
        if check_scheduler_status && check_system_cron_status; then
            print_warning "检测到重复调度器运行，建议停止其中一个"
        elif check_scheduler_status || check_system_cron_status; then
            print_success "当前调度器配置正常"
        else
            print_warning "没有运行中的调度器，请启动调度器"
        fi
    fi
}

# 显示日志
show_logs() {
    local lines=${1:-50}
    
    if [ -f "/tmp/d2c_scheduler.log" ]; then
        echo "=== D2C调度器日志 (最后${lines}行) ==="
        tail -n "$lines" "/tmp/d2c_scheduler.log"
    else
        print_warning "日志文件不存在: /tmp/d2c_scheduler.log"
    fi
}

# 测试配置
test_config() {
    print_info "测试当前配置..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    python3 "$SCHEDULER_SCRIPT" --config "$CONFIG_FILE" --test
}

# 显示帮助
show_help() {
    echo "D2C Python调度器管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  start     启动调度器"
    echo "  stop      停止调度器"
    echo "  restart   重启调度器"
    echo "  status    显示状态"
    echo "  logs      显示日志 [行数，默认50]"
    echo "  test      测试配置"
    echo "  help      显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start          # 启动调度器"
    echo "  $0 status         # 查看状态"
    echo "  $0 logs 100       # 查看最后100行日志"
    echo "  $0 test           # 测试配置"
}

# 主函数
main() {
    case "$1" in
        start)
            start_scheduler
            ;;
        stop)
            stop_scheduler
            ;;
        restart)
            restart_scheduler
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        test)
            test_config
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 检查是否有足够权限
if [ "$EUID" -ne 0 ] && [[ "$1" == "start" || "$1" == "stop" || "$1" == "restart" ]]; then
    print_warning "建议以root权限运行以确保完整功能"
fi

# 执行主函数
main "$@"