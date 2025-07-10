#!/usr/bin/env python3
"""
D2C Web UI - Docker to Compose 图形化界面
提供简洁、现代化的Web界面来管理Docker容器和生成Compose文件
"""

import os
import json
import yaml
from flask import Flask, render_template, request, jsonify, send_from_directory
from d2c import get_containers, get_networks, convert_container_to_service, group_containers_by_network, generate_compose_for_selected_containers, generate_compose_file
import subprocess
from datetime import datetime, timedelta
import pytz
import glob
from d2c import ensure_config_file
from cron_utils import CronUtils

app = Flask(__name__)

# 配置静态文件路径
app.static_folder = 'static'
app.template_folder = 'templates'

def get_timezone_from_config():
    """从配置文件获取时区设置"""
    try:
        config_file = '/app/config/config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            tz_str = config.get('TZ', 'Asia/Shanghai')
            return pytz.timezone(tz_str)
    except Exception as e:
        print(f"获取时区配置失败: {e}，使用默认时区 Asia/Shanghai")
    return pytz.timezone('Asia/Shanghai')

def get_localized_timestamp():
    """获取本地化的时间戳"""
    tz = get_timezone_from_config()
    now = datetime.now(tz)
    return now.strftime("%Y_%m_%d_%H_%M")

def ensure_compose_files_exist():
    """确保compose文件已生成，如果没有则自动生成一次"""
    compose_dir = "/app/compose"
    
    # 检查是否存在compose文件
    if os.path.exists(compose_dir):
        yaml_files = glob.glob(os.path.join(compose_dir, "**/*.yaml"), recursive=True)
        if yaml_files:
            print(f"发现已存在的compose文件: {len(yaml_files)} 个")
            return
    
    print("未发现compose文件，自动执行一次生成...")
    try:
        # 设置环境变量并执行d2c.py
        env = os.environ.copy()
        env['CRON'] = 'once'
        
        result = subprocess.run(
            ['python3', '/app/d2c.py'],
            env=env,
            capture_output=True,
            text=True,
            cwd='/app'
        )
        
        if result.returncode == 0:
            print("自动生成compose文件成功")
        else:
            print(f"自动生成compose文件失败: {result.stderr}")
    except Exception as e:
        print(f"执行自动生成时出错: {e}")

def find_compose_file_for_container(container_name):
    """查找容器对应的compose文件"""
    compose_dir = "/app/compose"
    
    if not os.path.exists(compose_dir):
        print(f"compose目录不存在: {compose_dir}")
        return None
    
    print(f"查找容器 {container_name} 对应的compose文件...")
    
    # 首先尝试直接匹配文件名
    direct_match = os.path.join(compose_dir, f"{container_name}.yaml")
    if os.path.exists(direct_match):
        print(f"找到直接匹配的文件: {direct_match}")
        return direct_match
    
    # 搜索所有yaml文件
    yaml_files = glob.glob(os.path.join(compose_dir, "*.yaml"))
    print(f"搜索到的yaml文件: {yaml_files}")
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查文件内容是否包含容器名或container_name
                if container_name in content or f"container_name: {container_name}" in content:
                    print(f"在文件 {yaml_file} 中找到容器 {container_name}")
                    return yaml_file
        except Exception as e:
            print(f"读取文件 {yaml_file} 时出错: {e}")
            continue
    
    print(f"未找到容器 {container_name} 对应的compose文件")
    return None

