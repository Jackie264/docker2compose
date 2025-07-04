# 前言

本工具用于读取极空间私有云系统中的存量Docker容器信息，自动生成对应的docker-compose.yaml文件。

它会根据容器之间的网络关系（自定义网络或link连接）将相关容器分组，并为每组容器生成一个独立的docker-compose.yaml文件。

理论上所有NAS都可以用，但是有些特意删除的功能，比如命令、性能限制、endpiont等，由于极空间不支持，所以删除了。

# 我的仓库

**1️⃣** ： 中文docker项目集成项目： [https://github.com/coracoo/awesome_docker_cn](https://github.com/coracoo/awesome_docker_cn)

**2️⃣** ： docker转compose：[https://github.com/coracoo/docker2compose](https://github.com/coracoo/docker2compose)

**3️⃣** ： 容器部署iSCSI，支持绿联极空间飞牛：[https://github.com/coracoo/d-tgtadm/](https://github.com/coracoo/d-tgtadm/)


# 我的频道

### 首发平台——什么值得买：

### [⭐点我关注](https://zhiyou.smzdm.com/member/9674309982/) 

### 微信公众号：

![关注](https://github.com/user-attachments/assets/9a1c4de0-2f08-413f-ab7f-d7d463af1698)

-------------------------------------

## 功能特点

- 纯AI打造，有问题提issuse，特殊容器贴原docker cli
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
  - command和entrypoint(在ZOS模式下不生成)
  - 健康检测
  - 其他配置等等

## 🌐全新的 Web UI 访问

部署完成后，可通过浏览器访问Web界面：
- 本地访问：`http://localhost:5000`
- 局域网访问：`http://你的IP地址:5000`

### Web UI功能特点

- 📊 **容器管理**：实时查看所有Docker容器状态，按网络关系自动分组
- 📄 **Compose预览**：直接在界面中查看生成的docker-compose.yaml文件内容
- ⏰ **调度器监控**：实时监控定时任务状态，查看执行日志
- 🚀 **立即执行**：一键执行compose文件生成任务
- 🗂️ **文件管理**：浏览和管理生成的compose文件目录
- 📝 **日志查看**：查看详细的执行日志，支持清空日志功能

🔻项目首页
![QQ_1751597270453](https://github.com/user-attachments/assets/d1b40dd7-408b-4f87-9756-a35ffe74a5da)

🔻可视化配置编辑
![QQ_1751597299766](https://github.com/user-attachments/assets/beff1d61-e495-491f-a1db-62cf59d5ce8d)

🔻定时任务管理
![QQ_1751597315617](https://github.com/user-attachments/assets/6eec9ece-e670-4ddb-b28e-bf301d22e8e7)

### 配置文件说明 (/app/config.json)

- `NAS`: 指定NAS系统类型
  - `debian`: 默认值，生成完整配置
  - `zos`: 极空间系统，不生成command和entrypoint配置

- `CRON`: 定时执行配置，支持5位\6位Cron规则，示例：`0 2 * * *`（每天凌晨2点执行）
  - 默认值：`0 */12 * * *`（每天0点起，每天12小时执行一次）
  - `once`: 执行一次后退出

- `NETWORK`: 控制bridge网络配置的显示方式
  - `true`: 默认值，在生成的compose.yaml中显式添加 `network_mode: bridge` 配置
  - `false`: 隐藏bridge网络配置，不在compose.yaml中显示 `network_mode: bridge`（因为bridge是Docker默认网络模式）

- `TZ`: 时区，用于定时执行
  - 默认值：`Asia/Shanghai`

### 输出目录说明
- `/app/compose`: 脚本输出目录，默认值为`/app/compose`
- `/app/compose/YYYY_MM_DD_HH_MM`: 定时任务输出目录，格式为`YYYY_MM_DD_HH_MM`，例如`2023_05_04_15_00`

### 输出说明

- 对于单个独立的容器，生成的文件名格式为：`{容器名}.yaml`
- 对于有网络关系的容器组，生成的文件名格式为：`{第一个容器名前缀}-group.yaml`
- 所有生成的文件都会保存在`compose/时间戳`目录下

### 注意事项

- 该工具需要Docker命令行权限才能正常工作
- 生成的docker-compose.yaml文件可能需要手动调整以满足特定需求
- 通过Docker运行时，会将宿主机的Docker套接字挂载到容器中，以便获取容器信息
- 工具支持定时执行，默认`once`（只执行一次），可通过CRON环境变量自定义执行时间
- 关于Macvlan网络，DHCP的理论上会展示`macvlan:{}`，
- 对于使用默认bridge网络但没有显式link的容器，它们可能会被分到不同的组中
- 工具会将自定义网络标记为`external: true`，因为它假设这些网络已经存在

-------------------------------------

# 使用方法

## 1、通过compose部署（推荐）

启用前确保系统安装了docker

**🔻docker cli**
```bash
docker run -itd --name d2c \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /{path}:/app/compose \
  -p 5000:5000 \
  crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
  # 或使用github镜像源：ghcr.io/coracoo/d2c:latest
```

**🔻docker-compose.yaml**
```yaml
services:
  d2c:
    # 阿里云镜像源，国内选择
    image: crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
    # github镜像源
    # image: ghcr.io/coracoo/d2c:latest
    container_name: d2c
    ports:
      - "5000:5000"  # Web UI端口
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /{path}:/app/compose
```

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

-------------------------------------

# 更新说明

## 2025-07-03(v1.1.0)
- 🎉 **新增Web UI界面**：
  - 采用全新得现代化的图形界面设计，原CLI模式保留不变。
  - 左侧为容器分组展示，支持按网络关系自动分组，包含运行状态、容器数量等。
  - 中间为文件列表，展示`/app/compose`目录下所有得`yaml`文件。
  - 右侧是Compose编辑区域，支持勾选docker整合compose。
  - 新增设置页面，用来编辑配置文件。
  - 新增任务计划页面，用来执行定时任务。
  - 新增日志查看页面，用来查看任务执行日志。

- 🔧 **修改代码逻辑**：
  - 去除环境变量，所有参数通过`/app/config/json`来配置（参考前面得配置文件说明）。
  - 新增系统CRON和Python调度器来执行CRON任务，彻底解决5、6位CRON的问题。
  - 初次登录会自动生成所有得容器yaml文件，保存在`/app/compose`目录下。

- 🐛 **修复已知问题**：
  - 解决多个稳定性和兼容性问题
  - 改进错误处理和异常捕获机制
  - 优化代码注释和函数级文档

## 2025-07-03(v1.0.5)
- 修复了volumes挂载权限处理逻辑，移除不必要的:rw后缀，只在只读模式时添加:ro后缀
- 优化了healthcheck的CMD-SHELL格式处理，确保生成符合Docker Compose规范的配置
- 改进了volumes处理逻辑，使生成的compose文件更简洁，符合Docker Compose最佳实践
- 添加了healthcheck处理过程的调试日志输出，便于跟踪问题
- 完善了代码注释和错误处理逻辑
- 修复了cron表达式的时区问题，确保定时任务在正确的时区执行
- 修复了extra_hosts配置处理，现在能够正确从容器的HostConfig.ExtraHosts获取配置

## 2025-06-04(v1.0.4)
- 改进了macvlan网络配置处理，现在能够正确导出IPv4地址、IPv6地址和MAC地址
- 优化了volumes处理逻辑，支持中文路径，确保在生成的compose文件中保留原始路径
- 修复了链接处理逻辑，现在能够正确处理容器链接格式
- 改进了YAML生成逻辑，使用自定义Dumper类确保正确的缩进格式
- 添加了更多错误处理和日志输出，便于调试和跟踪处理过程

## 2025-05-05(v1.0.3)
- 添加了command、entrypoint的生成，若环境变量配置NAS配置为ZOS，则不生成
- 添加了环境变量：NAS、CRON、TZ、NETWORK
- 支持定时执行，支持标准CRON表达式；支持一次性任务执行（CRON=once）
- 重新修改yaml文件生成路径，在`./compose/`路径下，按`YYYY-MM-DD-HH-MM`时间戳组织输出文件
- 完善日志输出内容；完善README.md
- 创建Github Action，自动构建并推送到github和阿里云
- 适配 amd64/arm64/arm7 架构
