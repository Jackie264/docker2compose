# Docker Compose 生成器

本工具用于读取极空间私有云系统中的存量Docker容器信息，自动生成对应的docker-compose.yaml文件。

它会根据容器之间的网络关系（自定义网络或link连接）将相关容器分组，并为每组容器生成一个独立的docker-compose.yaml文件。

理论上所有NAS都可以用，但是有些特意删除的功能，比如命令、性能限制、endpiont等，由于极空间不支持，所以删除了。

-------------------------------------

## 功能特点

- 读取系统中所有Docker容器信息
- 分析容器之间的网络关系（自定义network和link连接）
- 根据网络关系将相关容器分组
- 为每组容器生成对应的docker-compose.yaml文件（根据首个容器名称）
- 支持提取容器的各种配置，包括：
  - 容器名称
  - 镜像
  - 端口映射
  - 环境变量
  - 数据卷(volume/bind)
  - 网络(host/bridge/macvlan单独配置，其它网络根据名称在一起)
  - 重启策略
  - 特权模式
  - 硬件设备挂载
  - cap_add 能力
  - ~~性能限制~~(极空间暂不支持，暂时移除)
  - command和entrypoint(在ZOS系统中不生成)
  - 健康检测
  - 其他配置等等

# 使用方法

## 1、通过compose部署（推荐）

启用前确保系统安装了docker

**🔻docker cli**
```
docker run -itd --name d2c \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /{path}:/app/compose \
  -e NAS=debian \ # 可选，默认debian，详见下文说明
  -e CRON="0 */12 * * *" \ # 可选，默认每天0点起，每天12小时执行一次，详见下文说明
  -e NETWORK=true \ # 可选，默认true，详见下文说明
  -e TZ=Asia/Shanghai \ # 可选，默认Asia/Shanghai
  # 阿里云镜像源，国内选择
  crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
  # github镜像源
  # ghcr.io/coracoo/d2c:latest 
```

**🔻docker-compose.yaml**
```
services:
  d2c:
    # 阿里云镜像源，国内选择
    image: crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
    # github镜像源
    # image: ghcr.io/coracoo/d2c:latest
    container_name: d2c
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /{path}:/app/compose
    environment:
      - NAS=debian
      - CRON="0 */12 * * *"
      - NETWORK=true
      - TZ=Asia/Shanghai
```
### 环境变量说明

- `NAS`: 指定NAS系统类型
  - `debian`: 默认值，生成完整配置
  - `zos`: 极空间系统，不生成command和entrypoint配置

- `CRON`: 定时执行配置，使用标准cron表达式，示例：`0 2 * * *`（每天凌晨2点执行）
  - 默认值：`0 */12 * * *`（每天0点起，每天12小时执行一次）
  - `once`: 执行一次后退出

- `NETWORK`: 控制bridge网络配置的显示方式
  - `true`: 默认值，显式配置bridge网络模式，即新创建的compose还是在bridge网络下
  - `false`: 隐式配置bridge网络模式，即新创建的compose会遵循compose的逻辑，创建新的网络

- `TZ`: 时区，用于定时执行
  - 默认值：`Asia/Shanghai`

### 输出目录说明
- `/app/compose`: 脚本输出目录，默认值为`/app/compose`
- `YYYY_MM_DD_HH_MM`: 脚本执行时间，格式为`YYYY_MM_DD_HH_MM`，例如`2023_05_04_15_00`

## 2、直接运行（需要Python环境）

如果您的系统已安装Python环境，也可以直接运行：

1. 确保系统中已安装Python 3和Docker
2. 确保脚本有执行权限

```bash
chmod +x d2c.py
```

3. 安装python所需的依赖包

```bash
pip install -r requirements.txt
```

4. 运行脚本

```bash
./run.sh
```

5. 脚本会在当前目录下创建一个`compose`文件夹，并在其中生成docker-compose.yaml文件

## 输出说明

- 对于单个独立的容器，生成的文件名格式为：`{容器名}.yaml`
- 对于有网络关系的容器组，生成的文件名格式为：`{第一个容器名前缀}-group.yaml`
- 所有生成的文件都会保存在`compose/时间戳`目录下

## 注意事项

- 该工具需要Docker命令行权限才能正常工作
- 生成的docker-compose.yaml文件可能需要手动调整以满足特定需求
- 对于使用默认bridge网络但没有显式link的容器，它们可能会被分到不同的组中
- 工具会将自定义网络标记为`external: true`，因为它假设这些网络已经存在
- 通过Docker运行时，会将宿主机的Docker套接字挂载到容器中，以便获取容器信息
- 工具支持定时执行，默认每12小时执行一次，可通过CRON环境变量自定义执行时间

# 更新说明

## 2025-05-04(v1.0.4)
- 改进了macvlan网络配置处理，现在能够正确导出IPv4地址、IPv6地址和MAC地址
- 修复了extra_hosts配置处理，现在能够正确从容器的HostConfig.ExtraHosts获取配置
- 优化了volumes处理逻辑，支持中文路径，确保在生成的compose文件中保留原始路径
- 修复了链接处理逻辑，现在能够正确处理容器链接格式
- 改进了YAML生成逻辑，使用自定义Dumper类确保正确的缩进格式
- 添加了更多错误处理和日志输出，便于调试和跟踪处理过程


## 2025-05-04(v1.0.3)

- 添加了command、entrypoint的生成，若环境变量配置NAS配置为ZOS，则不生成
- 添加了环境变量：NAS、CRON、TZ、NETWORK
- 支持定时执行，支持标准CRON表达式；支持一次性任务执行（CRON=once）
- 重新修改yaml文件生成路径，在`./compose/`路径下，按`YYYY-MM-DD-HH-MM`时间戳组织输出文件
- 完善日志输出内容；完善README.md
- 创建Github Action，自动构建并推送到github和阿里云
- 适配 amd64/arm64/arm7 架构