def get_container_groups():
    """获取容器分组信息"""
    try:
        containers = get_containers()
        networks = get_networks()
        groups = group_containers_by_network(containers, networks)
        
        result = []
        for i, group in enumerate(groups):
            group_containers = []
            for container_id in group:
                container = next((c for c in containers if c['Id'] == container_id), None)
                if container:
                    container_name = container['Name'].lstrip('/')
                    compose_file = find_compose_file_for_container(container_name)
                    
                    group_containers.append({
                        'id': container['Id'][:12],
                        'name': container_name,
                        'image': container['Config']['Image'],
                        'status': 'running' if container['State']['Running'] else 'stopped',
                        'network_mode': container['HostConfig'].get('NetworkMode', 'default'),
                        'compose_file': compose_file
                    })
            
            if group_containers:
                # 确定组名
                if len(group_containers) == 1:
                    group_name = group_containers[0]['name']
                    group_type = 'single'
                else:
                    # 使用第一个容器名作为组名前缀
                    first_name = group_containers[0]['name']
                    group_name = f"{first_name}-group"
                    group_type = 'group'
                
                result.append({
                    'id': f'group_{i}',
                    'name': group_name,
                    'type': group_type,
                    'containers': group_containers,
                    'count': len(group_containers),
                    'expanded': i == 0  # 只有第一个分组默认展开
                })
        
        return result
    except Exception as e:
        print(f"获取容器分组时出错: {e}")
        return []

def generate_compose_for_containers(container_ids):
    """为指定容器生成compose配置"""
    return generate_compose_for_selected_containers(container_ids)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/containers')
