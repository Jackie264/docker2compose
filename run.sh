#!/bin/bash

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

# 创建cron任务
echo "${CRON} /usr/local/bin/python3 /app/d2c.py >> /var/log/cron.log 2>&1" > /etc/cron.d/d2c-cron
chmod 0644 /etc/cron.d/d2c-cron

# 创建日志文件
touch /var/log/cron.log

# 启动cron服务
cron

# 首次运行生成器脚本
python3 ./d2c.py

# 持续输出日志，保持容器运行
tail -f /var/log/cron.log

echo "完成！请查看 compose 目录下的生成文件。"