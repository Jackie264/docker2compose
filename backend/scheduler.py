#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D2C 精确调度器
支持6位CRON格式的秒级精确调度
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from croniter import croniter
import pytz
import signal
import os

class D2CScheduler:
    def __init__(self, config_file='/app/config/config.json'):
        self.config_file = config_file
        self.running = True
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """设置信号处理器，支持优雅退出"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """信号处理函数"""
        print(f"\n收到信号 {signum}，正在优雅退出...")
        self.running = False
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 支持大小写不敏感的键名
                cron_expr = config.get('CRON') or config.get('cron', '*/5 * * * *')
                return cron_expr
        except Exception as e:
            print(f"加载配置失败: {e}")
            return '*/5 * * * *'
            
    def load_tz_from_config(self):
        """从配置文件加载时区设置"""
        default_tz = 'Asia/Shanghai'
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('TZ', default_tz)
        except Exception as e:
            print(f"加载时区配置失败: {e}，使用默认时区: {default_tz}")
            return default_tz
            
    def parse_cron_expression(self, cron_expr):
        """解析CRON表达式，支持5位和6位格式"""
        fields = cron_expr.strip().split()
        
        if len(fields) == 5:
            # 5位格式：分 时 日 月 周
            return cron_expr, False
        elif len(fields) == 6:
            # 6位格式：秒 分 时 日 月 周
            return cron_expr, True
        else:
            raise ValueError(f"无效的CRON表达式: {cron_expr}")
            
    def calculate_next_run(self, cron_expr, is_6_field=False):
        """计算下次执行时间"""
        now = datetime.now()
        
        if is_6_field:
            # 6位格式需要特殊处理
            try:
                # 尝试使用croniter处理6位格式
                cron = croniter(cron_expr, now)
                return cron.get_next(datetime)
            except:
                # 如果失败，转换为5位格式
                fields = cron_expr.split()
                five_field_cron = ' '.join(fields[1:])  # 去掉秒字段
                # 将?替换为*，因为标准cron不支持?
                five_field_cron = five_field_cron.replace('?', '*')
                cron = croniter(five_field_cron, now)
                next_time = cron.get_next(datetime)
                
                # 如果原始表达式有秒字段，尝试调整
                seconds_field = fields[0]
                if seconds_field.isdigit():
                    # 固定秒数
                    next_time = next_time.replace(second=int(seconds_field))
                elif '/' in seconds_field:
                    # 间隔秒数，计算下一个符合条件的秒数
                    if '/' in seconds_field:
                        start_sec, interval = seconds_field.split('/')
                        start_sec = int(start_sec) if start_sec else 0
                        interval = int(interval)
                        current_sec = now.second
                        
                        # 计算下一个符合间隔的秒数
                        next_sec = start_sec
                        while next_sec <= current_sec:
                            next_sec += interval
                        
                        if next_sec >= 60:
                            # 如果超过60秒，需要到下一分钟
                            next_time = next_time + timedelta(minutes=1)
                            next_sec = start_sec
                        
                        next_time = next_time.replace(second=next_sec)
                    
                return next_time
        else:
            # 5位格式
            cron = croniter(cron_expr, now)
            return cron.get_next(datetime)
            
    def run_d2c_task(self):
        """执行D2C任务"""
        try:
            # 生成时间戳目录，使用config.json中的时区配置
            import subprocess
            tz = self.load_tz_from_config()
            env = os.environ.copy()
            env['TZ'] = tz
            result = subprocess.run(['date', '+%Y_%m_%d_%H_%M'], env=env, capture_output=True, text=True)
            timestamp = result.stdout.strip()
            output_dir = f"/app/compose/{timestamp}"
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行D2C任务")
            print(f"输出目录: {output_dir}")
            
            # 设置环境变量
            env = os.environ.copy()
            env['OUTPUT_DIR'] = output_dir
            
            result = subprocess.run(
                [sys.executable, '/app/d2c.py'],
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                env=env
            )
            
            if result.returncode == 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] D2C任务执行成功")
                if result.stdout:
                    print(f"输出: {result.stdout.strip()}")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] D2C任务执行失败")
                if result.stderr:
                    print(f"错误: {result.stderr.strip()}")
                    
        except subprocess.TimeoutExpired:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] D2C任务执行超时")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] D2C任务执行异常: {e}")
            
    def run(self):
        """主运行循环"""
        print("D2C精确调度器启动")
        print(f"配置文件: {self.config_file}")
        
        while self.running:
            try:
                # 重新加载配置（支持动态更新）
                cron_expr = self.load_config()
                parsed_cron, is_6_field = self.parse_cron_expression(cron_expr)
                
                print(f"\n当前CRON表达式: {cron_expr}")
                print(f"格式: {'6位(秒级)' if is_6_field else '5位(分钟级)'}")
                
                # 计算下次执行时间
                next_run = self.calculate_next_run(parsed_cron, is_6_field)
                print(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待到执行时间
                while self.running:
                    now = datetime.now()
                    if now >= next_run:
                        break
                        
                    # 计算等待时间
                    wait_seconds = (next_run - now).total_seconds()
                    
                    # 如果等待时间超过60秒，每60秒检查一次配置更新
                    if wait_seconds > 60:
                        time.sleep(60)
                        # 检查配置是否更新
                        new_cron = self.load_config()
                        if new_cron != cron_expr:
                            print("检测到配置更新，重新计算执行时间")
                            break
                    else:
                        # 精确等待
                        time.sleep(min(wait_seconds, 1))
                        
                # 执行任务
                if self.running and datetime.now() >= next_run:
                    self.run_d2c_task()
                    
            except KeyboardInterrupt:
                print("\n收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"调度器运行异常: {e}")
                print("等待30秒后重试...")
                time.sleep(30)
                
        print("D2C精确调度器已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='D2C精确调度器')
    parser.add_argument('--config', '-c', default='/app/config/config.json',
                        help='配置文件路径 (默认: /app/config/config.json)')
    parser.add_argument('--test', '-t', action='store_true',
                       help='测试模式：显示下次执行时间后退出')
    
    args = parser.parse_args()
    
    scheduler = D2CScheduler(args.config)
    
    if args.test:
        # 测试模式
        cron_expr = scheduler.load_config()
        parsed_cron, is_6_field = scheduler.parse_cron_expression(cron_expr)
        next_run = scheduler.calculate_next_run(parsed_cron, is_6_field)
        
        print(f"CRON表达式: {cron_expr}")
        print(f"格式: {'6位(秒级)' if is_6_field else '5位(分钟级)'}")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"等待时间: {(next_run - datetime.now()).total_seconds():.1f}秒")
    else:
        # 正常运行
        scheduler.run()

if __name__ == '__main__':
    main()