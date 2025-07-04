# 基于轻量级官方 Python 镜像
FROM python:3.9-slim

WORKDIR /app

# 设置构建参数（可用于多平台日志）
ARG TARGETPLATFORM
ARG BUILDPLATFORM
RUN echo "Building for $TARGETPLATFORM on $BUILDPLATFORM"

# 配置阿里云国内APT源，提高安装速度
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list

# 安装系统依赖与 Docker CLI 工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg cron \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
 && chmod a+r /etc/apt/keyrings/docker.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     tee /etc/apt/sources.list.d/docker.list > /dev/null \
 && apt-get update && apt-get install -y --no-install-recommends \
     docker-ce-cli docker-compose-plugin \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# 配置pip使用清华源并安装Python依赖
COPY requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
 && pip install -r requirements.txt

# 拷贝源代码并赋权
COPY . /app/
RUN chmod +x /app/d2c.py /app/run.sh

# 设置挂载目录和暴露端口
VOLUME ["/app"]
EXPOSE 5000

# 启动服务
CMD ["python3", "/app/web_ui.py"]
