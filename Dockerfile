# 使用多平台基础镜像
FROM --platform=$TARGETPLATFORM python:3.9-slim

# 添加环境变量
ENV NAS=debian
ENV CRON="0 */12 * * *"
ENV NETWORK=true
ENV TZ=Asia/Shanghai

WORKDIR /app

# 设置构建参数
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# 根据目标平台安装对应架构的依赖
RUN echo "Building for $TARGETPLATFORM on $BUILDPLATFORM"

# 配置国内APT源
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list

# 安装必要依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    cron \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
         "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian \
         $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
         tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
         docker-ce-cli \
         docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置pip国内源并安装依赖
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install pyyaml

# 复制应用文件并设置权限
COPY . /app/
RUN chmod +x /app/d2c.py /app/run.sh

CMD ["/app/run.sh"]