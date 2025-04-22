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
  - ~~性能限制~~(极空间暂不支持，所以删除了)
  - 其他配置等等

## 使用方法

### 通过compose部署（推荐）

启用前确保系统安装了docker

**🔻docker cli**
```
docker run -itd --name d2c \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /{path}:/app/compose \
  crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
```

**🔻docker-compose.yaml**
```
services:
  d2c:
    image: crpi-xg6dfmt5h2etc7hg.cn-hangzhou.personal.cr.aliyuncs.com/cherry4nas/d2c:latest
    container_name: d2c
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /{path}:/app/compose
```

### 直接运行（需要Python环境）

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
- 所有生成的文件都会保存在`compose`目录下

## 注意事项

- 该工具需要Docker命令行权限才能正常工作
- 生成的docker-compose.yaml文件可能需要手动调整以满足特定需求
- 对于使用默认bridge网络但没有显式link的容器，它们可能会被分到不同的组中
- 工具会将自定义网络标记为`external: true`，因为它假设这些网络已经存在
- 通过Docker运行时，会将宿主机的Docker套接字挂载到容器中，以便获取容器信息