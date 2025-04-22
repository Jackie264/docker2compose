#!/usr/bin/env python3

import json
import subprocess
import yaml
import os
import re
from collections import defaultdict


def run_command(command):
    """执行shell命令并返回输出
    
    当在容器内运行时，确保命令能够访问宿主机的Docker守护进程
    这需要容器启动时挂载了Docker socket (/var/run/docker.sock)
    """
    # 检查是否在容器内运行
    in_container = os.path.exists('/.dockerenv')
    
    # 如果在容器内运行且命令是docker相关，确保使用宿主机的Docker socket
    if in_container and command.startswith('docker'):
        # 确保Docker socket已挂载
        if not os.path.exists('/var/run/docker.sock'):
            print("错误: 未找到Docker socket挂载。请确保容器启动时使用了 -v /var/run/docker.sock:/var/run/docker.sock")
            return None
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"执行命令出错: {command}")
        print(f"错误信息: {stderr}")
        return None
    return stdout


def get_containers():
    """获取所有运行中的容器信息"""
    cmd = "docker ps -a --format '{{.ID}}'"
    output = run_command(cmd)
    if not output:
        return []
    
    container_ids = output.strip().split('\n')
    containers = []
    
    for container_id in container_ids:
        cmd = f"docker inspect {container_id}"
        output = run_command(cmd)
        if output:
            container_info = json.loads(output)
            # 检查容器的网络配置
            container = container_info[0]
            
            # 如果容器已停止，尝试从容器标签中获取网络信息
            if not container['State']['Running']:
                if 'Labels' in container['Config']:
                    network_labels = {k: v for k, v in container['Config']['Labels'].items() if 'network' in k.lower()}
                    if network_labels:
                        print(f"警告: 容器 {container['Name']} 已停止，但从标签中找到网络配置")
                else:
                    print(f"警告: 容器 {container['Name']} 已停止，可能无法获取完整的网络配置")
            
            containers.append(container)
    
    return containers


def get_networks():
    """获取所有网络信息"""
    cmd = "docker network ls --format '{{.ID}}'"
    output = run_command(cmd)
    if not output:
        return {}
    
    network_ids = output.strip().split('\n')
    networks = {}
    
    for network_id in network_ids:
        cmd = f"docker network inspect {network_id}"
        output = run_command(cmd)
        if output:
            network_info = json.loads(output)
            network_name = network_info[0]['Name']
            # 排除默认的bridge和host网络
            if network_name not in ['bridge', 'host', 'none']:
                networks[network_name] = network_info[0]
    
    return networks


def group_containers_by_network(containers, networks):
    """根据网络关系对容器进行分组"""
    # 初始化网络分组
    network_groups = defaultdict(list)
    container_to_networks = defaultdict(list)
    container_links = defaultdict(list)
    special_network_containers = []  # 重命名为更具描述性的名称
    
    # 记录每个容器所属的网络
    for container in containers:
        container_id = container['Id']
        container_name = container['Name'].lstrip('/')
        
        # 检查网络模式
        network_mode = container.get('HostConfig', {}).get('NetworkMode', '')
        
        # 检查是否使用特殊网络（bridge、host或macvlan）
        is_special_network = (
            network_mode in ['bridge', 'host'] or
            any(
                networks.get(net_name, {}).get('Driver', '') == 'macvlan'
                for net_name in container.get('NetworkSettings', {}).get('Networks', {})
            )
        )
        
        if is_special_network:
            special_network_containers.append(container_id)
            continue
            
        # 处理网络连接
        for network_name, network_config in container.get('NetworkSettings', {}).get('Networks', {}).items():
            # 排除默认的bridge和host网络
            if network_name not in ['bridge', 'host', 'none']:
                container_to_networks[container_id].append(network_name)
                network_groups[network_name].append(container_id)
        
        # 处理容器链接
        for link in container.get('HostConfig', {}).get('Links', []) or []:
            linked_container = link.split(':')[0].lstrip('/')
            container_links[container_id].append(linked_container)
    
    # 合并有链接关系的容器组
    merged_groups = []
    processed_networks = set()
    
    # 首先基于自定义网络分组
    for network_name, container_ids in network_groups.items():
        if network_name in processed_networks:
            continue
            
        group = set(container_ids)
        processed_networks.add(network_name)
        
        # 查找与当前网络有重叠容器的其他网络
        for other_network, other_containers in network_groups.items():
            if other_network != network_name and not other_network in processed_networks:
                if any(c in group for c in other_containers):
                    group.update(other_containers)
                    processed_networks.add(other_network)
        
        merged_groups.append(list(group))
    
    # 处理通过links连接但没有共享自定义网络的容器
    for container_id, linked_containers in container_links.items():
        if not any(container_id in group for group in merged_groups):
            # 查找所有链接的容器
            linked_group = {container_id}
            for linked in linked_containers:
                for c in containers:
                    if c['Name'].lstrip('/') == linked:
                        linked_group.add(c['Id'])
            
            # 检查是否可以合并到现有组
            merged = False
            for i, group in enumerate(merged_groups):
                if any(c in group for c in linked_group):
                    merged_groups[i] = list(set(group).union(linked_group))
                    merged = True
                    break
            
            if not merged:
                merged_groups.append(list(linked_group))
    
    # 处理剩余的独立容器
    standalone_containers = []
    for container in containers:
        container_id = container['Id']
        if not any(container_id in group for group in merged_groups) and container_id not in special_network_containers:
            standalone_containers.append(container_id)
    
    if standalone_containers:
        merged_groups.append(standalone_containers)
    
    # 为每个bridge、host或macvlan网络的容器创建单独的组
    for container_id in special_network_containers:
        merged_groups.append([container_id])
    
    return merged_groups


