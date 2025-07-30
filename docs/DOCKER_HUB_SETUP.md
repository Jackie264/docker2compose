# Docker Hub 自动构建设置指南

本文档说明如何设置GitHub Actions自动构建Docker镜像并推送到Docker Hub。

## 1. 创建Docker Hub账户和访问令牌

### 1.1 注册Docker Hub账户
1. 访问 [Docker Hub](https://hub.docker.com/)
2. 注册一个新账户或登录现有账户

### 1.2 创建访问令牌
1. 登录Docker Hub后，点击右上角的用户名
2. 选择 "Account Settings"
3. 点击 "Security" 标签
4. 点击 "New Access Token"
5. 输入令牌描述（如：`github-actions-docker2compose`）
6. 选择权限：`Read, Write, Delete`
7. 点击 "Generate"
8. **重要**：复制生成的令牌并保存，这是唯一一次显示

## 2. 在GitHub仓库中设置Secrets

### 2.1 访问仓库设置
1. 进入GitHub仓库页面
2. 点击 "Settings" 标签
3. 在左侧菜单中选择 "Secrets and variables" > "Actions"

### 2.2 添加必需的Secrets
点击 "New repository secret" 并添加以下secrets：

#### 必需的Secrets：
- **`DOCKERHUB_USERNAME`**: 您的Docker Hub用户名
- **`DOCKERHUB_TOKEN`**: 在步骤1.2中创建的访问令牌

#### 可选的Secrets（如果要推送到其他镜像仓库）：
- **`ALI_REGISTRY`**: 阿里云镜像仓库地址（如：`registry.cn-hangzhou.aliyuncs.com`）
- **`ALI_USERNAME`**: 阿里云镜像仓库用户名
- **`ALI_PASSWORD`**: 阿里云镜像仓库密码

## 3. 工作流程说明

### 3.1 触发条件
自动构建会在以下情况下触发：
- 推送到 `master` 分支
- 创建新的版本标签（格式：`v*.*.*`）
- 手动触发（workflow_dispatch）

### 3.2 构建流程
1. **测试阶段**：运行完整的测试套件
2. **构建阶段**：多平台Docker镜像构建
3. **推送阶段**：推送到多个镜像仓库

### 3.3 支持的平台
- `linux/amd64`
- `linux/arm64`
- `linux/arm/v7`

## 4. 镜像标签策略

### 4.1 标签规则
- **版本标签**：`v1.2.3` → `1.2.3`
- **分支标签**：`master` → `master`
- **最新标签**：`latest`（仅限master分支）
- **提交标签**：`master-abc1234`

### 4.2 镜像仓库
构建的镜像会推送到：
1. **Docker Hub**: `your-username/docker2compose`
2. **GitHub Container Registry**: `ghcr.io/coracoo/docker2compose`
3. **阿里云镜像仓库**（如果配置）: `your-registry/cherry4nas/docker2compose`

## 5. 使用构建的镜像

### 5.1 从Docker Hub拉取
```bash
# 拉取最新版本
docker pull your-username/docker2compose:latest

# 拉取特定版本
docker pull your-username/docker2compose:1.2.3

# 拉取特定分支
docker pull your-username/docker2compose:master
```

### 5.2 运行容器
```bash
docker run -d \
  --name docker2compose \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  your-username/docker2compose:latest
```

## 6. 监控构建状态

### 6.1 GitHub Actions
- 访问仓库的 "Actions" 标签查看构建状态
- 每次推送或创建标签都会触发新的构建

### 6.2 Docker Hub
- 登录Docker Hub查看推送的镜像
- 检查镜像的标签和构建时间

## 7. 故障排除

### 7.1 常见问题
1. **认证失败**：检查DOCKERHUB_USERNAME和DOCKERHUB_TOKEN是否正确
2. **权限错误**：确保访问令牌有足够的权限
3. **构建失败**：检查Dockerfile.github是否存在且正确

### 7.2 调试步骤
1. 检查GitHub Actions日志
2. 验证secrets配置
3. 确认Docker Hub令牌未过期
4. 检查网络连接问题

## 8. 安全最佳实践

1. **定期轮换令牌**：建议每6个月更新一次访问令牌
2. **最小权限原则**：只给予必要的权限
3. **监控使用情况**：定期检查Docker Hub的使用统计
4. **保护secrets**：不要在代码中硬编码敏感信息

## 9. 自动更新Docker Hub描述

工作流还会自动更新Docker Hub上的镜像描述：
- 使用仓库的README.md作为详细描述
- 设置简短描述为项目简介
- 仅在推送到master分支时更新

这样可以确保Docker Hub上的信息与GitHub仓库保持同步。
