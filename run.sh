#!/bin/bash

# 获取CRON环境变量，如果未设置则使用默认值
CRON=${CRON:-"0 */12 * * *"}
echo "当前CRON设置为: ${CRON}"

# 获取当前时间作为目录名（年月日时分）
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M")
export OUTPUT_DIR="/app/compose/${TIMESTAMP}"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 检查是否为一次性任务
if [ "$CRON" = "once" ]; then
    echo "执行一次性任务..."
    python3 ./d2c.py
    echo "任务完成！请查看 ${OUTPUT_DIR} 目录下的生成文件。"
    exit 0
fi

# 验证CRON表达式格式
if ! [[ "$CRON" =~ ^[0-9*/-]+" "[0-9*/-]+" "[0-9*/-]+" "[0-9*/-]+" "[0-9*/-]+$ ]]; then
    echo "错误：无效的CRON表达式格式: ${CRON}"
    echo "使用默认值：0 */12 * * *"
    CRON="0 */12 * * *"
fi

# 计算下次执行时间
next_run=$(date -d "$(python3 -c "
from datetime import datetime, timedelta
from croniter import croniter
base = datetime.now()
cron = croniter('${CRON}', base)
next_time = cron.get_next(datetime)
print(next_time.strftime('%Y-%m-%d %H:%M:%S'))
")" '+%Y年%m月%d日 %H时%M分%S秒')

# 创建cron任务，添加必要的环境变量
cat > /etc/cron.d/d2c-cron << EOF
# 设置环境变量
NAS=${NAS:-debian}
NETWORK=${NETWORK:-true}
TZ=${TZ:-Asia/Shanghai}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 定时任务
${CRON} root cd /app && OUTPUT_DIR="/app/compose/\$(date +"%Y_%m_%d_%H_%M")" /usr/local/bin/python3 /app/d2c.py >> /var/log/cron.log 2>&1
EOF
chmod 0644 /etc/cron.d/d2c-cron

# 创建日志文件
touch /var/log/cron.log

# 启动cron服务
cron

# 首次运行生成器脚本
python3 ./d2c.py

echo "完成！请查看 compose 目录下的生成文件。下次执行时间: ${next_run} "

# 持续输出日志，保持容器运行
tail -f /var/log/cron.log