def convert_container_to_service(container):
    """将容器配置转换为docker-compose服务配置"""
    service = {}
    
    # 基本信息
    container_name = container['Name'].lstrip('/')
    service['container_name'] = container_name
    
    # 镜像
    service['image'] = container['Config']['Image']
    
    # 重启策略
    restart_policy = container['HostConfig'].get('RestartPolicy', {})
    if restart_policy and restart_policy.get('Name'):
        if restart_policy['Name'] != 'no':
            service['restart'] = restart_policy['Name']
            if restart_policy['Name'] == 'on-failure' and restart_policy.get('MaximumRetryCount'):
                service['restart'] = f"{restart_policy['Name']}:{restart_policy['MaximumRetryCount']}"
    
    # 端口映射 - 优化连续端口和简化格式
    port_mappings = {}
    for port in container['NetworkSettings'].get('Ports', {}) or {}:
        if container['NetworkSettings']['Ports'][port]:
            for binding in container['NetworkSettings']['Ports'][port]:
                # 提取端口信息
                host_ip = binding['HostIp']
                host_port = int(binding['HostPort'])  # 转换为整数
                container_port = port.split('/')[0]  # 移除协议部分
                protocol = port.split('/')[1] if '/' in port else 'tcp'
                
                # 标准化IP地址
                if host_ip in ['0.0.0.0', '::', '']:
                    key = f"{container_port}/{protocol}"
                else:
                    key = f"{host_ip}:{container_port}/{protocol}"
                
                # 使用集合去重
                if key not in port_mappings:
                    port_mappings[key] = set()
                port_mappings[key].add(host_port)
    
    # 处理端口映射，合并连续端口
    ports = []
    for container_port, host_ports in port_mappings.items():
        # 转换为列表并排序
        host_ports = sorted(list(host_ports))
        
        # 查找连续的端口范围
        if len(host_ports) > 0:
            ranges = []
            start = host_ports[0]
            prev = start
            
            for curr in host_ports[1:]:
                if curr != prev + 1:
                    # 如果不连续，添加之前的范围
                    if start == prev:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"{start}-{prev}")
                    start = curr
                prev = curr
            
            # 添加最后一个范围
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            
            # 生成端口映射字符串
            if ':' in container_port:  # 包含特定IP
                host_ip, port_proto = container_port.split(':', 1)
                for port_range in ranges:
                    ports.append(f"{host_ip}:{port_range}:{port_proto}")
            else:
                for port_range in ranges:
                    ports.append(f"{port_range}:{container_port}")
    
    if ports:
        service['ports'] = ports
    
    # 环境变量 (忽略PATH)
    if container['Config'].get('Env'):
        env = {}
        for env_var in container['Config']['Env']:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                if key != 'PATH':  # 忽略PATH环境变量
                    env[key] = value
        if env:
            service['environment'] = env
    
    # 数据卷
    volumes = []
    for mount in container['Mounts']:
        if mount['Type'] == 'bind':
            mode = mount.get('RW', True)
            if mode:
                mode_suffix = 'rw'
            else:
                mode_suffix = 'ro'
            volumes.append(f"{mount['Source']}:{mount['Destination']}:{mode_suffix}")
        elif mount['Type'] == 'volume':
            mode = mount.get('RW', True)
            if mode :
                mode_suffix = 'rw'
            else:
                mode_suffix = 'ro'
                print('ro')
            volumes.append(f"{mount['Name']}:{mount['Destination']}:{mode_suffix}")
    if volumes:
        service['volumes'] = volumes
    
    # 网络配置
    network_mode = container['HostConfig'].get('NetworkMode', '')
    if network_mode == 'host':
        service['network_mode'] = 'host'
    else:
        networks = []
        for network_name in container['NetworkSettings'].get('Networks', {}):
            if network_name not in ['bridge', 'host', 'none']:
                networks.append(network_name)
        if networks:
            service['networks'] = networks
    
    # 链接
    links = container['HostConfig'].get('Links', [])
    if links:
        service['links'] = [link.replace(':', ':') for link in links]
    
    # 其他常用配置
    if container['HostConfig'].get('Privileged'):
        service['privileged'] = container['HostConfig']['Privileged']
    
    # 处理设备挂载
    if container['HostConfig'].get('Devices'):
        devices = []
        for device in container['HostConfig']['Devices']:
            devices.append(f"{device['PathOnHost']}:{device['PathInContainer']}:{device['CgroupPermissions']}")
        service['devices'] = devices
    
    # 只保留watchtower.enable标签
    if container['Config'].get('Labels'):
        labels = {}
        for label_key, label_value in container['Config']['Labels'].items():
            # 保留所有watchtower相关标签
            if 'watchtower' in label_key.lower():
                labels[label_key] = label_value
            # 保留其他重要标签
            # elif label_key.startswith('com.') or label_key.startswith('org.') or label_key.startswith('io.'):
            #    labels[label_key] = label_value
        if labels:
            service['labels'] = labels
    
    # 添加容器权限
    if container['HostConfig'].get('CapAdd'):
        caps = []
        if 'SYS_ADMIN' in container['HostConfig']['CapAdd']:
            service['security_opt'] = ['apparmor:unconfined']
            caps.append('SYS_ADMIN')
        if 'NET_ADMIN' in container['HostConfig']['CapAdd']:
            service['security_opt'] = ['apparmor:unconfined']
            caps.append('NET_ADMIN')
        if caps:
            service['cap_add'] = caps
    
    # 添加资源限制配置
    host_config = container.get('HostConfig', {})
    
    # CPU限制
    cpu_shares = host_config.get('CpuShares')
    cpu_period = host_config.get('CpuPeriod')
    cpu_quota = host_config.get('CpuQuota')
    cpuset_cpus = host_config.get('CpusetCpus')
    
    # 内存限制
    memory = host_config.get('Memory')
    memory_swap = host_config.get('MemorySwap')
    memory_reservation = host_config.get('MemoryReservation')
    
    # 如果设置了资源限制，添加到服务配置中
    if any([cpu_shares, cpu_period, cpu_quota, cpuset_cpus, memory, memory_swap, memory_reservation]):
        deploy = {}
        resources = {'limits': {}, 'reservations': {}}
        
        # CPU配置
        if cpu_quota and cpu_period:
            # 将CPU配额转换为cores数量
            cores = float(cpu_quota) / float(cpu_period)
            resources['limits']['cpus'] = str(cores)
        elif cpu_shares:
            # cpu_shares是相对权重，1024为默认值
            resources['limits']['cpus'] = str(float(cpu_shares) / 1024.0)
        
        if cpuset_cpus:
            resources['limits']['cpus'] = cpuset_cpus
        
        # 内存配置
        if memory and memory > 0:
            resources['limits']['memory'] = memory
        if memory_reservation and memory_reservation > 0:
            resources['reservations']['memory'] = memory_reservation
        
        # 只有当实际设置了资源限制时才添加配置
        if resources['limits'] or resources['reservations']:
            deploy['resources'] = resources
            service['deploy'] = deploy
    
    return service


