#!/bin/bash

# 配置文件路径
CONFIG_FILE="/app/config.json"

# 从配置文件读取CRON设置的函数
get_cron_from_config() {
    local config_file="$CONFIG_FILE"
    local default_cron="once"
    # 检查配置文件是否存在
    if [ -f "$config_file" ]; then
        # 尝试从配置文件中提取CRON值
        local cron_from_file=$(grep '"CRON"' "$config_file" | sed 's/.*"CRON"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        
        # 如果成功提取到CRON值且不为空
        if [ -n "$cron_from_file" ] && [ "$cron_from_file" != "CRON" ]; then
            echo "$cron_from_file"
            return 0
        fi
    fi
    
    # 如果配置文件不存在或读取失败，使用环境变量或默认值
    echo "${CRON:-$default_cron}"
}

# 获取CRON配置，优先从config.json读取，其次环境变量，最后默认值
CRON=$(get_cron_from_config)
# 去掉CRON值开头和结尾的双引号
CRON=$(echo "$CRON" | sed 's/^"\|"$//g')
echo "当前CRON设置为: ${CRON}"

# 检查是否为一次性任务 - 优先处理，避免不必要的计算
if [ "$CRON" = "once" ]; then
    echo "执行一次性任务..."
    # 获取当前时间作为目录名（年月日时分）
    TIMESTAMP=$(date +"%Y_%m_%d_%H_%M")
    export OUTPUT_DIR="/app/compose/${TIMESTAMP}"
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    
    # 执行任务
    python3 ./d2c.py
    echo "任务完成！请查看 ${OUTPUT_DIR} 目录下的生成文件。"
    exit 0
fi

# 获取当前时间作为目录名（年月日时分）
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M")
export OUTPUT_DIR="/app/compose/${TIMESTAMP}"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 验证CRON表达式格式 - 兼容群晖NAS等不同环境
validate_cron() {
    local cron_expr="$1"
    local debug_mode="${DEBUG_CRON:-true}"
    
    # 环境检测和调试信息
    if [ "$debug_mode" = "true" ]; then
        echo "调试: 验证CRON表达式 '$cron_expr'"
        echo "调试: Bash版本 $BASH_VERSION"
    fi
    
    # 方法1: 使用awk计算字段数量
    local field_count
    if command -v awk >/dev/null 2>&1; then
        field_count=$(echo "$cron_expr" | awk '{print NF}')
        [ "$debug_mode" = "true" ] && echo "调试: awk检测到 $field_count 个字段"
    else
        # 回退方法: 手动计算字段
        field_count=0
        for field in $cron_expr; do
            field_count=$((field_count + 1))
        done
        [ "$debug_mode" = "true" ] && echo "调试: 手动计算 $field_count 个字段"
    fi
    
    # 支持标准5位格式 (分 时 日 月 周) 和扩展6位格式 (秒 分 时 日 月 周)
    if [ "$field_count" -ne 5 ] && [ "$field_count" -ne 6 ]; then
        [ "$debug_mode" = "true" ] && echo "调试: 字段数量不正确 (期望5或6个，实际${field_count}个)"
        return 1
    fi
    
    [ "$debug_mode" = "true" ] && echo "调试: 检测到${field_count}位CRON格式"
    
    # 方法2: 字符验证 - 多种兼容性方案
    local field_num=1
    
    # 使用数组来正确分割字段，避免shell展开问题
    local IFS=' '
    read -ra fields <<< "$cron_expr"
    
    for field in "${fields[@]}"; do
        [ "$debug_mode" = "true" ] && echo "调试: 检查字段$field_num: '$field'"
        
        # 尝试多种验证方法
        local valid=0
        
        # 方法A: 使用grep (最兼容) - 支持6位格式的?字符
        if echo "$field" | grep -q '^[0-9*/,?-]*$' 2>/dev/null; then
            valid=1
        # 方法B: 使用case语句 (bash内置) - 支持6位格式的?字符
        elif case "$field" in *[!0-9*/,?-]*) false;; *) true;; esac; then
            valid=1
        # 方法C: 字符逐一检查 (最保守) - 支持6位格式的?字符
        else
            local char
            valid=1
            for ((i=0; i<${#field}; i++)); do
                char="${field:$i:1}"
                case "$char" in
                    [0-9]|\*|\/|,|\?|-) ;;
                    *) valid=0; break;;
                esac
            done 2>/dev/null || valid=1  # 如果不支持字符串操作，默认通过
        fi
        
        if [ "$valid" -eq 0 ]; then
            [ "$debug_mode" = "true" ] && echo "调试: 字段$field_num包含无效字符"
            return 1
        fi
        
        field_num=$((field_num + 1))
    done
    
    [ "$debug_mode" = "true" ] && echo "调试: CRON表达式验证通过"
    return 0
}

if ! validate_cron "$CRON"; then
    echo "错误：无效的CRON表达式格式: ${CRON}"
    echo "使用默认值：once"
    CRON="once"
else
    # 基本格式验证通过，记录到日志
    echo "CRON表达式格式验证通过: ${CRON}"
fi

