#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRON表达式工具模块
提供CRON表达式的验证、转换和计算功能
"""

import re
import sys
import json
import argparse
from datetime import datetime, timedelta
from croniter import croniter


class CronUtils:
    """CRON表达式工具类"""
    
    def __init__(self):
        self.debug = False
    
    def set_debug(self, debug=True):
        """设置调试模式"""
        self.debug = debug
    
    def log_debug(self, message):
        """输出调试信息"""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)
    
    def normalize_cron_expression(self, cron_expr):
        """
        标准化CRON表达式，处理全角字符和特殊字符
        
        Args:
            cron_expr (str): 原始CRON表达式
            
        Returns:
            str: 标准化后的CRON表达式
        """
        if not cron_expr:
            return cron_expr
        
        # 全角字符到半角字符的映射
        char_map = {
            '　': ' ',  # 全角空格转半角空格
            '？': '?',  # 全角问号转半角问号
            '＊': '*',  # 全角星号转半角星号
            '，': ',',  # 全角逗号转半角逗号
            '－': '-',  # 全角减号转半角减号
            '／': '/',  # 全角斜杠转半角斜杠
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
        }
        
        # 执行字符替换
        normalized = cron_expr
        for full_char, half_char in char_map.items():
            normalized = normalized.replace(full_char, half_char)
        
        # 处理多个连续空格，替换为单个空格
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        
        self.log_debug(f"标准化CRON表达式: '{cron_expr}' -> '{normalized}'")
        return normalized
    
    def validate_cron_expression(self, cron_expr):
        """
        验证CRON表达式格式
        支持5位格式 (分 时 日 月 周) 和6位格式 (秒 分 时 日 月 周)
        
        Args:
            cron_expr (str): CRON表达式
            
        Returns:
            tuple: (is_valid, field_count, error_message)
        """
        if not cron_expr or not isinstance(cron_expr, str):
            return False, 0, "CRON表达式不能为空"
        
        # 去除首尾空格并标准化字符
        cron_expr = self.normalize_cron_expression(cron_expr.strip())
        
        # 分割字段
        fields = cron_expr.split()
        field_count = len(fields)
        
        self.log_debug(f"验证CRON表达式: '{cron_expr}'")
        self.log_debug(f"检测到 {field_count} 个字段")
        
        # 检查字段数量
        if field_count not in [5, 6]:
            return False, field_count, f"字段数量不正确 (期望5或6个，实际{field_count}个)"
        
        # 验证每个字段的字符
        valid_chars_pattern = r'^[0-9*/,?-]+$'
        
        for i, field in enumerate(fields):
            self.log_debug(f"检查字段{i+1}: '{field}'")
            
            if not re.match(valid_chars_pattern, field):
                return False, field_count, f"字段{i+1}包含无效字符: '{field}'"
        
        self.log_debug("CRON表达式验证通过")
        return True, field_count, "验证通过"
    
    def is_6_field_cron(self, cron_expr):
        """
        检查是否为6位CRON表达式
        
        Args:
            cron_expr (str): CRON表达式
            
        Returns:
            bool: 是否为6位格式
        """
        if not cron_expr or cron_expr.strip() == 'once':
            return False
        
        # 标准化表达式
        normalized = self.normalize_cron_expression(cron_expr.strip())
        fields = normalized.split()
        return len(fields) == 6
    
    def convert_6_to_5_field(self, cron_expr):
        """
        将6位CRON表达式转换为5位格式
        仅用于系统CRON兼容性，不改变原始6位表达式的语义
        
        Args:
            cron_expr (str): 6位CRON表达式
            
        Returns:
            tuple: (converted_cron, conversion_strategy)
        """
        if not self.is_6_field_cron(cron_expr):
            return cron_expr, "无需转换"
        
        # 标准化表达式
        normalized = self.normalize_cron_expression(cron_expr.strip())
        fields = normalized.split()
        seconds, minutes, hours, days, months, weekdays = fields
        
        self.log_debug(f"转换6位CRON: {cron_expr}")
        
        # 仅在转换为5位时处理'?'字符，用于系统CRON兼容性
        # 原始6位表达式保持不变，由Python调度器处理
        converted_minutes = minutes.replace('?', '*')
        converted_hours = hours.replace('?', '*')
        converted_days = days.replace('?', '*')
        converted_months = months.replace('?', '*')
        converted_weekdays = weekdays.replace('?', '*')
        
        # 特殊处理：如果是每秒执行且时间范围有限，转换为每分钟执行
        if (re.match(r'^[0-9]+/[0-9]+$', seconds) and 
            re.match(r'^[0-9]+-[0-9]+$', minutes)):
            
            # 将分钟范围转换为每分钟执行
            converted_cron = f"*/1 {converted_hours} {converted_days} {converted_months} {converted_weekdays}"
            strategy = "秒级重复执行模式，转换为分钟级执行以保持调度意图"
            
        else:
            # 标准转换：去掉秒字段
            converted_cron = f"{converted_minutes} {converted_hours} {converted_days} {converted_months} {converted_weekdays}"
            strategy = "标准转换: 去掉秒字段，保持其他时间设置"
        
        self.log_debug(f"转换结果: {converted_cron}")
        self.log_debug(f"转换策略: {strategy}")
        
        return converted_cron, strategy
    
    def calculate_next_run_time(self, cron_expr, base_time=None):
        """
        计算下次执行时间
        对于6位CRON表达式，建议使用Python调度器进行精确计算
        
        Args:
            cron_expr (str): CRON表达式
            base_time (datetime, optional): 基准时间，默认为当前时间
            
        Returns:
            tuple: (next_time, formatted_time, error_message)
        """
        if base_time is None:
            base_time = datetime.now()
        
        try:
            # 标准化表达式
            normalized = self.normalize_cron_expression(cron_expr.strip())
            fields = normalized.split()
            
            # 检查是否为6位格式
            if len(fields) == 6:
                self.log_debug("检测到6位CRON格式")
                
                # 对于6位CRON，建议使用Python调度器
                # 这里提供一个简化的计算，实际应该由scheduler.py处理
                try:
                    # 尝试使用croniter的6位支持
                    from croniter import croniter
                    
                    # 某些版本的croniter可能不完全支持6位格式
                    # 我们先尝试直接使用，如果失败则使用5位部分
                    try:
                        cron = croniter(normalized, base_time)
                        next_time = cron.get_next(datetime)
                        self.log_debug("成功使用6位CRON格式计算")
                    except:
                        # 如果6位格式失败，使用5位部分进行近似计算
                        five_field_cron = ' '.join(fields[1:]).replace('?', '*')
                        cron = croniter(five_field_cron, base_time)
                        next_time = cron.get_next(datetime)
                        self.log_debug(f"使用5位近似计算: {five_field_cron}")
                        
                except Exception as e:
                    self.log_debug(f"6位CRON计算失败: {e}")
                    return None, None, f"6位CRON表达式计算失败，建议使用Python调度器: {str(e)}"
            else:
                self.log_debug("使用5位CRON格式计算")
                # 标准5位格式
                cron = croniter(normalized, base_time)
                next_time = cron.get_next(datetime)
            
            formatted_time = next_time.strftime('%Y-%m-%d %H:%M:%S')
            return next_time, formatted_time, None
            
        except Exception as e:
            error_msg = f"计算下次执行时间失败: {str(e)}"
            self.log_debug(error_msg)
            return None, None, error_msg
    
    def get_cron_from_config(self, config_file):
        """
        从配置文件读取CRON表达式
        
        Args:
            config_file (str): 配置文件路径
            
        Returns:
            str: CRON表达式，如果读取失败返回默认值
        """
        default_cron = "*/5 * * * *"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 尝试多个可能的键名
                cron_expr = config.get('cron', config.get('CRON', default_cron))
                
                # 处理可能的引号
                if isinstance(cron_expr, str):
                    cron_expr = cron_expr.strip('"\'')
                
                return cron_expr
                
        except Exception as e:
            self.log_debug(f"读取配置文件失败: {e}")
            return default_cron
    
    def analyze_cron_expression(self, cron_expr):
        """
        分析CRON表达式，返回详细信息
        
        Args:
            cron_expr (str): CRON表达式
            
        Returns:
            dict: 分析结果
        """
        result = {
            'original': cron_expr,
            'is_valid': False,
            'field_count': 0,
            'is_6_field': False,
            'converted_5_field': None,
            'conversion_strategy': None,
            'next_run_time': None,
            'formatted_next_run': None,
            'error_message': None
        }
        
        # 验证表达式
        is_valid, field_count, error_msg = self.validate_cron_expression(cron_expr)
        result['is_valid'] = is_valid
        result['field_count'] = field_count
        
        if not is_valid:
            result['error_message'] = error_msg
            return result
        
        # 检查是否为6位格式
        result['is_6_field'] = self.is_6_field_cron(cron_expr)
        
        # 如果是6位格式，进行转换
        if result['is_6_field']:
            converted, strategy = self.convert_6_to_5_field(cron_expr)
            result['converted_5_field'] = converted
            result['conversion_strategy'] = strategy
        
        # 计算下次执行时间
        next_time, formatted_time, calc_error = self.calculate_next_run_time(cron_expr)
        if calc_error:
            result['error_message'] = calc_error
        else:
            result['next_run_time'] = next_time
            result['formatted_next_run'] = formatted_time
        
        return result


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='CRON表达式工具')
    parser.add_argument('--cron', '-c', help='CRON表达式')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--validate', action='store_true', help='验证CRON表达式')
    parser.add_argument('--convert', action='store_true', help='转换6位CRON为5位')
    parser.add_argument('--next-time', action='store_true', help='计算下次执行时间')
    parser.add_argument('--analyze', action='store_true', help='分析CRON表达式')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    
    args = parser.parse_args()
    
    utils = CronUtils()
    if args.debug:
        utils.set_debug(True)
    
    # 获取CRON表达式
    cron_expr = args.cron
    if not cron_expr and args.config:
        cron_expr = utils.get_cron_from_config(args.config)
    
    if not cron_expr:
        print("错误: 请提供CRON表达式或配置文件", file=sys.stderr)
        sys.exit(1)
    
    # 执行相应操作
    if args.analyze:
        result = utils.analyze_cron_expression(cron_expr)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"CRON表达式: {result['original']}")
            print(f"有效性: {'有效' if result['is_valid'] else '无效'}")
            print(f"字段数量: {result['field_count']}")
            print(f"6位格式: {'是' if result['is_6_field'] else '否'}")
            if result['converted_5_field']:
                print(f"转换为5位: {result['converted_5_field']}")
                print(f"转换策略: {result['conversion_strategy']}")
            if result['formatted_next_run']:
                print(f"下次执行: {result['formatted_next_run']}")
            if result['error_message']:
                print(f"错误: {result['error_message']}")
    
    elif args.validate:
        is_valid, field_count, error_msg = utils.validate_cron_expression(cron_expr)
        if args.json:
            result = {'valid': is_valid, 'field_count': field_count, 'message': error_msg}
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"验证结果: {'通过' if is_valid else '失败'}")
            print(f"字段数量: {field_count}")
            print(f"消息: {error_msg}")
        sys.exit(0 if is_valid else 1)
    
    elif args.convert:
        if utils.is_6_field_cron(cron_expr):
            converted, strategy = utils.convert_6_to_5_field(cron_expr)
            if args.json:
                result = {'original': cron_expr, 'converted': converted, 'strategy': strategy}
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"原始: {cron_expr}")
                print(f"转换: {converted}")
                print(f"策略: {strategy}")
        else:
            if args.json:
                result = {'original': cron_expr, 'converted': cron_expr, 'strategy': '无需转换'}
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"无需转换: {cron_expr}")
    
    elif args.next_time:
        next_time, formatted_time, error = utils.calculate_next_run_time(cron_expr)
        if error:
            if args.json:
                result = {'error': error}
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"错误: {error}")
            sys.exit(1)
        else:
            if args.json:
                result = {'next_time': formatted_time, 'timestamp': next_time.timestamp()}
                print(json.dumps(result, ensure_ascii=False, default=str))
            else:
                print(formatted_time)
    
    else:
        # 默认行为：分析表达式
        result = utils.analyze_cron_expression(cron_expr)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"CRON表达式分析: {cron_expr}")
            print(f"格式: {result['field_count']}位 ({'6位秒级' if result['is_6_field'] else '5位标准'}格式)")
            if result['is_6_field'] and result['converted_5_field']:
                print(f"建议: 使用Python调度器以支持完整的6位格式")
                print(f"系统cron兼容格式: {result['converted_5_field']}")
            if result['formatted_next_run']:
                print(f"下次执行时间: {result['formatted_next_run']}")


if __name__ == '__main__':
    main()