def generate_compose_file(containers_group, all_containers, output_dir):
    """为一组容器生成docker-compose.yaml文件"""
    compose = {
        'version': '3',
        'services': {},
    }
    
    # 添加网络配置
    networks = set()
    for container_id in containers_group:
        for container in all_containers:
            if container['Id'] == container_id:
                for network_name in container['NetworkSettings'].get('Networks', {}):
                    if network_name not in ['bridge', 'host', 'none']:
                        networks.add(network_name)
    
    if networks:
        compose['networks'] = {network: {'external': True} for network in networks}
    
    # 添加服务配置
    for container_id in containers_group:
        for container in all_containers:
            if container['Id'] == container_id:
                container_name = container['Name'].lstrip('/')
                service_name = re.sub(r'[^a-zA-Z0-9_]', '_', container_name)
                compose['services'][service_name] = convert_container_to_service(container)
    
    # 生成文件名
    if len(containers_group) == 1:
        for container in all_containers:
            if container['Id'] == containers_group[0]:
                filename = f"{container['Name'].lstrip('/')}.yaml"
                break
    else:
        # 使用第一个容器的名称作为文件名前缀
        for container in all_containers:
            if container['Id'] == containers_group[0]:
                prefix = container['Name'].lstrip('/').split('_')[0]
                filename = f"{prefix}-group.yaml"
                break
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 写入文件
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w') as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
    
    print(f"已生成 {file_path}")
    return file_path


def main():
    print("开始读取Docker容器信息...")
    containers = get_containers()
    if not containers:
        print("未找到Docker容器")
        return
    
    print(f"找到 {len(containers)} 个Docker容器")
    
    print("读取网络信息...")
    networks = get_networks()
    print(f"找到 {len(networks)} 个自定义网络")
    
    print("根据网络关系对容器进行分组...")
    container_groups = group_containers_by_network(containers, networks)
    print(f"分组完成，共 {len(container_groups)} 个分组")
    
    # 创建输出目录
    output_dir = "compose"
    
    print("生成docker-compose文件...")
    generated_files = []
    for i, group in enumerate(container_groups):
        print(f"处理第 {i+1} 组，包含 {len(group)} 个容器")
        file_path = generate_compose_file(group, containers, output_dir)
        generated_files.append(file_path)
    
    print("\n生成完成！生成的文件列表:")
    for file_path in generated_files:
        print(f"- {file_path}")


if __name__ == "__main__":
    main()