# 计算下次执行时间 - 支持5位和6位格式
next_run=$(date -d "$(python3 -c "
import sys
from datetime import datetime, timedelta
from croniter import croniter

cron_expr = '${CRON}'
fields = cron_expr.split()
base = datetime.now()

# 检查是否为6位格式 (秒 分 时 日 月 周)
if len(fields) == 6:
    # croniter默认支持6位格式，直接使用
    try:
        cron = croniter(cron_expr, base)
        next_time = cron.get_next(datetime)
        print(next_time.strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        # 如果6位格式失败，转换为5位格式 (忽略秒字段)
        five_field_cron = ' '.join(fields[1:])
        cron = croniter(five_field_cron, base)
        next_time = cron.get_next(datetime)
        print(next_time.strftime('%Y-%m-%d %H:%M:%S'))
else:
    # 标准5位格式
    cron = croniter(cron_expr, base)
    next_time = cron.get_next(datetime)
    print(next_time.strftime('%Y-%m-%d %H:%M:%S'))
")" '+%Y年%m月%d日 %H时%M分%S秒')

# 处理CRON格式 - 系统cron只支持5位格式
SYSTEM_CRON="$CRON"
field_count=$(echo "$CRON" | awk '{print NF}')
if [ "$field_count" -eq 6 ]; then
    echo "检测到6位CRON格式: $CRON"
    
    # 智能转换6位到5位格式
    IFS=' ' read -ra cron_fields <<< "$CRON"
    seconds="${cron_fields[0]}"
    minutes="${cron_fields[1]}"
    hours="${cron_fields[2]}"
    days="${cron_fields[3]}"
    months="${cron_fields[4]}"
    weekdays="${cron_fields[5]}"
    
    # 特殊处理：如果是每秒执行且时间范围有限，转换为每分钟执行
    if [[ "$seconds" =~ ^[0-9]+/[0-9]+$ ]] && [[ "$minutes" =~ ^[0-9]+-[0-9]+$ ]]; then
        echo "检测到秒级重复执行模式，转换为分钟级执行以保持调度意图"
        # 将分钟范围转换为每分钟执行
        SYSTEM_CRON="*/1 $hours $days $months $(echo $weekdays | sed 's/?/*/g')"
        echo "转换策略: 每分钟执行一次，保持时间窗口限制"
    else
        # 标准转换：去掉秒字段
        SYSTEM_CRON="$minutes $hours $days $months $(echo $weekdays | sed 's/?/*/g')"
        echo "标准转换: 去掉秒字段，保持其他时间设置"
    fi
    
    echo "系统cron格式: $SYSTEM_CRON"
    echo "注意: 由于系统cron限制，秒级精度无法保持"
    echo "建议: 如需精确秒级调度，请考虑使用Python调度器"
    echo ""
    echo "选择调度方式:"
    echo "1. 使用系统cron (当前选择) - 分钟级精度"
    echo "2. 使用Python精确调度器 - 秒级精度"
    echo ""
    read -p "是否切换到Python精确调度器? (y/N): " use_python_scheduler
    
    if [[ "$use_python_scheduler" =~ ^[Yy]$ ]]; then
        echo "启动Python精确调度器..."
        echo "注意: 这将替代系统cron，支持完整的6位CRON格式"
        
        # 停止现有的cron任务
        if [ -f "/etc/cron.d/d2c-cron" ]; then
            rm -f "/etc/cron.d/d2c-cron"
            echo "已移除系统cron任务"
        fi
        
        # 启动Python调度器
        echo "正在启动Python精确调度器..."
        python3 /app/scheduler.py --config "$CONFIG_FILE" &
        SCHEDULER_PID=$!
        echo "Python调度器已启动 (PID: $SCHEDULER_PID)"
        echo "调度器将在后台运行，支持完整的6位CRON格式: $CRON"
        echo "要停止调度器，请运行: kill $SCHEDULER_PID"
        
        # 保存PID到文件
        echo $SCHEDULER_PID > /tmp/d2c_scheduler.pid
        echo "PID已保存到 /tmp/d2c_scheduler.pid"
        
        exit 0
    fi
fi

# 创建cron任务，添加必要的环境变量
cat > /etc/cron.d/d2c-cron << EOF
# 设置环境变量
NAS=${NAS:-debian}
NETWORK=${NETWORK:-true}
TZ=${TZ:-Asia/Shanghai}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 定时任务 (原始格式: ${CRON})
${SYSTEM_CRON} root cd /app && export OUTPUT_DIR="/app/compose/\$(date +"%Y_%m_%d_%H_%M")" && /usr/local/bin/python3 /app/d2c.py >> /var/log/cron.log 2>&1
EOF
chmod 0644 /etc/cron.d/d2c-cron

# 创建日志文件
touch /var/log/cron.log

# 启动cron服务
echo "正在启动cron服务..."
service cron start

# 检查cron服务状态
if service cron status >/dev/null 2>&1; then
    echo "✅ cron服务启动成功"
else
    echo "⚠️  cron服务启动失败，尝试直接启动..."
    cron
    sleep 2
    if pgrep cron >/dev/null 2>&1; then
        echo "✅ cron进程启动成功"
    else
        echo "❌ cron启动失败，请检查容器权限"
    fi
fi

# 首次运行生成器脚本
echo "执行首次D2C任务..."
python3 ./d2c.py

echo "完成！请查看 compose 目录下的生成文件。下次执行时间: ${next_run} "
echo "cron任务已配置，日志将输出到 /var/log/cron.log"

# 持续输出日志，保持容器运行
tail -f /var/log/cron.log