def api_containers():
    """获取容器分组API"""
    try:
        groups = get_container_groups()
        return jsonify({'success': True, 'data': groups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/compose-file/<container_id>')
def api_get_compose_file(container_id):
    """获取容器对应的compose文件内容"""
    try:
        # 根据容器ID查找对应的compose文件
        containers = get_containers()
        container = None
        
        for c in containers:
            if c['Id'].startswith(container_id) or c['Id'][:12] == container_id:
                container = c
                break
        
        if not container:
            return jsonify({
                'success': False,
                'error': '容器未找到'
            }), 404
        
        container_name = container['Names'][0].lstrip('/')
        compose_file = find_compose_file_for_container(container_name)
        
        if not compose_file:
            return jsonify({
                'success': False,
                'error': '未找到对应的compose文件'
            }), 404
        
        with open(compose_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'data': {
                'content': content,
                'filename': os.path.basename(compose_file),
                'filepath': compose_file
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/compose', methods=['POST'])
def api_compose():
    """生成compose文件API"""
    try:
        data = request.get_json()
        container_ids = data.get('container_ids', [])
        
        if not container_ids:
            return jsonify({'success': False, 'error': '请选择至少一个容器'})
        
        compose_config = generate_compose_for_selected_containers(container_ids)
        if compose_config is None:
            return jsonify({'success': False, 'error': '未找到指定的容器'})
        
        # 使用与d2c.py相同的自定义YAML Dumper类来确保正确的缩进
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)
            
            def write_line_break(self, data=None):
                super(MyDumper, self).write_line_break(data)
                if len(self.indents) == 1:
                    super(MyDumper, self).write_line_break()
        
        # 转换为YAML格式，使用自定义的Dumper类
        yaml_content = yaml.dump(compose_config, Dumper=MyDumper, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2, width=float('inf'))
        
        return jsonify({
            'success': True, 
            'data': {
                'yaml': yaml_content,
                'config': compose_config
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/save-compose', methods=['POST'])
def api_save_compose():
    """保存compose文件API"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'custom-compose.yaml')
        content = data.get('content', '')
        
        # 确保文件名以.yaml结尾
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        # 创建输出目录
        timestamp = get_localized_timestamp()
        output_dir = f"/app/compose/{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True, 
            'message': f'文件已保存到 {file_path}',
            'path': file_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files')
def api_files():
    """获取compose目录下的文件夹结构"""
    try:
        compose_dir = '/app/compose'
        result = {
            'root': [],
            'folders': {}
        }
        
        if os.path.exists(compose_dir):
            # 获取根目录下的文件
            for item in os.listdir(compose_dir):
                item_path = os.path.join(compose_dir, item)
                if os.path.isfile(item_path) and item.endswith(('.yaml', '.yml')):
                    stat = os.stat(item_path)
                    result['root'].append({
                        'name': item,
                        'path': item_path,
                        'modified': stat.st_mtime,
                        'size': stat.st_size,
                        'type': 'file'
                    })
                elif os.path.isdir(item_path):
                    # 处理子文件夹
                    folder_files = []
                    for subitem in os.listdir(item_path):
                        if subitem.endswith(('.yaml', '.yml')):
                            subitem_path = os.path.join(item_path, subitem)
                            if os.path.isfile(subitem_path):
                                stat = os.stat(subitem_path)
                                folder_files.append({
                                    'name': subitem,
                                    'path': subitem_path,
                                    'modified': stat.st_mtime,
                                    'size': stat.st_size,
                                    'type': 'file'
                                })
                    
                    if folder_files:
                        # 按修改时间倒序排列文件夹内的文件
                        folder_files.sort(key=lambda x: x['modified'], reverse=True)
                        # 获取文件夹的最新修改时间
                        folder_stat = os.stat(item_path)
                        result['folders'][item] = {
                            'name': item,
                            'path': item_path,
                            'modified': folder_stat.st_mtime,
                            'files': folder_files,
                            'type': 'folder'
                        }
        
        # 按修改时间倒序排列根目录文件
        result['root'].sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/file-content', methods=['POST'])
def api_file_content():
    """获取文件内容"""
    try:
        data = request.get_json()
        file_path = data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 安全检查：确保文件在compose目录下
        compose_dir = os.path.abspath("/app/compose")
        abs_file_path = os.path.abspath(file_path)
        if not abs_file_path.startswith(compose_dir):
            return jsonify({
                'success': False,
                'error': '无权访问该文件'
            }), 403
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'data': {
                'content': content,
                'filename': os.path.basename(file_path),
                'filepath': file_path
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-file', methods=['POST'])
def api_delete_file():
    """删除文件或文件夹"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '文件路径不能为空'
            }), 400
        
        # 安全检查：确保文件路径在允许的目录下
        compose_dir = '/app/compose'
        if not file_path.startswith(compose_dir):
            return jsonify({
                'success': False,
                'error': '文件路径不在允许的目录下'
            }), 403
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件或文件夹不存在'
            }), 404
        
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-all-compose', methods=['POST'])
def api_generate_all_compose():
    """生成全量Compose文件"""
    try:
        # 导入d2c模块
        import d2c
        import yaml
        
        # 获取所有容器
        containers = d2c.get_containers()
        if not containers:
            return jsonify({
                'success': False,
                'error': '未找到任何容器'
            }), 404
        
        # 获取所有容器ID
        container_ids = [container['Id'] for container in containers]
        
        # 生成compose配置
        compose_config = d2c.generate_compose_for_selected_containers(container_ids)
        
        if not compose_config:
            return jsonify({
                'success': False,
                'error': '生成Compose配置失败'
            }), 500
        
        # 保存文件到磁盘
        timestamp = get_localized_timestamp()
        output_dir = f"/app/compose/{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = 'all-containers-compose.yaml'
        file_path = os.path.join(output_dir, filename)
        
        # 使用与d2c.py相同的自定义YAML Dumper类
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)
            
            def write_line_break(self, data=None):
                super(MyDumper, self).write_line_break(data)
                if len(self.indents) == 1:
                    super(MyDumper, self).write_line_break()
        
        # 转换为YAML格式并保存
        yaml_content = yaml.dump(compose_config, Dumper=MyDumper, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2, width=float('inf'))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return jsonify({
            'success': True,
            'message': f'全量Compose文件生成成功，保存到: {file_path}',
            'filename': filename,
            'filepath': file_path
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取配置设置"""
    try:
        config_file = '/app/config/config.json'
        
        # 默认设置
        default_settings = {
            'NAS': 'debian',
            'CRON': 'once',
            'NETWORK': 'true',
            'TZ': 'Asia/Shanghai'
        }
        
        # 优先从配置文件读取设置
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 只提取非注释字段（不以//开头的字段）
                saved_settings = {k: v for k, v in saved_config.items() if not k.startswith('//')}
                default_settings.update(saved_settings)
        
        return jsonify({
            'success': True,
            'settings': default_settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """保存配置设置"""
    try:
        data = request.get_json()
        settings = data.get('settings', {})
        
        config_file = '/app/config/config.json'
        cron_expr = settings.get('CRON', 'once')
        
        # 初始化CRON工具
        cron_utils = CronUtils()
        cron_utils.set_debug(True)
        
        # 标准化和验证CRON表达式
        if cron_expr != 'once':
            # 标准化CRON表达式（处理全角字符等）
            normalized_cron = cron_utils.normalize_cron_expression(cron_expr)
            
            # 验证CRON表达式
            is_valid, field_count, error_msg = cron_utils.validate_cron_expression(normalized_cron)
            
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': f'无效的CRON表达式: {error_msg}',
                    'original_cron': cron_expr,
                    'normalized_cron': normalized_cron
                }), 400
            
            # 使用标准化后的表达式
            cron_expr = normalized_cron
            settings['CRON'] = cron_expr
        
        # 检测6位CRON表达式
        is_6_field_cron = False
        scheduler_switch_message = ''
        
        if cron_expr != 'once':
            is_6_field_cron = cron_utils.is_6_field_cron(cron_expr)
            if is_6_field_cron:
                scheduler_switch_message = '检测到6位CRON格式，建议使用Python精确调度器以支持秒级调度。'
        
        # 创建包含注释的配置结构，保持与d2c.py中default_config一致
        config_with_comments = {
            "// 配置说明": "以下是D2C的配置选项",
            "// NAS": "指定NAS系统类型: debian(默认,生成完整配置) 或 zos(极空间系统,不生成command和entrypoint)",
            "NAS": settings.get('NAS', 'debian'),
            "// CRON": "定时执行配置,使用标准cron表达式,如'0 2 * * *'(每天凌晨2点),'once'(执行一次后退出)。支持6位格式(秒 分 时 日 月 周)",
            "CRON": cron_expr,
            "// NETWORK": "控制bridge网络配置的显示方式: true(显示) 或 false(隐藏)",
            "NETWORK": settings.get('NETWORK', 'true'),
            "// TZ": "时区设置,如Asia/Shanghai、Europe/London等",
            "TZ": settings.get('TZ', 'Asia/Shanghai')
        }
        
        # 保存设置到配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_with_comments, f, indent=2, ensure_ascii=False)
        
        # 如果检测到6位CRON且当前有调度器在运行，重启调度器以应用新配置
        if is_6_field_cron:
            try:
                # 检查当前调度器状态
                status_result = subprocess.run(
                    ['/app/scheduler_manager.sh', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # 如果调度器正在运行，重启以应用新的6位CRON配置
                if ('正在运行' in status_result.stdout or 
                    '调度器正在运行' in status_result.stdout):
                    
                    # 重启调度器
                    restart_result = subprocess.run(
                        ['/app/scheduler_manager.sh', 'restart'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if restart_result.returncode == 0:
                        scheduler_switch_message += ' 调度器已自动重启以应用6位CRON配置。'
                    else:
                        scheduler_switch_message += ' 请手动重启调度器以应用6位CRON配置。'
                        
            except Exception as e:
                scheduler_switch_message += f' 自动重启调度器失败: {str(e)}'
        
        response_message = '设置保存成功'
        if scheduler_switch_message:
            response_message += '。' + scheduler_switch_message
        
        return jsonify({
            'success': True,
            'message': response_message,
            'is_6_field_cron': is_6_field_cron
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/start', methods=['POST'])
def api_start_scheduler():
    """启动定时任务"""
    try:
        # 检查当前CRON配置
        config_file = '/app/config/config.json'
        current_cron = 'once'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                current_cron = config.get('CRON', 'once')
            except Exception:
                pass
        
        # 如果是once模式，提示用户修改CRON配置
        if current_cron == 'once':
            return jsonify({
                'success': False,
                'error': 'CRON配置为"once"模式，无法启动定时任务。请在设置中修改CRON表达式后再启动定时任务，或者点击"立即运行"执行一次性任务。',
                'suggestion': 'modify_cron'
            }), 400
        
        # 启动调度器（scheduler_manager.sh会自动检测CRON格式并选择合适的调度器）
        result = subprocess.run(
            ['/app/scheduler_manager.sh', 'start'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        
        # 检查是否已经在运行中（返回码为1但输出包含运行状态信息）
        if "已经在运行中" in output or "调度器已经在运行" in output or "正在运行" in output:
            # 判断运行的调度器类型
            if "Python调度器已经在运行中" in output:
                scheduler_type = 'python'
                message = 'Python精确调度器已在运行中，支持6位CRON格式。如需重启，请先停止当前调度器。'
            elif "系统CRON调度器已经在运行中" in output:
                scheduler_type = 'system_cron'
                message = '系统CRON调度器已在运行中。如需切换到Python调度器以支持6位CRON格式，请先停止当前调度器。'
            else:
                scheduler_type = 'unknown'
                message = '调度器已在运行中。如需重启，请先停止当前调度器。'
            
            return jsonify({
                'success': False,
                'error': message,
                'status': 'already_running',
                'scheduler_type': scheduler_type,
                'suggestion': 'stop_first',
                'output': output
            }), 409  # 409 Conflict - 资源冲突
        
        if result.returncode == 0:
            # 解析输出信息以确定启动的调度器类型
            if "Python精确调度器启动成功" in output:
                return jsonify({
                    'success': True,
                    'message': '调度器启动成功，已自动选择Python精确调度器支持6位CRON格式',
                    'scheduler_type': 'python',
                    'output': output
                })
            elif "系统CRON启动成功" in output:
                return jsonify({
                    'success': True,
                    'message': '调度器启动成功，已自动选择系统CRON调度器',
                    'scheduler_type': 'system_cron',
                    'output': output
                })
            elif "一次性任务执行完成" in output:
                return jsonify({
                    'success': True,
                    'message': '一次性任务执行完成',
                    'scheduler_type': 'once',
                    'output': output
                })
            else:
                return jsonify({
                    'success': True,
                    'message': '调度器启动成功',
                    'output': output
                })
        else:
            return jsonify({
                'success': False,
                'error': f'调度器启动失败: {result.stderr or result.stdout}',
                'output': result.stdout
            }), 500
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '启动超时，请检查系统状态'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def api_stop_scheduler():
    """停止定时任务"""
    try:
        # 使用scheduler_manager.sh停止定时任务，增加超时时间
        result = subprocess.run(
            ['/app/scheduler_manager.sh', 'stop'],
            capture_output=True,
            text=True,
            timeout=60  # 增加到60秒超时
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '定时任务停止成功',
                'output': result.stdout
            })
        else:
            # 即使返回非0，也可能是因为进程本来就没运行
            if '调度器未运行' in result.stdout or '调度器已停止' in result.stdout:
                return jsonify({
                    'success': True,
                    'message': '定时任务已停止',
                    'output': result.stdout
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'停止失败: {result.stderr}',
                    'output': result.stdout
                }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '停止操作超时，可能需要手动检查进程状态'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/run-once', methods=['POST'])
def api_run_once():
    """立即执行一次任务"""
    try:
        # 生成时间戳目录
        import os
        import json
        from datetime import datetime
        import subprocess
        
        timestamp = get_localized_timestamp()
        output_dir = f'/app/compose/{timestamp}'
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置环境变量并执行d2c.py
        env = os.environ.copy()
        env['CRON'] = 'once'
        env['OUTPUT_DIR'] = output_dir
        
        result = subprocess.run(
            ['python3', '/app/d2c.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            cwd='/app'
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'任务执行成功，输出目录: {output_dir}',
                'output': result.stdout,
                'output_dir': output_dir
            })
        else:
            return jsonify({
                'success': False,
                'error': f'执行失败: {result.stderr}'
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '执行超时'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/status', methods=['GET'])
def api_get_scheduler_status():
    """获取任务状态"""
    try:
        # 使用scheduler_manager.sh获取状态
        result = subprocess.run(
            ['/app/scheduler_manager.sh', 'status'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # 解析状态输出 - 检查中文和英文的运行状态
        output_lower = result.stdout.lower() if result.returncode == 0 else ''
        is_running = False
        
        if result.returncode == 0:
            # 检查Python调度器状态
            python_running = 'Python调度器: 运行中' in result.stdout or 'python调度器正在运行' in result.stdout
            # 检查系统CRON状态 - 注意大小写
            system_cron_running = '系统CRON: 运行中' in result.stdout or '系统cron正在运行' in result.stdout
            # 只要有一个调度器在运行就认为任务状态为运行中
            is_running = python_running or system_cron_running or 'running' in output_lower or '正在运行' in result.stdout
            
            # 确定调度器类型
            scheduler_type = 'unknown'
            if python_running and system_cron_running:
                scheduler_type = 'both'  # 不应该发生，但以防万一
            elif python_running:
                scheduler_type = 'python'
            elif system_cron_running:
                scheduler_type = 'system_cron'
        else:
            scheduler_type = 'none'
        
        # 尝试获取最后执行时间（从日志文件或其他方式）
        last_run = None
        try:
            # 检查最新的compose文件夹时间戳
            compose_dir = '/app/compose'
            if os.path.exists(compose_dir):
                folders = [f for f in os.listdir(compose_dir) if os.path.isdir(os.path.join(compose_dir, f))]
                if folders:
                    # 按文件夹名称排序（时间戳格式）
                    folders.sort(reverse=True)
                    latest_folder = folders[0]
                    # 解析时间戳格式：2025_01_03_16_42
                    try:
                        time_parts = latest_folder.split('_')
                        if len(time_parts) == 5:
                            year, month, day, hour, minute = map(int, time_parts)
                            last_run = datetime(year, month, day, hour, minute).isoformat()
                    except:
                        pass
        except:
            pass
        
        return jsonify({
            'success': True,
            'status': {
                'running': is_running,
                'scheduler_type': scheduler_type,
                'last_run': last_run,
                'output': result.stdout
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/logs', methods=['GET'])
def api_get_scheduler_logs():
    """获取任务日志"""
    try:
        logs = []
        
        # 尝试从多个来源获取日志
        log_sources = [
            '/app/logs/cron.log'
        ]
        
        for log_file in log_sources:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()  # 读取全部行
                        # 获取文件修改时间作为基准时间戳
                        file_mtime = os.path.getmtime(log_file)
                        base_timestamp = datetime.fromtimestamp(file_mtime)
                        
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if line:
                                # 简单的日志级别检测
                                level = 'info'
                                if 'error' in line.lower() or 'failed' in line.lower():
                                    level = 'error'
                                elif 'warning' in line.lower() or 'warn' in line.lower():
                                    level = 'warning'
                                elif 'success' in line.lower() or 'completed' in line.lower():
                                    level = 'success'
                                
                                # 使用文件修改时间加上行号偏移作为时间戳
                                log_timestamp = base_timestamp + timedelta(seconds=i)
                                
                                logs.append({
                                    'timestamp': log_timestamp.isoformat(),
                                    'level': level,
                                    'message': line,
                                    'source': os.path.basename(log_file)
                                })
                except Exception as e:
                    logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'error',
                        'message': f'读取日志文件 {log_file} 失败: {str(e)}',
                        'source': 'system'
                    })
        
        # 如果没有找到日志文件，添加一些示例日志
        if not logs:
            logs = [
                {
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': '暂无日志记录，请执行任务后查看',
                    'source': 'system'
                }
            ]
        
        # 按时间戳排序所有日志
        logs.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'success': True,
            'logs': logs  # 返回全部日志
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/clear-logs', methods=['POST'])
def api_clear_scheduler_logs():
    """清空任务日志"""
    try:
        log_files = [
            '/app/logs/cron.log'
        ]
        
        cleared_files = []
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'w') as f:
                        f.write('')  # 清空文件内容
                    cleared_files.append(log_file)
                except Exception as e:
                    print(f'清空日志文件 {log_file} 失败: {e}')
        
        return jsonify({
            'success': True,
            'message': f'已清空 {len(cleared_files)} 个日志文件',
            'cleared_files': cleared_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # 确保配置文件存在

    ensure_config_file()
    
    # 确保compose文件存在
    ensure_compose_files_exist()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
