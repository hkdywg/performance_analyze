#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图形显示应用程序性能分析 - HTML报告生成器

此脚本读取远程采集的数据，生成包含性能分析和优化建议的HTML报告。
"""

import os
import json
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 项目根目录
SCRIPT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = SCRIPT_DIR / "report"
TEMPLATE_DIR = SCRIPT_DIR / "templates"

# HTML模板
HTML_HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 性能分析报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .header .meta {{
            margin-top: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        
        .header .meta-item {{
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 5px;
        }}
        
        /* 导航栏 */
        .nav {{
            background: white;
            padding: 15px 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 10px;
            z-index: 100;
        }}
        
        .nav ul {{
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .nav a {{
            text-decoration: none;
            color: #667eea;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 5px;
            transition: all 0.3s;
        }}
        
        .nav a:hover {{
            background: #667eea;
            color: white;
        }}
        
        /* 内容卡片 */
        .card {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .card h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        .card h3 {{
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.3em;
        }}
        
        /* 状态指示器 */
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        .status.normal {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status.warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status.error {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        /* 表格样式 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        /* 代码块 */
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }}
        
        /* 问题列表 */
        .issue {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}
        
        .issue.error {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}
        
        .issue.success {{
            background: #d4edda;
            border-left-color: #28a745;
        }}
        
        .issue h4 {{
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        /* 优化建议 */
        .suggestion {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}

        .suggestion .code {{
            background: #d4e5f7;
            padding: 10px 15px;
            border-radius: 5px;
            font-family: monospace;
            margin: 10px 0;
            overflow-x: auto;
        }}

        /* 热点函数调用栈样式 */
        .stack-details {{
            margin: 15px 0;
        }}

        /* 热点函数表格样式 */
        .hot-functions-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }}

        .hot-functions-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        .hot-functions-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}

        .hot-functions-table tr:hover {{
            background: #f8f9fa;
        }}

        .hot-functions-table tr.high-usage {{
            background: #fff3cd;
        }}

        .hot-functions-table tr.high-usage:hover {{
            background: #ffeeba;
        }}

        .category-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}

        .category-tag.图形 {{
            background: #e3f2fd;
            color: #1565c0;
        }}

        .category-tag.通用 {{
            background: #f3e5f5;
            color: #7b1fa2;
        }}

        .stack-link {{
            color: #667eea;
            text-decoration: none;
            font-size: 12px;
        }}

        .stack-link:hover {{
            text-decoration: underline;
        }}

        /* SVG火焰图容器 */
        .svg-flamegraph-container {{
            margin: 20px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            border: 1px solid #eee;
        }}

        .svg-wrapper {{
            overflow-x: auto;
            margin: 10px 0;
        }}

        .svg-wrapper svg {{
            max-width: 100%;
            height: auto;
        }}

        .download-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
        }}

        .download-link:hover {{
            background: #5568d3;
        }}

        .back-link {{
            font-size: 12px;
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            margin-left: 15px;
        }}

        .back-link:hover {{
            color: white;
            text-decoration: underline;
        }}

        .stack-function {{
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}

        .stack-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
        }}

        .stack-header:hover {{
            background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
        }}

        .stack-name {{
            font-weight: bold;
            max-width: 60%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .stack-name code {{
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 13px;
        }}

        .stack-pct {{
            background: rgba(255,255,255,0.3);
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 13px;
        }}

        .stack-toggle {{
            font-size: 12px;
            margin-left: 10px;
        }}

        .stack-content {{
            background: #f8f9fa;
            border-top: 1px solid #ddd;
            padding: 15px;
        }}

        .stack-content pre {{
            margin: 0;
            font-family: 'Courier New', Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        .stack-content pre .func-entry {{
            color: #e83e8c;
            font-weight: bold;
        }}

        /* 网格布局 */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-box {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-box .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-box .label {{
            color: #666;
            margin-top: 5px;
        }}
        
        /* 图表容器 */
        .chart-container {{
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .chart-container h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        
        .chart-container canvas {{
            max-height: 300px;
        }}
        
        .no-data {{
            text-align: center;
            color: #999;
            padding: 40px;
            font-style: italic;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .header .meta {{
                flex-direction: column;
                gap: 10px;
            }}
            .nav ul {{
                flex-direction: column;
            }}
        }}
        
        /* 目录树 */
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .toc ul {{
            list-style: none;
            padding-left: 20px;
        }}
        
        .toc li {{
            padding: 5px 0;
        }}
        
        .toc a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        .toc a:hover {{
            text-decoration: underline;
        }}
        
        /* 进度条 */
        .progress {{
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-bar {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s;
        }}
        
        .progress-bar.low {{ background: #28a745; }}
        .progress-bar.medium {{ background: #ffc107; }}
        .progress-bar.high {{ background: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
"""

HTML_FOOTER = """
    </div>
    <div class="footer">
        <p>报告生成时间: {timestamp}</p>
        <p>图形显示应用程序性能分析系统</p>
    </div>
</body>
</html>
"""


class PerformanceReportGenerator:
    """性能报告生成器类"""
    
    def __init__(self, data_dir: str, output_path: str = None):
        self.data_dir = Path(data_dir)
        self.output_path = output_path or str(self.data_dir / "report.html")
        self.data = {}
        self.issues = []
        self.suggestions = []
        
    def load_data(self) -> bool:
        """加载数据文件"""
        print(f"从 {self.data_dir} 加载数据...")

        # 查找JSON汇总文件
        json_files = list(self.data_dir.glob("remote_data_*.json"))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            # 重新加载所有数据文件（优先使用最新文件内容覆盖JSON中的旧数据）
            self._load_all_data_files()
        else:
            # 加载所有txt文件
            self._load_text_files()

        return bool(self.data)

    def _load_all_data_files(self):
        """重新加载所有数据文件以获取最新内容"""
        # 加载所有 txt 文件（perf_report.txt, stack_counts.txt 等）
        for txt_file in self.data_dir.glob("*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][txt_file.name] = f.read()
            except Exception as e:
                print(f"读取 {txt_file.name} 失败: {e}")

        # 加载 CSV 文件
        self._load_csv_files()

        # 加载 SVG 文件
        self._load_svg_files()

    def _load_csv_files(self):
        """加载 CSV 文件"""
        for csv_file in self.data_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][csv_file.name] = f.read()
            except Exception as e:
                print(f"读取 {csv_file.name} 失败: {e}")

    def _load_svg_files(self):
        """加载 SVG 文件"""
        for svg_file in self.data_dir.glob("*.svg"):
            try:
                with open(svg_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][svg_file.name] = f.read()
            except Exception as e:
                print(f"读取 {svg_file.name} 失败: {e}")

    def _load_text_files(self):
        """从文本文件加载数据"""
        self.data = {"files": {}}

        # 加载所有支持的文件类型
        file_patterns = ["*.txt", "*.csv", "*.svg", "*.json"]
        for pattern in file_patterns:
            for data_file in self.data_dir.glob(pattern):
                try:
                    with open(data_file, 'r', encoding='utf-8', errors='ignore') as f:
                        self.data["files"][data_file.name] = f.read()
                except Exception as e:
                    print(f"读取 {data_file.name} 失败: {e}")
    
    def analyze_data(self):
        """分析数据并识别问题"""
        print("分析性能数据...")

        self._check_memory()
        self._check_cpu()
        self._check_wayland()
        self._check_app_process()

        # 新增：火焰图数据分析
        self._check_flamegraph_data()

        # 新增：图形学特定分析
        self._check_graphics_optimization()

        print(f"发现 {len(self.issues)} 个问题, {len(self.suggestions)} 条建议")
    
    def _extract_value(self, text: str, pattern: str) -> Optional[str]:
        """从文本中提取值"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None
    
    def _extract数值(self, text: str, pattern: str) -> Optional[float]:
        """提取数值"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                return None
        return None

    #============================================================================
    # 火焰图数据分析
    #============================================================================
    def _check_flamegraph_data(self):
        """分析火焰图数据，识别CPU热点函数"""
        print("  分析火焰图数据...")

        perf_report = self.data.get("files", {}).get("perf_report.txt", "")
        stack_counts = self.data.get("files", {}).get("stack_counts.txt", "")
        function_counts = self.data.get("files", {}).get("function_counts.txt", "")
        syscall_counts = self.data.get("files", {}).get("syscall_counts.txt", "")
        hot_functions_stacks = self.data.get("files", {}).get("hot_functions_stacks.txt", "")

        # 分析perf报告
        if perf_report and perf_report != "N/A" and "采集失败" not in perf_report:
            hot_functions = self._extract_hot_functions(perf_report)
            if hot_functions:
                self._analyze_hot_functions(hot_functions)

        # 从新的结构化文件解析热点函数和调用栈
        if hot_functions_stacks and hot_functions_stacks != "N/A":
            parsed = self._parse_hot_functions_stacks(hot_functions_stacks)
            if parsed:
                # 更新热点函数列表（如果解析成功）
                if parsed.get("status") == "success":
                    print(f"  解析到 {len(parsed.get('functions', []))} 个热点函数")
                elif parsed.get("status") == "no_callchain":
                    print("  perf.data无调用链数据")

        # 分析函数调用频率
        if function_counts and function_counts != "N/A":
            self._analyze_graphics_functions(function_counts)

        # 分析系统调用
        if syscall_counts and syscall_counts != "N/A" and "N/A" not in syscall_counts:
            self._analyze_syscalls(syscall_counts)

    def _parse_hot_functions_stacks(self, content: str) -> Dict:
        """解析热点函数调用栈文件"""
        result = {
            "status": "unknown",
            "functions": [],
            "no_callchain_message": ""
        }
        
        lines = content.split('\n')
        if not lines:
            return result
        
        # 检查状态行
        for line in lines:
            if line.startswith("# 状态:"):
                status = line.split("状态:")[1].strip()
                result["status"] = status
                if status == "无调用链数据":
                    result["no_callchain_message"] = self._extract_no_callchain_message(content)
                return result
        
        # 解析函数和调用栈
        current_func = None
        current_stack = []
        
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            
            if line.startswith("FUNC:"):
                # 保存前一个函数
                if current_func:
                    result["functions"].append({
                        "name": current_func["name"],
                        "pct": current_func["pct"],
                        "stack": current_stack[:]
                    })
                
                # 解析新函数
                # 格式: "FUNC: 0xaddr PCT: xx.xx%"
                match = re.match(r'FUNC:\s*(\S+)\s+PCT:\s*([0-9.]+)%', line)
                if match:
                    current_func = {
                        "name": match.group(1),
                        "pct": float(match.group(2))
                    }
                    current_stack = []
            
            elif line.startswith("  STACK["):
                # 解析调用栈
                # 格式: "  STACK[2]: module:addr"
                match = re.match(r'\s+STACK\[(\d+)\]:\s*(\S+)', line)
                if match:
                    depth = int(match.group(1))
                    frame = match.group(2)
                    # 只保留新深度的调用
                    if depth <= len(current_stack) + 1:
                        current_stack.append(frame)
        
        # 保存最后一个函数
        if current_func:
            result["functions"].append({
                "name": current_func["name"],
                "pct": current_func["pct"],
                "stack": current_stack[:]
            })
        
        return result

    def _extract_no_callchain_message(self, content: str): 
        """提取无调用链时的提示信息"""
        lines = content.split('\n')
        messages = []
        for line in lines:
            if line.startswith("#") and "解决方案" not in line and "perf record" not in line:
                msg = line.lstrip("# ").strip()
                if msg:
                    messages.append(msg)
        return "\n".join(messages)

    def _extract_hot_functions_from_report(self, report_text: str) -> Tuple[List, Dict, bool]:
        """从 perf report 文本中提取热点函数和调用栈
        返回: (hot_functions列表, 函数数据字典, 是否有调用链)
        """
        hot_functions = []
        hot_functions_data = {}
        has_callchain = False
        seen = set()

        lines = report_text.split('\n')
        current_func = None
        current_pct = 0.0
        current_stack = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 检测新的热点函数行（perf report 标准格式）
            # 例如: "    89.29%     0.00%  kanzi    kanzi                [.] 0x0000000000435bb0"
            match = re.match(r'\s*(\d+\.?\d*)%\s+(\d+\.?\d*)%\s+\S+\s+(\S+)\s+\[.\]\s+(0x\S+)', line)
            if match:
                # 保存前一个函数
                if current_func:
                    hot_functions.append((current_func, current_pct))
                    hot_functions_data[current_func] = {"pct": current_pct, "stack": current_stack[:]}

                current_pct = float(match.group(1))  # Children%
                module = match.group(2).strip()
                addr = match.group(3).strip()

                # 提取函数名 - Perf report 的第5列是 Symbol（函数名）
                # 例如: "    89.29%     0.00%  kanzi    kanzi                [.] 0x0000000000435bb0"
                # 第1个空格后: 89.29% (Children%)
                # 第2个空格后: 0.00% (Self%)
                # 第3个空格后: kanzi (Command)
                # 第4个空格后: kanzi (Shared Object/Module)
                # 第5个空格后: [.] (类型)
                # 第6个空格后: 0x0000000000435bb0 (Symbol/地址)
                # 真正的函数名在第5列（Shared Object之后）
                func_name = addr  # 使用地址作为函数名标识

                # 对于 kanzi 应用，创建更友好的函数名标识
                if module == 'kanzi' and addr.startswith('0x'):
                    # 使用简短地址格式，便于阅读
                    short_addr = addr[2:10] if len(addr) > 10 else addr[2:]
                    current_func = f"app_0x{short_addr}"
                else:
                    current_func = func_name

                current_stack = []
                has_callchain = False
                continue

            # 检测带调用栈的 perf report 格式（树形结构）
            # 例如: "            |"
            #       "            ---0x435bb0"
            if '|' in line or '---' in line:
                has_callchain = True
                # 提取地址
                addr_match = re.search(r'0x([0-9a-f]+)', line)
                if addr_match:
                    addr = addr_match.group(1)
                    if addr.startswith('ffff'):
                        current_stack.append(f"kernel:0x{addr[-8:]}")
                    else:
                        current_stack.append(f"app:0x{addr[-8:]}")

        # 保存最后一个函数
        if current_func:
            hot_functions.append((current_func, current_pct))
            hot_functions_data[current_func] = {"pct": current_pct, "stack": current_stack[:]}

        return hot_functions, hot_functions_data, has_callchain

    def _extract_hot_functions(self, perf_text: str) -> List[Tuple[str, float]]:
        """从perf报告中提取热点函数"""
        hot_funcs = []
        lines = perf_text.split('\n')
        seen = set()  # 用于去重
        
        for line in lines:
            # 跳过空行和注释行
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # perf report 格式: "[空白][Children%][空白][Self%][空白][Command][空白][Shared Object][空白][Symbol]"
            # 例如: "    89.49%     0.00%  kanzi    kanzi                [.] 0x000000000041c55c"
            # 或: "    29.07%     0.00%  kanzi    [kernel.kallsyms]    [k] 0xffff800010011d98"
            match = re.match(r'\s*(\d+\.?\d*)%\s+(\d+\.?\d*)%\s+\S+\s+(\S+)\s+\[.\]\s+(0x\S+)', line)
            if match:
                children_pct = float(match.group(1))  # Children% - 这个函数及其子函数占总时间的百分比
                self_pct = float(match.group(2))       # Self% - 这个函数本身占用的时间
                module = match.group(3).strip()
                addr = match.group(4).strip()

                # 使用模块名作为函数名标识（因为Symbol是地址）
                func_name = module.strip('[]')

                # 对于 kanzi 应用的地址，创建更友好的函数名标识
                if func_name == 'kanzi' and addr.startswith('0x'):
                    # 使用简短地址格式，便于阅读
                    short_addr = addr[2:10] if len(addr) > 10 else addr[2:]
                    func_name = f"app_0x{short_addr}"

                # CPU占比使用 Children%（这个函数占用的总CPU时间）
                pct = children_pct

                if func_name and func_name != '[unknown]':
                    # 去重
                    key = (func_name, pct)
                    if key not in seen:
                        seen.add(key)
                        hot_funcs.append((func_name, pct))
                    continue
                
            # 处理 kernel 符号格式: [k] 0xaddr
            match2 = re.match(r'\s*(\d+\.?\d*)%\s+(\d+\.?\d*)%\s+\S+\s+(\S+)\s+\[k\]\s+(0x\S+)', line)
            if match2:
                children_pct = float(match2.group(1))  # Children%
                self_pct = float(match2.group(2))       # Self%
                module = match2.group(3).strip()
                addr = match2.group(4).strip()
                func_name = module.strip('[]')

                # CPU占比使用 Children%
                pct = children_pct

                # 保留内核地址前缀，使用简短格式
                if func_name == 'kernel.kallsyms':
                    short_addr = addr[2:10] if len(addr) > 10 else addr[2:]
                    func_name = f"kernel_0x{short_addr}"

                if func_name:
                    key = (func_name, pct)
                    if key not in seen:
                        seen.add(key)
                        hot_funcs.append((func_name, pct))
        
        return hot_funcs[:20]  # 返回前20个热点

    def _analyze_hot_functions(self, hot_funcs: List[Tuple[str, float]]):
        """分析热点函数，生成优化建议"""
        if not hot_funcs:
            return

        # 按类别分析热点函数
        graphics_hot = []
        general_hot = []

        for func, pct in hot_funcs:
            func_lower = func.lower()
            # 图形学相关函数
            if any(kw in func_lower for kw in ['gl', 'egl', 'drm', 'gpu', 'shader', 'texture', 'render', 'blit', 'flip', 'sync', ' Mesa']):
                graphics_hot.append((func, pct))
            else:
                general_hot.append((func, pct))

        # 报告热点函数
        if graphics_hot:
            top_graphics = graphics_hot[:3]
            self.suggestions.append({
                "title": "GPU/图形渲染热点检测",
                "category": "graphics",
                "content": f"检测到以下图形渲染函数占用较高CPU时间: {', '.join([f'{f[0]} ({f[1]:.1f}%)' for f in top_graphics])}",
                "action": self._get_graphics_hot_suggestion(top_graphics)
            })

        if general_hot:
            top_general = general_hot[:5]
            self.issues.append({
                "severity": "warning",
                "title": "通用热点函数",
                "detail": f"检测到高CPU占用的非图形函数: {', '.join([f[0] for f in top_general])}"
            })
            self.suggestions.append({
                "title": "CPU热点优化",
                "category": "general",
                "content": f"热点函数: {', '.join([f'{f[0]} ({f[1]:.1f}%)' for f in top_general])}",
                "action": "检查这些函数是否有优化空间，考虑算法优化、缓存、并行化等方式。"
            })

    def _get_graphics_hot_suggestion(self, hot_funcs: List[Tuple[str, float]]): 
        """根据热点图形函数生成具体建议"""
        suggestions = []
        for func, pct in hot_funcs:
            func_lower = func.lower()
            if 'shader' in func_lower:
                suggestions.append(f"着色器 {func} 占用{pct:.1f}%，考虑简化着色器逻辑或使用更低精度的数据类型。")
            elif 'texture' in func_lower or 'tex' in func_lower:
                suggestions.append(f"纹理操作 {func} 占用{pct:.1f}%，考虑使用GPU压缩纹理格式（ETC/ASTC/BC）。")
            elif 'blit' in func_lower or 'copy' in func_lower:
                suggestions.append(f"数据传输 {func} 占用{pct:.1f}%，考虑使用PBO或DMA传输优化。")
            elif 'sync' in func_lower or 'wait' in func_lower:
                suggestions.append(f"同步操作 {func} 占用{pct:.1f}%，考虑使用Fence或Timeline同步机制。")
            elif 'drm' in func_lower or 'modeset' in func_lower:
                suggestions.append(f"DRM调用 {func} 占用{pct:.1f}%，检查显示模式设置是否有缓存空间。")
            elif 'egl' in func_lower or 'gl' in func_lower:
                suggestions.append(f"OpenGL/EGL调用 {func} 占用{pct:.1f}%，检查是否有冗余的状态切换。")

        if not suggestions:
            return "分析热点函数，建议使用GPU Profiler进行深入分析。"
        return " ".join(suggestions[:3])

    def _analyze_graphics_functions(self, func_text: str):
        """分析BCC/funccount采集的图形函数调用频率"""
        lines = func_text.split('\n')
        high_freq_funcs = []

        for line in lines:
            # 匹配格式: "FUNCTION                              COUNT"
            match = re.match(r'([gl|egl|drm][\w]+)\s+(\d+)', line, re.IGNORECASE)
            if match:
                func = match.group(1)
                count = int(match.group(2))
                if count > 10000:  # 高频调用阈值
                    high_freq_funcs.append((func, count))

        if high_freq_funcs:
            self.suggestions.append({
                "title": "高频图形API调用检测",
                "category": "api_calls",
                "content": f"检测到 {len(high_freq_funcs)} 个高频调用的图形函数，可能存在冗余调用。",
                "action": f"高频函数: {', '.join([f[0] for f in high_freq_funcs[:5]])}。建议检查调用链，合并相同状态的绘制调用。"
            })

    def _analyze_syscalls(self, syscall_text: str):
        """分析系统调用，识别阻塞和频繁调用"""
        lines = syscall_text.split('\n')
        blocking_calls = ['ioctl', 'read', 'write', 'poll', 'select', 'epoll']
        high_count = []

        for line in lines:
            if any(call in line.lower() for call in blocking_calls):
                # 提取调用次数
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        count = int(parts[-1])
                        syscall = parts[0] if len(parts) > 1 else ""
                        if count > 1000:
                            high_count.append((syscall, count))
                    except:
                        pass

        if high_count:
            self.suggestions.append({
                "title": "系统调用优化建议",
                "category": "syscall",
                "content": f"检测到频繁的系统调用: {', '.join([f'{s[0]}({s[1]})' for s in high_count[:3]])}",
                "action": "考虑使用批处理、缓存或异步IO减少系统调用次数。"
            })

    #============================================================================
    # 图形学特定优化分析
    #============================================================================
    def _check_graphics_optimization(self):
        """分析OpenGL/DRM相关信息，生成图形学特定的优化建议"""
        print("  分析图形优化机会...")

        # 分析OpenGL信息
        opengl_info = self.data.get("files", {}).get("opengl_info.txt", "")
        if opengl_info and opengl_info != "N/A":
            self._analyze_opengl_caps(opengl_info)

        # 分析DRM状态
        drm_clients = self.data.get("files", {}).get("drm_clients.txt", "")

        # 分析帧率相关
        app_cpu = self.data.get("files", {}).get("app_cpu.txt", "")
        if app_cpu:
            self._analyze_frame_timing(app_cpu)

        # Vulkan分析
        vulkan_info = self.data.get("files", {}).get("vulkan_info.txt", "")
        if vulkan_info and vulkan_info != "N/A":
            self._analyze_vulkan_info(vulkan_info)

    def _analyze_opengl_caps(self, gl_info: str):
        """分析OpenGL能力，检查优化点"""
        issues = []

        # 检查GL版本
        gl_version = re.search(r'OpenGL version string:\s*(.+)', gl_info)
        if gl_version:
            version_str = gl_version.group(1).strip()
            # 提取主版本号
            version_match = re.search(r'(\d+)\.(\d+)', version_str)
            if version_match:
                major, minor = int(version_match.group(1)), int(version_match.group(2))
                if major < 3:
                    issues.append("OpenGL版本较低（<3.0），无法使用现代渲染优化技术。建议升级到OpenGL ES 3.0或更高版本。")
                elif major == 3 and minor < 2:
                    issues.append("OpenGL 3.x版本，建议考虑使用Compute Shader等更现代的特性。")

        # 检查纹理压缩支持
        compressions = []
        if 'GL_OES_compressed_ETC1_RGB8_texture' in gl_info or 'GL_ETC1_RGB8_OES' in gl_info:
            compressions.append('ETC1')
        if 'GL_OES_texture_compression_astc' in gl_info or 'GL_ASTC' in gl_info:
            compressions.append('ASTC')
        if 'GL_S3TC' in gl_info or 'GL_EXT_texture_compression_s3tc' in gl_info:
            compressions.append('DXT/BC')

        if compressions:
            self.suggestions.append({
                "title": "纹理压缩格式建议",
                "category": "texture",
                "content": f"GPU支持的纹理压缩格式: {', '.join(compressions)}",
                "action": f"使用 {compressions[0]} 格式可显著减少纹理内存占用和带宽使用。"
            })
        else:
            issues.append("未检测到GPU压缩纹理支持，建议评估纹理数据格式优化。")

        # 检查V-Sync设置
        if 'v-sync' in gl_info.lower() or 'vsync' in gl_info.lower():
            self.suggestions.append({
                "title": "垂直同步设置检查",
                "category": "vsync",
                "content": "检测到V-Sync配置",
                "action": "对于固定帧率应用，可考虑使用Triple Buffering优化显示延迟。"
            })

        if issues:
            for issue in issues[:2]:  # 限制数量
                self.issues.append({
                    "severity": "info",
                    "title": "OpenGL配置建议",
                    "detail": issue
                })

    def _analyze_frame_timing(self, cpu_info: str):
        """分析帧渲染时机相关指标"""
        # 从CPU使用率推断帧率稳定性
        cpu_values = re.findall(r"^\s*\d+\s+[\d.]+\s+(\d+\.?\d*)", cpu_info, re.MULTILINE)
        if cpu_values:
            try:
                values = [float(v) for v in cpu_values if float(v) > 0]
                if values:
                    avg_cpu = sum(values) / len(values)
                    max_cpu = max(values)
                    std_dev = (sum((v - avg_cpu) ** 2 for v in values) / len(values)) ** 0.5

                    # CPU使用率很高且波动大
                    if max_cpu > 90:
                        self.issues.append({
                            "severity": "warning",
                            "title": "帧渲染CPU负载过高",
                            "detail": f"峰值CPU使用率 {max_cpu:.1f}%，可能导致帧率不稳定"
                        })
                        self.suggestions.append({
                            "title": "帧率稳定性优化",
                            "category": "frame_rate",
                            "content": "CPU使用率波动较大，可能导致帧时间不稳定。",
                            "action": "建议：1) 使用帧时间预算管理 2) 实现异步渲染管线 3) 将CPU密集操作移至GPU 4) 使用多线程渲染分离逻辑和渲染。"
                        })

                    # 波动检测
                    if std_dev > avg_cpu * 0.3 and avg_cpu > 50:
                        self.suggestions.append({
                            "title": "渲染负载均衡",
                            "category": "load_balance",
                            "content": "检测到渲染负载不均匀，可能导致周期性卡顿。",
                            "action": "建议实现脏矩形更新、视锥剔除、LOD等技术减少每帧渲染负载差异。"
                        })
            except:
                pass

    def _analyze_vulkan_info(self, vulkan_info: str):
        """分析Vulkan信息"""
        # 检查Vulkan特性
        if 'VK_KHR_timeline_semaphore' in vulkan_info or 'timeline semaphore' in vulkan_info.lower():
            self.suggestions.append({
                "title": "Vulkan Timeline Semaphore",
                "category": "vulkan",
                "content": "GPU支持Timeline Semaphore同步机制",
                "action": "使用Timeline Semaphore替代传统Fence可减少同步开销，提高多线程渲染效率。"
            })

        # 检查WSI扩展
        if 'VK_KHR_display' in vulkan_info:
            self.suggestions.append({
                "title": "Vulkan显示扩展支持",
                "category": "vulkan_display",
                "content": "GPU支持原生显示扩展",
                "action": "可考虑使用VK_KHR_display直接控制显示输出，减少 compositor 开销。"
            })
    
    def _check_memory(self):
        """检查内存状态"""
        mem_content = self.data.get("files", {}).get("memory.txt", "")
        
        if not mem_content or mem_content == "N/A":
            return
        
        # 提取内存信息
        total = self._extract_value(mem_content, r"Mem:\s+(\d+)")
        available = self._extract_value(mem_content, r"Mem:\s+\d+\s+(\d+)")
        
        if total and available:
            try:
                total_mb = int(total) / 1024
                avail_mb = int(available) / 1024
                used_pct = (1 - int(available) / int(total)) * 100
                
                if used_pct > 90:
                    self.issues.append({
                        "severity": "error",
                        "title": "内存使用率过高",
                        "detail": f"当前内存使用率: {used_pct:.1f}%, 可用内存: {avail_mb:.0f}MB"
                    })
                    self.suggestions.append({
                        "title": "内存优化建议",
                        "content": "当前内存使用率过高，可能导致系统性能下降。",
                        "action": "检查并优化应用程序内存使用，考虑增加内存或优化内存分配策略。"
                    })
                elif used_pct > 75:
                    self.issues.append({
                        "severity": "warning",
                        "title": "内存使用率偏高",
                        "detail": f"当前内存使用率: {used_pct:.1f}%"
                    })
            except:
                pass
    
    def _check_cpu(self):
        """检查CPU状态"""
        top_content = self.data.get("files", {}).get("top.txt", "")
        vmstat_content = self.data.get("files", {}).get("vmstat.txt", "")
        
        if not top_content or top_content == "N/A":
            return
        
        # 检查CPU等待
        if vmstat_content:
            wa = self._extract数值(vmstat_content, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
            if wa and wa > 30:
                self.issues.append({
                    "severity": "warning",
                    "title": "CPU I/O等待过高",
                    "detail": f"I/O等待: {wa}%, 可能存在I/O瓶颈"
                })
                self.suggestions.append({
                    "title": "I/O性能优化",
                    "content": "CPU大量时间在等待I/O操作完成。",
                    "action": "检查磁盘I/O模式，考虑使用更快的存储设备或优化I/O调度策略。"
                })
    
    def _check_wayland(self):
        """检查Wayland/Weston状态"""
        weston_info = self.data.get("files", {}).get("weston_info.txt", "")
        weston_log = self.data.get("files", {}).get("weston_log.txt", "")
        
        if not weston_info or weston_info == "N/A":
            self.issues.append({
                "severity": "warning",
                "title": "Wayland/Weston未运行",
                "detail": "未检测到 Weston compositor"
            })
            return
        
        # 检查Weston日志错误
        if weston_log and "error" in weston_log.lower():
            self.issues.append({
                "severity": "warning",
                "title": "Weston日志中存在错误",
                "detail": "检测到 compositor 日志错误"
            })
    
    def _check_app_process(self):
        """检查目标应用进程"""
        app_content = self.data.get("files", {}).get("app_process.txt", "")
        
        if not app_content or app_content == "N/A" or "grep" in app_content:
            self.issues.append({
                "severity": "error",
                "title": "目标应用未运行",
                "detail": "未找到目标应用程序进程"
            })
            self.suggestions.append({
                "title": "应用启动检查",
                "content": "目标应用未运行或进程名不匹配。",
                "action": "确认应用已启动，检查进程名称是否与配置一致。"
            })
            return
        
        # 分析CPU使用
        app_cpu = self.data.get("files", {}).get("app_cpu.txt", "")
        if app_cpu:
            cpu_values = re.findall(r"\d+\.\d+\s+(\d+\.\d+)", app_cpu)
            if cpu_values:
                try:
                    avg_cpu = sum(float(v) for v in cpu_values) / len(cpu_values)
                    if avg_cpu > 80:
                        self.issues.append({
                            "severity": "warning",
                            "title": "应用CPU占用过高",
                            "detail": f"平均CPU使用率: {avg_cpu:.1f}%"
                        })
                        self.suggestions.append({
                            "title": "CPU使用优化",
                            "content": "应用程序CPU占用过高。",
                            "action": "优化渲染逻辑、使用多线程、考虑GPU加速计算。"
                        })
                except:
                    pass
        
        # 检查内存泄漏
        app_smaps = self.data.get("files", {}).get("app_smaps.txt", "")
        if app_smaps:
            rss = self._extract_value(app_smaps, r"Rss:\s+(\d+)\s+kB")
            if rss:
                rss_mb = int(rss) / 1024
                if rss_mb > 500:
                    self.suggestions.append({
                        "title": "内存使用监控",
                        "content": f"应用RSS内存: {rss_mb:.0f}MB",
                        "action": "持续监控内存使用趋势，检测可能的内存泄漏。"
                    })
    
    def generate_html(self): 
        """生成完整的HTML报告"""
        print("生成HTML报告...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = self.data.get("app_name", "未知应用")
        
        html = HTML_HEADER.format(title=title)
        
        # 添加头部信息
        html += self._generate_header()
        
        # 添加目录
        html += self._generate_toc()
        
        # 系统概览
        html += self._generate_system_overview()
        
        # Compositor状态
        html += self._generate_compositor_section()
        
        # 应用性能
        html += self._generate_app_section()
        
        # 性能趋势图表
        html += self._generate_performance_chart_section()
        
        # 问题诊断
        html += self._generate_issues_section()

        # 火焰图分析
        html += self._generate_flamegraph_section()

        # 图形渲染优化
        html += self._generate_graphics_optimization_section()

        # 优化建议
        html += self._generate_suggestions_section()
        
        # 添加 Chart.js 和图表渲染脚本
        html += '''
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // 综合性能图表（CPU + 内存）
        if (typeof perfChartData !== 'undefined' && perfChartData.times.length > 0) {
            const perfCtx = document.getElementById('perfChart');
            if (perfCtx) {
                // 检查是否有有效数据（非 null）
                const hasCpuData = perfChartData.appCpu.some(v => v !== null && v !== undefined);
                const hasRssData = perfChartData.appRss.some(v => v !== null && v !== undefined);
                const hasVszData = perfChartData.appVsz.some(v => v !== null && v !== undefined);
                
                if (!hasCpuData && !hasRssData && !hasVszData) {
                    // 所有数据都是 N/A，显示提示信息
                    perfCtx.parentElement.innerHTML += '<div class="no-data" style="padding:40px;text-align:center;color:#999;">采集数据失败：目标进程采样数据全为 N/A<br>请检查：1) 目标进程是否在运行 2) SSH连接是否正常 3) 采样权限是否足够</div>';
                    perfCtx.style.display = 'none';
                } else {
                    // 过滤掉 null 值，只保留有效数据点
                    const validIndices = [];
                    const validTimes = [];
                    const validCpu = [];
                    const validRss = [];
                    const validVsz = [];
                    
                    for (let i = 0; i < perfChartData.times.length; i++) {
                        if (perfChartData.appCpu[i] !== null || 
                            perfChartData.appRss[i] !== null || 
                            perfChartData.appVsz[i] !== null) {
                            validIndices.push(i);
                            validTimes.push(perfChartData.times[i]);
                            validCpu.push(perfChartData.appCpu[i]);
                            validRss.push(perfChartData.appRss[i]);
                            validVsz.push(perfChartData.appVsz[i]);
                        }
                    }
                    
                    const datasets = [];
                    
                    if (hasCpuData) {
                        datasets.push({
                            label: 'CPU %',
                            data: validCpu,
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.1)',
                            tension: 0.3,
                            fill: true,
                            yAxisID: 'y',
                            spanGaps: true
                        });
                    }
                    
                    if (hasRssData) {
                        datasets.push({
                            label: 'RSS (MB)',
                            data: validRss,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            tension: 0.3,
                            fill: true,
                            yAxisID: 'y1',
                            spanGaps: true
                        });
                    }
                    
                    if (hasVszData) {
                        datasets.push({
                            label: 'VSZ (MB)',
                            data: validVsz,
                            borderColor: 'rgb(153, 102, 255)',
                            backgroundColor: 'rgba(153, 102, 255, 0.1)',
                            tension: 0.3,
                            fill: false,
                            yAxisID: 'y1',
                            spanGaps: true
                        });
                    }
                    
                    new Chart(perfCtx, {
                        type: 'line',
                        data: {
                            labels: validTimes.map(t => t + 's'),
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            plugins: {
                                legend: { position: 'top' },
                                tooltip: { callbacks: {} }
                            },
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    beginAtZero: true,
                                    max: 100,
                                    title: { display: true, text: 'CPU %' }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    beginAtZero: true,
                                    suggestedMax: maxMemValue > 0 ? maxMemValue : 100,
                                    grid: { drawOnChartArea: false }
                                }
                            }
                        }
                    });
                }
            }
        }
    });
    </script>
    <script>
    // 热点函数调用栈折叠功能
    function toggleStack(id) {
        var content = document.getElementById(id);
        if (content) {
            if (content.style.display === 'none' || content.style.display === '') {
                content.style.display = 'block';
                // 更新header中的toggle图标
                var header = content.previousElementSibling;
                if (header && header.classList.contains('stack-header')) {
                    var toggle = header.querySelector('.stack-toggle');
                    if (toggle) toggle.textContent = '▲';
                }
            } else {
                content.style.display = 'none';
                var header = content.previousElementSibling;
                if (header && header.classList.contains('stack-header')) {
                    var toggle = header.querySelector('.stack-toggle');
                    if (toggle) toggle.textContent = '▼';
                }
            }
        }
    }

    // 页面加载完成后隐藏所有调用栈内容
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.stack-content').forEach(function(el) {
            el.style.display = 'none';
        });
    });

    // 处理URL中的锚点跳转
    if (window.location.hash) {
        var hash = window.location.hash.substring(1);
        var targetEl = document.getElementById(hash);
        if (targetEl) {
            setTimeout(function() {
                targetEl.scrollIntoView({ behavior: 'smooth' });
                // 如果是stack-content，自动展开
                if (targetEl.classList.contains('stack-content')) {
                    targetEl.style.display = 'block';
                }
                // 如果是stack-header，展开其后的content
                if (targetEl.classList.contains('stack-header')) {
                    var content = targetEl.nextElementSibling;
                    if (content && content.classList.contains('stack-content')) {
                        content.style.display = 'block';
                        var toggle = targetEl.querySelector('.stack-toggle');
                        if (toggle) toggle.textContent = '▲';
                    }
                }
            }, 300);
        }
    }
    </script>
'''
        
        # 页脚
        html += HTML_FOOTER.format(timestamp=timestamp)
        
        return html
    
    def _generate_header(self):
        """生成报告头部"""
        app_name = self.data.get("app_name", "未知")
        host = self.data.get("ssh_host", "未知")
        server = self.data.get("display_server", "未知")
        compositor = self.data.get("compositor", "未知")
        
        return f"""
        <div class="header">
            <h1>AR-HUD应用程序性能分析报告</h1>
            <div class="subtitle">{app_name}</div>
            <div class="meta">
                <div class="meta-item">主机: {host}</div>
                <div class="meta-item">显示服务器: {server}</div>
                <div class="meta-item">Compositor: {compositor}</div>
                <div class="meta-item">时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>
        </div>
        """
    
    def _generate_toc(self): 
        """生成目录"""
        return """
        <nav class="nav">
            <ul>
                <li><a href="#overview">系统概览</a></li>
                <li><a href="#compositor">Compositor状态</a></li>
                <li><a href="#application">应用性能</a></li>
                <li><a href="#issues">问题诊断</a></li>
                <li><a href="#flamegraph">火焰图</a></li>
                <li><a href="#graphics">图形优化</a></li>
                <li><a href="#suggestions">优化建议</a></li>
            </ul>
        </nav>
        """
    
    def _generate_system_overview(self):
        """生成系统概览部分"""
        # 提取系统信息
        os_release = self.data.get("files", {}).get("os_release.txt", "N/A")
        uname = self.data.get("files", {}).get("uname.txt", "N/A")
        nproc = self.data.get("files", {}).get("nproc.txt", "N/A")
        memory = self.data.get("files", {}).get("memory.txt", "N/A")
        
        # 解析CPU核心数
        cpu_count = nproc.strip() if nproc != "N/A" else "N/A"
        
        # 提取内存信息 - 支持 free -h (带单位) 和 free (纯数字，单位为KB)
        mem_total = mem_used = "N/A"

        # 尝试解析 free -h 输出 (如: 863.4M, 1.2G)
        mem_match_h = re.search(r"Mem:\s+([\d.]+)([KMGT]?i?\s)", memory)
        if mem_match_h:
            total_val = float(mem_match_h.group(1))
            total_unit = mem_match_h.group(2).strip()
            # 转换为 GB
            if 'T' in total_unit.upper():
                total_gb = total_val * 1024
            elif 'G' in total_unit.upper():
                total_gb = total_val
            elif 'M' in total_unit.upper():
                total_gb = total_val / 1024
            elif 'K' in total_unit.upper():
                total_gb = total_val / 1024 / 1024
            mem_total = f"{total_gb:.1f} GB"

            # 解析已用内存
            used_match = re.search(r"Mem:\s+[\d.]+[KMGT]?\s+([\d.]+)([KMGT]?)", memory)
            if used_match:
                used_val = float(used_match.group(1))
                used_unit = used_match.group(2)
                if 'G' in used_unit.upper():
                    mem_used = f"{used_val:.1f} GB"
                elif 'M' in used_unit.upper():
                    mem_used = f"{used_val:.0f} MB"
                elif 'K' in used_unit.upper():
                    mem_used = f"{used_val:.0f} KB"
        else:
            # 尝试解析 free 输出 (纯数字，单位为KB)
            mem_match = re.search(r"Mem:\s+(\d+)\s+(\d+)", memory)
            if mem_match:
                total_kb = int(mem_match.group(1))
                used_kb = int(mem_match.group(2))
                mem_total = f"{total_kb / 1024 / 1024:.1f} GB"
                mem_used = f"{used_kb / 1024 / 1024:.1f} GB"
        
        # 解析OS信息
        os_name = "Linux"
        os_match = re.search(r'PRETTY_NAME="([^"]+)"', os_release)
        if os_match:
            os_name = os_match.group(1)
        
        return f"""
        <section id="overview" class="card">
            <h2>1. 系统概览</h2>
            
            <div class="grid" style="grid-template-columns: repeat(4, 1fr);">
                <div class="stat-box">
                    <div class="value">{cpu_count}</div>
                    <div class="label">CPU核芯</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_total}</div>
                    <div class="label">总内存</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_used}</div>
                    <div class="label">已用</div>
                </div>
                <div class="stat-box">
                    <div class="value">{os_name[:15]}</div>
                    <div class="label">OS</div>
                </div>
            </div>
            
            <h3>系统详细信息</h3>
            <pre>{self._escape_html(uname[:500])}</pre>
        </section>
        """
    
    def _generate_compositor_section(self):
        """生成Compositor状态部分"""
        display_server = self.data.get("display_server", "wayland")
        
        if display_server == "wayland":
            weston_info = self.data.get("files", {}).get("weston_info.txt", "N/A")
            weston_log = self.data.get("files", {}).get("weston_log.txt", "N/A")
            compositor_procs = self.data.get("files", {}).get("compositor_process.txt", "N/A")
            
            has_errors = "error" in weston_log.lower() if weston_log != "N/A" else False
            
            return f"""
        <section id="compositor" class="card">
            <h2>3. Compositor状态 (Wayland/Weston)</h2>
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{"运行中" if weston_info != "N/A" else "未运行"}</div>
                    <div class="label">Weston状态</div>
                </div>
                <div class="stat-box">
                    <div class="value">{"<span class='status warning'>有错误</span>" if has_errors else "<span class='status normal'>正常</span>"}</div>
                    <div class="label">日志状态</div>
                </div>
            </div>
            
            <h3>Weston信息</h3>
            <pre>{self._escape_html(weston_info[:2000]) if weston_info != 'N/A' else 'Weston未运行或无法获取信息'}</pre>
            
            <h3>Compositor进程</h3>
            <pre>{self._escape_html(compositor_procs[:1000]) if compositor_procs != 'N/A' else 'N/A'}</pre>
            
            <h3>最近日志</h3>
            <pre>{self._escape_html(weston_log[:2000]) if weston_log != 'N/A' else 'N/A'}</pre>
        </section>
            """
        else:
            # DRM直接模式
            drm_nodes = self.data.get("files", {}).get("drm_nodes.txt", "N/A")
            fbset = self.data.get("files", {}).get("fbset.txt", "N/A")
            framebuffer = self.data.get("files", {}).get("framebuffer.txt", "N/A")
            
            return f"""
        <section id="compositor" class="card">
            <h2>3. DRM状态 (无Compositor)</h2>
            
            <h3>DRM设备节点</h3>
            <pre>{self._escape_html(drm_nodes[:1000]) if drm_nodes != 'N/A' else 'N/A'}</pre>
            
            <h3>Framebuffer信息</h3>
            <pre>{self._escape_html(fbset[:1500]) if fbset != 'N/A' else 'N/A'}</pre>
            
            <h3>虚拟显示尺寸</h3>
            <pre>{framebuffer if framebuffer != 'N/A' else 'N/A'}</pre>
        </section>
            """
    
    def _generate_app_section(self):
        """生成应用性能部分"""
        app_process = self.data.get("files", {}).get("app_process.txt", "N/A")
        app_status = self.data.get("files", {}).get("app_status.txt", "N/A")
        app_cpu = self.data.get("files", {}).get("app_cpu.txt", "N/A")
        app_memory = self.data.get("files", {}).get("app_memory.txt", "N/A")
        app_threads = self.data.get("files", {}).get("app_threads.txt", "N/A")
        app_smaps = self.data.get("files", {}).get("app_smaps.txt", "N/A")
        app_pid = self.data.get("files", {}).get("app_pid.txt", "N/A").strip()
        
        # 计算线程数 - 从 app_status.txt 读取
        thread_count = "N/A"
        if app_status and app_status != "N/A":
            threads_match = re.search(r"Threads:\s+(\d+)", app_status)
            if threads_match:
                thread_count = threads_match.group(1)
        
        # 从 app_cpu.txt (top输出) 解析 CPU 使用率
        # 处理可能的数组类型
        if isinstance(app_cpu, list):
            app_cpu_raw = ' '.join(app_cpu).strip()
        else:
            app_cpu_raw = str(app_cpu).strip() if app_cpu else "N/A"
        
        app_cpu_display = app_cpu_raw if app_cpu_raw and app_cpu_raw != "None" else "N/A"
        cpu_pct = "N/A"
        if app_cpu_display != "N/A":
            # 解析 top 输出格式: PID USER S VIRT RES SHR CPU% COMMAND
            # 示例: " 3198   309 root     S     626m 72.4   1 14.2 ./kanzi"
            top_match = re.search(r'\d+\s+\d+\s+\S+\s+\S+\s+\S+\s+([\d.]+)\s+\S+\s+([\d.]+)', app_cpu_display)
            if top_match:
                cpu_pct = f"{top_match.group(2)}%"
        
        # 提取内存信息 - 从 app_status.txt 读取 VmSize/VmRSS
        mem_rss = mem_vs = "N/A"
        mem_pct = "N/A"
        if app_status and app_status != "N/A":
            # VmRSS: 物理内存
            rss_match = re.search(r"VmRSS:\s+(\d+)\s+kB", app_status)
            # VmSize: 虚拟内存
            vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", app_status)
            # 或者尝试从 smaps 读取
            if app_smaps and app_smaps != "N/A":
                rss_smaps = re.search(r"Rss:\s+(\d+)\s+kB", app_smaps)
                if rss_smaps and not rss_match:
                    mem_rss = f"{int(rss_smaps.group(1)) / 1024:.0f} MB"
                    rss_kb = int(rss_smaps.group(1))
                elif rss_match:
                    mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
                    rss_kb = int(rss_match.group(1))
                else:
                    rss_kb = None
                vs_smaps = re.search(r"VmSize:\s+(\d+)\s+kB", app_smaps)
                if vs_smaps:
                    mem_vs = f"{int(vs_smaps.group(1)) / 1024:.0f} MB"
                elif vs_match:
                    mem_vs = f"{int(vs_match.group(1)) / 1024:.0f} MB"
            elif vs_match:
                mem_vs = f"{int(vs_match.group(1)) / 1024:.0f} MB"
                if rss_match:
                    mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
                    rss_kb = int(rss_match.group(1))
                else:
                    rss_kb = None
            elif rss_match:
                mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
                mem_vs = "N/A"
                rss_kb = int(rss_match.group(1))
            else:
                rss_kb = None
            
                # 计算内存占比 = RSS / 系统总内存
            # 从内存文件读取系统总内存
            if rss_kb:
                mem_info = self.data.get("files", {}).get("memory.txt", "")
                if isinstance(mem_info, list):
                    mem_info = '\n'.join(mem_info)
                total_match = re.search(r'Mem:\s+([\d.]+)([KMGT])', mem_info)
                if total_match:
                    total_mem = float(total_match.group(1))
                    unit = total_match.group(2)
                    # 转换为 KB
                    unit_to_kb = {'K': 1, 'M': 1024, 'G': 1024*1024, 'T': 1024*1024*1024}
                    total_kb = int(total_mem * unit_to_kb.get(unit, 1024))
                    mem_pct = f"{rss_kb / total_kb * 100:.1f}%"
        
        running = app_process != "N/A" and "grep" not in app_process.lower()
        
        return f"""
        <section id="application" class="card">
            <h2>4. 应用性能</h2>
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{"PID: " + app_pid if app_pid and app_pid != "N/A" else "未运行"}</div>
                    <div class="label">PID</div>
                </div>
                <div class="stat-box">
                    <div class="value">{thread_count}</div>
                    <div class="label">线程数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{cpu_pct if cpu_pct != 'N/A' else 'N/A'}</div>
                    <div class="label">CPU</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_pct if mem_pct != 'N/A' else 'N/A'}</div>
                    <div class="label">内存占比</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_rss if mem_rss != 'N/A' else 'N/A'}</div>
                    <div class="label">RSS</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_vs if mem_vs != 'N/A' else 'N/A'}</div>
                    <div class="label">VSZ</div>
                </div>
            </div>

            <h3>进程信息 (top)</h3>
            <pre>{self._escape_html(app_cpu[:1500]) if app_cpu and app_cpu != 'N/A' and app_cpu.strip() else 'N/A'}</pre>

            <h3>内存详情 (VmRSS/VmSize)</h3>
            <pre>{self._escape_html(app_memory[:1500]) if app_memory and app_memory != 'N/A' and app_memory.strip() else 'N/A'}</pre>
            
            <h3>内存映射概览</h3>
            <pre>{self._escape_html(app_smaps[:1500]) if app_smaps != 'N/A' else 'N/A'}</pre>
        </section>
        """
    
    def _generate_performance_chart_section(self): 
        """生成 CPU 和内存折线图部分"""
        perf_samples = self.data.get("files", {}).get("perf_samples.csv", "N/A")
        
        if perf_samples == "N/A" or not perf_samples.strip():
            # 尝试使用 app_cpu.txt 作为备用数据源
            return self._generate_chart_from_fallback()
        
        # 解析 CSV 数据
        lines = perf_samples.strip().split('\n')
        if len(lines) < 2:
            return self._generate_chart_from_fallback()
        
        # 解析表头和数据
        header = lines[0].split(',')
        time_data = []
        app_cpu_data = []
        app_rss_data = []
        app_vsz_data = []
        
        # 统计有效数据点
        valid_data_count = 0
        
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 4:
                time_data.append(parts[0])
                
                # 解析 CPU 值
                cpu_val = parts[1].strip()
                if cpu_val == "N/A" or cpu_val == "" or cpu_val == "0":
                    app_cpu_data.append(None)  # 使用 None 表示无效数据
                else:
                    try:
                        app_cpu_data.append(float(cpu_val))
                        valid_data_count += 1
                    except:
                        app_cpu_data.append(None)
                
                # 解析 RSS 值
                rss_val = parts[2].strip()
                if rss_val == "N/A" or rss_val == "":
                    app_rss_data.append(None)
                else:
                    try:
                        # 处理 "626m" 或 "100K" 格式
                        rss_clean = rss_val.lower().replace('m', '').replace('k', '')
                        app_rss_data.append(float(rss_clean))
                        valid_data_count += 1
                    except:
                        app_rss_data.append(None)
                
                # 解析 VSZ 值
                vsz_val = parts[3].strip()
                if vsz_val == "N/A" or vsz_val == "":
                    app_vsz_data.append(None)
                else:
                    try:
                        vsz_clean = vsz_val.lower().replace('m', '').replace('k', '')
                        app_vsz_data.append(float(vsz_clean))
                        valid_data_count += 1
                    except:
                        app_vsz_data.append(None)
        
        # 检查是否有有效数据
        if valid_data_count == 0:
            return self._generate_chart_from_fallback()
        
        # 计算内存数据的最大值用于Y轴
        max_mem = max(max(app_rss_data) if app_rss_data else 0, max(app_vsz_data) if app_vsz_data else 0)
        max_mem = max_mem * 1.1 if max_mem > 0 else 100  # 留10%余量
        
        # 生成 JSON 数据供 JavaScript 使用
        return f"""
        <section id="perf-chart" class="card">
            <h2>3. 性能趋势</h2>
            
            <div class="chart-container">
                <h3>应用性能趋势 (CPU、内存)</h3>
                <canvas id="perfChart"></canvas>
                <script>
                var perfChartData = {json.dumps({
                    'times': time_data,
                    'appCpu': app_cpu_data,
                    'appRss': app_rss_data,
                    'appVsz': app_vsz_data
                })};
                var maxMemValue = {max_mem};
                </script>
            </div>
        </section>
        """
    
    def _generate_chart_from_fallback(self):
        """从备用数据源(app_cpu.txt, app_status.txt)生成图表"""
        app_cpu = self.data.get("files", {}).get("app_cpu.txt", "N/A")
        app_status = self.data.get("files", {}).get("app_status.txt", "N/A")
        
        time_data = []
        app_cpu_data = []
        app_rss_data = []
        app_vsz_data = []
        
        # 从 app_status.txt 获取 RSS 和 VSZ (这是最可靠的来源)
        if app_status and app_status != "N/A" and app_status.strip():
            # 解析 VmRSS 和 VmSize
            rss_match = re.search(r"VmRSS:\s+(\d+)\s+kB", app_status)
            vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", app_status)
            
            if rss_match:
                app_rss_data = [float(rss_match.group(1)) / 1024]  # KB to MB
                time_data = ["0"]
            
            if vs_match:
                app_vsz_data = [float(vs_match.group(1)) / 1024]  # KB to MB
                if not time_data:
                    time_data = ["0"]
        
        # 从 app_cpu.txt 获取 CPU 使用率 (top输出格式)
        # top -b 输出: PID USER %CPU %MEM RSS VSZ TTY STAT START TIME COMMAND
        # 示例: " 3198   309 root     R     626m 72.4   0 14.2 ./kanzi"
        # 列: VSZ=%MEM, RSS=实际内存值, SHR=0, CPU=CPU%
        if app_cpu and app_cpu != "N/A" and app_cpu.strip():
            lines = app_cpu.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 格式: " 3198   309 root     R     626m 72.4   0 14.2 ./kanzi"
                # 列5=VSZ(MB) 列6=%MEM 列7=SHR 列8=CPU%
                match = re.match(r'\s*(\d+)\s+\d+\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+\S+\s+(\S+)', line)
                if match:
                    cpu_val = match.group(4)  # CPU%
                    time_data = ["0"]
                    
                    try:
                        app_cpu_data.append(float(cpu_val))
                    except:
                        app_cpu_data.append(None)
                    break
        
        # 检查是否有有效数据
        has_cpu = any(v is not None for v in app_cpu_data)
        has_rss = any(v is not None for v in app_rss_data)
        has_vsz = any(v is not None for v in app_vsz_data)
        
        if not has_cpu and not has_rss and not has_vsz:
            return """
        <section id="perf-chart" class="card">
            <h2>3. 性能趋势</h2>
            <div class="no-data">暂无性能数据，请运行采集脚本获取数据</div>
        </section>
            """
        
        # 计算内存数据的最大值用于Y轴
        max_mem = 100
        valid_rss = [v for v in app_rss_data if v is not None]
        valid_vsz = [v for v in app_vsz_data if v is not None]
        if valid_rss:
            max_mem = max(max_mem, max(valid_rss) * 1.2)
        if valid_vsz:
            max_mem = max(max_mem, max(valid_vsz) * 1.2)
        
        # 判断数据来源
        data_source_note = ""
        if time_data == ["0"] and len(time_data) == 1:
            data_source_note = """
            <div class="issue success" style="margin-bottom: 15px;">
                <h4>数据来源: 进程快照数据</h4>
                <p>数据从 app_status.txt 获取 (单次采样)。如需趋势数据，请重新运行采集脚本。</p>
            </div>
            """
        
        return f"""
        <section id="perf-chart" class="card">
            <h2>3. 性能趋势</h2>
            {data_source_note}
            
            <div class="chart-container">
                <h3>应用性能趋势 (CPU、内存)</h3>
                <canvas id="perfChart"></canvas>
                <script>
                var perfChartData = {json.dumps({
                    'times': time_data if time_data else ["0"],
                    'appCpu': app_cpu_data if app_cpu_data else [0],
                    'appRss': app_rss_data if app_rss_data else [0],
                    'appVsz': app_vsz_data if app_vsz_data else [0]
                })};
                var maxMemValue = {max_mem};
                </script>
            </div>
        </section>
        """
    
    def _generate_issues_section(self):
        """生成问题诊断部分"""
        if not self.issues:
            issues_html = """
            <div class="issue success">
                <h4>未发现明显问题</h4>
                <p>系统运行状态良好，未检测到明显的性能问题。</p>
            </div>
            """
        else:
            issues_html = ""
            for issue in self.issues:
                severity_class = issue.get("severity", "warning")
                title = issue.get("title", "未知问题")
                detail = issue.get("detail", "")
                
                issues_html += f"""
                <div class="issue {severity_class}">
                    <h4><span class="status {severity_class}">{severity_class.upper()}</span> {title}</h4>
                    <p>{detail}</p>
                </div>
                """
        
        return f"""
        <section id="issues" class="card">
            <h2>5. 问题诊断</h2>
            {issues_html}
        </section>
        """

    def _generate_flamegraph_section(self): 
        """生成火焰图分析章节"""
        perf_report = self.data.get("files", {}).get("perf_report.txt", "N/A")
        perf_flamegraph_svg = self.data.get("files", {}).get("perf_flamegraph.svg", "")
        stack_counts = self.data.get("files", {}).get("stack_counts.txt", "N/A")
        syscall_counts = self.data.get("files", {}).get("syscall_counts.txt", "N/A")
        function_counts = self.data.get("files", {}).get("function_counts.txt", "N/A")

        # 检查SVG内容是否存在且有效（直接从内存中的数据检查）
        svg_content = perf_flamegraph_svg if perf_flamegraph_svg else ""
        svg_display = "none"
        if svg_content and len(svg_content) > 100:
            svg_display = "block"

        # 解析热点函数 - 优先使用 perf_report.txt，如果太短则使用 perf_report_with_stack.txt
        hot_functions = []
        seen = set()  # 用于去重
        perf_report_with_stack = self.data.get("files", {}).get("perf_report_with_stack.txt", "")

        # 确定使用哪个报告文件
        source_report = perf_report
        # 如果 perf_report 是错误信息或太短，使用 perf_report_with_stack
        if not source_report or source_report == "N/A" or len(source_report.strip()) < 100 or "not owned" in source_report or "采集失败" in source_report:
            source_report = perf_report_with_stack

        if source_report and source_report != "N/A" and "采集失败" not in source_report:
            for line in source_report.split('\n'):
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                # perf report 格式: "[空白][Children%][空白][Self%][空白][Command][空白][Shared Object][空白][Symbol]"
                # 例如: "    89.49%     0.00%  kanzi    kanzi                [.] 0x000000000041c55c"
                match = re.match(r'\s*(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+(\S+)\s+\[.\]\s+(0x\S+)', line)
                if match:
                    pct = float(match.group(1))
                    module = match.group(2).strip()
                    addr = match.group(3).strip()
                    
                    func = module.strip('[]')
                    if func == 'kanzi' and addr.startswith('0x'):
                        func = f"0x{addr[2:18]}"
                    
                    if func and func != '[unknown]':
                        key = (func, pct)
                        if key not in seen:
                            seen.add(key)
                            hot_functions.append((func, pct))
                        continue
                
                # 处理 kernel 符号格式: [k] 0xaddr
                match2 = re.match(r'\s*(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+(\S+)\s+\[k\]\s+(0x\S+)', line)
                if match2:
                    pct = float(match2.group(1))
                    module = match2.group(2).strip()
                    addr = match2.group(3).strip()
                    func = module.strip('[]')
                    
                    if func == 'kernel.kallsyms':
                        func = f"[k]0x{addr[2:18]}"
                    
                    if func:
                        key = (func, pct)
                        if key not in seen:
                            seen.add(key)
                            hot_functions.append((func, pct))

        # 分类热点函数
        graphics_funcs = []
        general_funcs = []
        graphics_func_names = set()
        for func, pct in hot_functions:
            func_lower = func.lower()
            # 图形学相关函数
            if any(kw in func_lower for kw in ['gl', 'egl', 'drm', 'gpu', 'shader', 'texture', 'render', ' Mesa', 'intel', 'i915', 'libgles', 'libsrv', 'pvrsrv']):
                graphics_funcs.append((func, pct))
                graphics_func_names.add(func)
            # 保留所有函数，包括地址格式的（用于显示热点）
            else:
                general_funcs.append((func, pct))

        # 生成热点函数调用栈详情
        hot_stacks_html = ""
        if stack_counts and stack_counts != "N/A" and hot_functions:
            hot_stacks_html = self._generate_hot_function_stacks(stack_counts, hot_functions[:10])

        # 系统调用分析
        syscall_html = ""
        if syscall_counts and syscall_counts != "N/A" and "N/A" not in syscall_counts:
            syscall_lines = [l for l in syscall_counts.split('\n') if l.strip()][:10]
            if syscall_lines:
                syscall_html = "<h3>系统调用统计</h3><pre>" + "\n".join(self._escape_html(l) for l in syscall_lines) + "</pre>"

        # 函数计数
        func_count_html = ""
        if function_counts and function_counts != "N/A" and "N/A" not in function_counts:
            func_lines = [l for l in function_counts.split('\n') if l.strip() and not l.startswith('#')][:15]
            if func_lines:
                func_count_html = "<h3>图形函数调用频率</h3><pre>" + "\n".join(self._escape_html(l) for l in func_lines) + "</pre>"

        # 热点函数表格
        hot_funcs_html = ""
        call_stack_note = ""
        
        # 检查是否有调用链数据
        has_callchain = stack_counts and stack_counts != "N/A" and "no callchain" not in stack_counts.lower() and "N/A" not in stack_counts
        # 如果 stack_counts 没有调用链，但 perf_report_with_stack.txt 有内容，认为有调用链
        if not has_callchain and perf_report_with_stack and len(perf_report_with_stack) > 1000:
            has_callchain = True
        # perf_report不为空且不是只有占位符
        perf_report_stripped = perf_report.strip() if perf_report else ""
        has_perf_report = perf_report and perf_report != "N/A" and len(perf_report_stripped) > 50
        # 检查perf报告是否只是错误提示
        is_placeholder_report = perf_report and ("perf报告生成失败" in perf_report or "not owned" in perf_report)
        
        if hot_functions:
            hot_funcs_html = """
            <table class="hot-functions-table">
                <tr><th>排名</th><th>函数名</th><th>CPU占比</th><th>类别</th><th>操作</th></tr>"""
            for i, (func, pct) in enumerate(hot_functions[:15]):
                category = "图形" if func in graphics_func_names else "通用"
                # 改进函数名ID生成，确保一致性
                func_id_clean = re.sub(r'[^a-zA-Z0-9]', '_', func[:30]).replace('_', '')
                func_id = f"stack_{func_id_clean}"
                # 高亮超过5%的热点
                highlight_class = "high-usage" if pct >= 5 else ""

                # 调用栈链接（只有有调用链数据时才显示）
                if has_callchain and pct >= 0.5:  # 只有当函数占比>=0.5%且存在调用链数据时才显示链接
                    action_link = f'<a href="#{func_id}" class="stack-link" onclick="toggleStack(\'{func_id}_content\'); return false;">查看调用栈</a>'
                else:
                    action_link = '<span class="no-data">无调用栈数据</span>'

                hot_funcs_html += f"""<tr class="{highlight_class}">
                    <td>{i+1}</td>
                    <td><code class="func-name">{self._escape_html(func)}</code></td>
                    <td>{pct:.2f}%</td>
                    <td><span class="category-tag {category.lower()}">{category}</span></td>
                    <td>{action_link}</td>
                </tr>"""
            hot_funcs_html += "</table>"
            
            if not has_callchain:
                call_stack_note = '''
                <div class="issue warning" style="margin-top: 15px;">
                    <h4>注意：调用栈数据不可用</h4>
                    <p>当前perf数据采集时未使用"-g"参数，因此没有调用链信息。</p>
                    <p>如需查看详细调用栈，请在远程设备上使用以下命令重新采集perf数据：</p>
                    <div class="code">perf record -F 99 -p &lt;PID&gt; -a -g -o /tmp/perf.data -- sleep 10</div>
                </div>'''
        else:
            hot_funcs_html = '<p class="no-data">暂无热点函数数据</p>'
            # 如果有 perf 报告但没有热点函数，显示 warning
            if is_placeholder_report or (has_perf_report and len(hot_functions) == 0):
                call_stack_note = '''
                <div class="issue warning" style="margin-top: 15px;">
                    <h4>注意：未能解析出热点函数</h4>
                    <p>perf报告存在但未能解析出热点函数。可能原因：</p>
                    <ul style="margin: 10px 0 10px 20px;">
                        <li>perf.data采集时未使用"-g"参数，没有调用链信息</li>
                        <li>sudo权限不足，无法读取perf.data</li>
                        <li>perf工具版本不匹配</li>
                    </ul>
                    <p style="margin-top: 10px;"><strong>解决方案：</strong>在远程设备上使用以下命令重新采集perf数据：</p>
                    <div class="code">perf record -F 99 -p &lt;PID&gt; -a -g -o /tmp/perf.data -- sleep 10</div>
                </div>'''

        return f"""
        <section id="flamegraph" class="card">
            <h2>6. 火焰图与热点分析</h2>

            <div class="grid">
                <div class="stat-box">
                    <div class="value">{len(hot_functions)}</div>
                    <div class="label">检测到的热点函数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{len(graphics_funcs)}</div>
                    <div class="label">图形相关热点</div>
                </div>
                <div class="stat-box">
                    <div class="value">{f"{hot_functions[0][1]:.1f}%" if hot_functions else "0.0%"}</div>
                    <div class="label">最高热点占比</div>
                </div>
            </div>

            <!-- SVG火焰图显示 -->
            <div class="svg-flamegraph-container" style="display: {svg_display}; margin: 20px 0;">
                <h3>火焰图 (SVG)</h3>
                <p class="tip">点击火焰图中的函数可以查看详细信息。火焰图颜色说明: 红色=渲染, 橙色=计算, 黄色=系统调用, 绿色=应用代码, 蓝色=库函数。</p>
                <div class="svg-wrapper">
                    {svg_content}
                </div>
                <a href="perf_flamegraph.svg" download="perf_flamegraph.svg" class="download-link">下载SVG火焰图</a>
            </div>
            {'<p class="no-data">SVG火焰图暂不可用（需在本地执行perf生成）</p>' if svg_display == 'none' else ''}

            <h3>热点函数列表</h3>
            <p class="tip">高亮显示CPU占比>=5%的热点函数，点击"查看调用栈"可跳转到该函数的详细调用链。</p>
            {hot_funcs_html}
            {call_stack_note}

            {hot_stacks_html}

            <h3>perf采样报告</h3>
            <pre>{self._escape_html(perf_report[:5000]) if perf_report != 'N/A' else 'perf数据不可用'}</pre>

            {syscall_html}
            {func_count_html}

            <div class="suggestion">
                <h4>热点分析方法</h4>
                <p>1. 查看上方热点函数列表，优先关注占比>5%的函数（高亮行）</p>
                <p>2. 图形相关热点（gl*/egl*/drm*）建议检查着色器复杂度、纹理格式、绘制调用次数</p>
                <p>3. 通用热点需评估是否有算法优化空间或缓存可能</p>
                <p>4. 查看上方火焰图，点击热点函数可放大查看调用栈详情</p>
            </div>
        </section>
        """

    def _generate_hot_function_stacks(self, stack_data: str, hot_functions: List[Tuple[str, float]]): 
        """为热点函数生成调用栈详情"""
        html = "<h3 id='hot-stacks'>热点函数调用栈详情</h3>"
        html += "<div class='stack-details'>"

        # 过滤掉CPU占比太低的函数
        filtered_functions = [(func, pct) for func, pct in hot_functions if pct >= 0.5]

        for func, pct in filtered_functions:
            # 提取该函数相关的调用栈
            func_stacks = self._extract_call_stacks(stack_data, func)

            # 改进函数名用于HTML id的清理（避免特殊字符）
            func_id_clean = re.sub(r'[^a-zA-Z0-9]', '_', func[:30]).replace('_', '')
            func_id = f"stack_{func_id_clean}"

            if func_stacks:
                html += f"""
                <div class="stack-function" id="{func_id}">
                    <div class="stack-header" onclick="toggleStack('{func_id}_content')">
                        <span class="stack-name"><code>{self._escape_html(func)}</code></span>
                        <span class="stack-pct">{pct:.2f}%</span>
                        <span class="stack-toggle">▼</span>
                        <a href="#{func_id}_link" class="back-link">↑返回列表</a>
                    </div>
                    <div class="stack-content" id="{func_id}_content">
                        <pre>{func_stacks}</pre>
                    </div>
                </div>
                """
            else:
                # 即使没有调用栈也显示函数名
                html += f"""
                <div class="stack-function" id="{func_id}">
                    <div class="stack-header" onclick="toggleStack('{func_id}_content')">
                        <span class="stack-name"><code>{self._escape_html(func)}</code></span>
                        <span class="stack-pct">{pct:.2f}%</span>
                        <span class="stack-toggle">▼</span>
                        <a href="#{func_id}_link" class="back-link">↑返回列表</a>
                    </div>
                    <div class="stack-content" id="{func_id}_content">
                        <pre>(无详细调用栈数据)</pre>
                    </div>
                </div>
                """

        html += "</div>"

        return html

    def _generate_hot_function_stacks_from_data(self, hot_functions_data: Dict): 
        """从解析后的热点函数数据生成调用栈详情HTML"""
        html = "<h3 id='hot-stacks'>热点函数调用栈详情</h3>"
        html += "<div class='stack-details'>"

        for func_name, data in hot_functions_data.items():
            pct = data.get("pct", 0)
            stack = data.get("stack", [])

            if pct < 0.5:  # 只显示占比>0.5%的函数
                continue

            func_id = "stack_" + re.sub(r'[^a-zA-Z0-9]', '_', func_name[:30])

            # 生成调用栈HTML
            if stack:
                stack_html = ""
                for i, frame in enumerate(stack[:15]):  # 最多显示15层
                    if i == 0:
                        stack_html += f'<span class="func-entry">└─ {self._escape_html(frame)} (root)</span>\n'
                    else:
                        indent = '&nbsp;&nbsp;&nbsp;' * (i - 1)
                        stack_html += f'{indent}└─ {self._escape_html(frame)}\n'

                html += f"""
                <div class="stack-function" id="{func_id}">
                    <div class="stack-header" onclick="toggleStack('{func_id}_content')">
                        <span class="stack-name"><code>{self._escape_html(func_name)}</code></span>
                        <span class="stack-pct">{pct:.2f}%</span>
                        <span class="stack-toggle">▼</span>
                        <a href="#stack_{func_id}_link" class="back-link">↑返回列表</a>
                    </div>
                    <div class="stack-content" id="{func_id}_content">
                        <pre>{stack_html}</pre>
                    </div>
                </div>
                """

        html += "</div>"
        return html

    def _extract_call_stacks(self, stack_data: str, func_name: str):
        """从栈数据中提取特定函数的调用栈"""
        lines = stack_data.split('\n')
        
        # 首先尝试从 perf report (带调用栈格式) 中提取
        perf_report_data = self.data.get("files", {}).get("perf_report_with_stack.txt", "")
        if perf_report_data:
            result = self._extract_from_perf_report(perf_report_data, func_name)
            if result:
                return result
        
        # 回退到 stack_counts.txt
        stack_frames = []
        found_target = False
        current_stack = []
        
        # 提取要搜索的地址有意义部分（如果func_name是地址）
        search_addr_part = None
        if func_name.startswith('0x') or func_name.startswith('[k]0x') or '0x' in func_name:
            # 提取地址部分
            addr_match = re.search(r'0x([0-9a-f]+)', func_name)
            if addr_match:
                full_addr = addr_match.group(1)
                # 使用地址的最后6位进行匹配
                if len(full_addr) >= 6:
                    search_addr_part = full_addr[-6:]
                else:
                    search_addr_part = full_addr.lstrip('0')

        for line in lines:
            stripped = line.strip()

            # perf script 输出格式: "comm  pid  [cpu]  time: event"
            # 检测新事件的开始
            if re.match(r'^\S+\s+\d+\s+\[\d+\]\s+\d+\.\d+:', stripped):
                if found_target and current_stack:
                    stack_frames.extend(current_stack)
                current_stack = []
                found_target = False
                continue

            # 检查是否包含目标函数或地址
            if search_addr_part:
                # 改进地址匹配 - 支持多种地址格式
                addr_match = re.search(r'[0-9a-f]{6,}', stripped)
                if addr_match:
                    addr_in_line = addr_match.group(0)
                    # 检查地址的最后几位是否匹配
                    if len(addr_in_line) >= 6 and addr_in_line[-6:] == search_addr_part:
                        found_target = True
                    elif search_addr_part in addr_in_line:
                        found_target = True
            elif func_name.lower() in stripped.lower():
                # 检查模块名匹配
                found_target = True
            
            # 解析栈帧行
            if stripped and line.startswith('\t'):
                frame_text = stripped
                match = re.match(r'([0-9a-f]+)\s+\[unknown\]\s+\(([^)]+)\)', frame_text)
                if match:
                    addr = match.group(1)
                    module = match.group(2)
                    
                    if 'libc' in module:
                        module_name = 'libc'
                    elif 'libGLES' in module or 'libGL' in module:
                        module_name = 'libGLES'
                    elif 'libsrv' in module:
                        module_name = 'libsrv_um'
                    elif 'pvrsrv' in module:
                        module_name = 'pvrsrvkm'
                    elif 'libpthread' in module:
                        module_name = 'libpthread'
                    elif 'kanzi' in module or module.startswith('/HUD'):
                        module_name = 'kanzi'
                    elif 'kernel' in module or module.startswith('['):
                        module_name = 'kernel'
                    else:
                        import os
                        module_name = os.path.basename(module)
                    
                    current_stack.append(f"{module_name}:{addr[-8:]}")
        
        if found_target and current_stack:
            stack_frames.extend(current_stack)
        
        if not stack_frames:
            return ""
        
        stack_frames.reverse()
        deduped = []
        seen_frames = set()
        for f in stack_frames[:20]:
            if f not in seen_frames:
                seen_frames.add(f)
                deduped.append(f)
        
        result = []
        for i, frame in enumerate(deduped):
            if i == 0:
                result.append(f'<span class="func-entry">└─ {frame}</span>')
            else:
                indent = '&nbsp;&nbsp;&nbsp;' * (i - 1)
                result.append(f'{indent}└─ {frame}')
        
        return '\n'.join(result)

    def _extract_from_perf_report(self, perf_text: str, func_name: str): 
        """从带调用栈的 perf report 中提取调用链"""
        lines = perf_text.split('\n')

        # 提取搜索地址 - 改进地址匹配
        search_addr = None
        if func_name.startswith('0x') and len(func_name) > 2:
            addr = func_name[2:]  # 去掉 0x
            search_addr = addr
        elif '0x' in func_name:
            # 从函数名中提取地址
            addr_match = re.search(r'0x([0-9a-f]+)', func_name)
            if addr_match:
                search_addr = addr_match.group(1)

        if not search_addr:
            return ""

        # 查找包含目标函数的区域
        call_chain = []  # 保存从根到叶子的调用链
        found_hotspot = False

        for i, line in enumerate(lines):
            stripped = line.rstrip()

            # 检查是否是热点行（包含Children%和地址）
            hotspot_match = re.match(r'\s+(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+\S+\s+\[.\]\s+(0x\S+)', stripped)
            if hotspot_match:
                hotspot_addr = hotspot_match.group(2)
                # 检查是否匹配目标地址（支持前缀匹配）
                if search_addr in hotspot_addr or hotspot_addr.endswith(search_addr[-6:]):
                    found_hotspot = True
                    # 开始收集调用栈
                    continue
                elif found_hotspot:
                    # 遇到新的热点，停止收集
                    break

            if not found_hotspot:
                continue

            # 解析调用栈行
            # 格式示例:
            # "---0x435bb0"                    <- 热点函数 (深度0)
            # "   0xffff899d7098"              <- 调用者 (深度1)
            # "   0x41c55c"                    <- 调用者的调用者 (深度2)

            # 跳过非调用栈行
            if not re.search(r'0x[0-9a-f]+', stripped):
                continue

            # 计算缩进级别
            indent = len(line) - len(line.lstrip())
            level = indent // 3  # 假设每级3个字符

            # 提取地址
            addr_match = re.search(r'0x([0-9a-f]+)', stripped)
            if addr_match:
                addr = addr_match.group(1)

                # 判断是内核地址还是用户地址
                if addr.startswith('ffff'):
                    module = 'kernel'
                    # 内核地址，只保留后8位
                    frame = f"{module}:0x{addr[-8:]}"
                else:
                    module = 'kanzi'
                    # 用户地址，只保留后6位
                    frame = f"{module}:0x{addr[-6:]}"

                # 添加到调用链
                call_chain.append((level, frame))

        if not call_chain:
            return ""

        # 去重并生成输出（按深度排序）
        call_chain.sort()  # 按深度排序
        deduped = []
        seen = set()
        for level, frame in call_chain[:20]:
            if frame not in seen:
                seen.add(frame)
                deduped.append((level, frame))

        # 生成层级调用关系
        result = []
        for i, (level, frame) in enumerate(deduped):
            if i == 0:
                # 入口函数（根）
                result.append(f'<span class="func-entry">└─ {frame} (root)</span>')
            else:
                indent = '&nbsp;&nbsp;&nbsp;' * (level - 1)
                result.append(f'{indent}└─ {frame}')

        return '\n'.join(result)

    def _generate_graphics_optimization_section(self):
        """生成图形渲染优化章节"""
        opengl_info = self.data.get("files", {}).get("opengl_info.txt", "N/A")
        vulkan_info = self.data.get("files", {}).get("vulkan_info.txt", "N/A")
        drm_traces = self.data.get("files", {}).get("drm_traces.txt", "N/A")

        # 解析OpenGL版本
        gl_version = "未知"
        gl_renderer = "未知"
        if opengl_info and opengl_info != "N/A":
            v_match = re.search(r'OpenGL version string:\s*(.+)', opengl_info)
            r_match = re.search(r'OpenGL renderer:\s*(.+)', opengl_info)
            if v_match:
                gl_version = v_match.group(1).strip()[:40]
            if r_match:
                gl_renderer = r_match.group(1).strip()[:40]

        # 纹理压缩支持
        texture_formats = []
        if opengl_info:
            if 'ETC1' in opengl_info or 'ETC' in opengl_info:
                texture_formats.append('ETC')
            if 'ASTC' in opengl_info:
                texture_formats.append('ASTC')
            if 'S3TC' in opengl_info or 'DXT' in opengl_info or 'BC' in opengl_info:
                texture_formats.append('BC/DXT')
            if 'RGTC' in opengl_info or 'LATC' in opengl_info:
                texture_formats.append('RGTC')

        formats_str = ', '.join(texture_formats) if texture_formats else '未检测到压缩格式'

        return f"""
        <section id="graphics" class="card">
            <h2>7. 图形渲染分析</h2>

            <h3>图形API信息</h3>
            <table>
                <tr><th>项目</th><th>值</th></tr>
                <tr><td>OpenGL版本</td><td>{gl_version}</td></tr>
                <tr><td>渲染器</td><td>{gl_renderer}</td></tr>
                <tr><td>支持的纹理压缩</td><td>{formats_str}</td></tr>
            </table>

            {self._generate_graphics_optimization_suggestions(texture_formats, gl_version)}

            <div class="issue success">
                <h4>图形优化检查清单</h4>
                <ul style="margin: 10px 0 10px 20px;">
                    <li>□ 使用压缩纹理减少内存带宽占用</li>
                    <li>□ 合并绘制调用，使用实例化渲染</li>
                    <li>□ 实现帧率限制，避免无意义的过高帧率</li>
                    <li>□ 检查是否有冗余的状态切换</li>
                    <li>□ 考虑使用脏矩形更新替代全屏重绘</li>
                    <li>□ 优化着色器，避免在顶点着色器中进行复杂计算</li>
                    <li>□ 使用Uniform Buffer替代大量uniform变量</li>
                    <li>□ 实施纹理流式加载，延迟加载远处资源</li>
                </ul>
            </div>
        </section>
        """

    def _generate_graphics_optimization_suggestions(self, texture_formats: list, gl_version: str): 
        """生成针对当前GPU配置的图形优化建议"""
        suggestions = []

        # 纹理格式建议
        if 'ASTC' in texture_formats:
            suggestions.append("推荐使用ASTC纹理格式，提供高质量压缩比（可达0.5bpp），特别适合移动GPU。")
        elif 'ETC' in texture_formats:
            suggestions.append("推荐使用ETC2纹理格式（向后兼容ETC1），广泛支持且压缩效果好。")
        elif 'BC' in texture_formats or 'DXT' in texture_formats:
            suggestions.append("推荐使用BC/DXT纹理格式，适合桌面GPU，可显著减少显存占用。")
        else:
            suggestions.append("建议评估是否可使用压缩纹理格式以优化内存使用。")

        # OpenGL版本建议
        if 'ES 2' in gl_version or 'OpenGL ES 2' in gl_version:
            suggestions.append("OpenGL ES 2.0环境限制较多，建议避免使用MRT（多渲染目标）等高级特性。")
        elif 'ES 3' in gl_version or 'OpenGL ES 3' in gl_version:
            suggestions.append("OpenGL ES 3.0支持实例化渲染和MSAA，可优化大量相似物体的渲染效率。")
        elif '4.' in gl_version or '5.' in gl_version:
            suggestions.append("现代OpenGL环境，可使用Compute Shader进行通用计算，将部分CPU负载转移至GPU。")

        if suggestions:
            html = "<h3>图形优化建议</h3>"
            for i, s in enumerate(suggestions, 1):
                html += f'<div class="suggestion"><h4>{i}. 优化建议</h4><p>{s}</p></div>'
            return html
        return ""

    def _generate_suggestions_section(self):
        """生成优化建议部分"""
        if not self.suggestions:
            suggestions_html = """
            <div class="suggestion" style="background: #d4edda; border-left-color: #28a745;">
                <h4>系统状态良好</h4>
                <p>当前未需要特殊的优化建议。</p>
            </div>
            """
        else:
            suggestions_html = ""
            for i, suggestion in enumerate(self.suggestions, 1):
                title = suggestion.get("title", f"优化建议 #{i}")
                content = suggestion.get("content", "")
                action = suggestion.get("action", "")
                
                suggestions_html += f"""
                <div class="suggestion">
                    <h4>{i}. {title}</h4>
                    <p>{content}</p>
                    {f'<div class="code">{action}</div>' if action else ''}
                </div>
                """
        
        return f"""
        <section id="suggestions" class="card">
            <h2>8. 优化建议</h2>
            {suggestions_html}

            <h3>通用优化策略</h3>
            <div class="suggestion">
                <h4>渲染优化</h4>
                <p>针对嵌入式系统的图形优化建议：</p>
                <ul style="margin: 10px 0 10px 20px;">
                    <li>使用高效的纹理格式（如ETC、ASTC）</li>
                    <li>合并绘制调用，减少draw call数量</li>
                    <li>使用实例化渲染处理大量相似物体</li>
                    <li>启用纹理压缩减少带宽占用</li>
                </ul>
            </div>
            
            <div class="suggestion">
                <h4>Wayland/Weston优化</h4>
                <p>Compositor层面优化：</p>
                <ul style="margin: 10px 0 10px 20px;">
                    <li>禁用不必要的Weston插件</li>
                    <li>使用脏矩形更新减少全屏重绘</li>
                    <li>配置合适的帧率上限</li>
                    <li>使用hwcomposer后端替代GBM</li>
                </ul>
            </div>
            
            <div class="suggestion">
                <h4>应用程序优化</h4>
                <p>应用层优化策略：</p>
                <ul style="margin: 10px 0 10px 20px;">
                    <li>使用双缓冲或多缓冲减少撕裂</li>
                    <li>实现帧率限制避免无意义的高帧率</li>
                    <li>使用内存池减少分配开销</li>
                    <li>优化事件处理循环</li>
                </ul>
            </div>
        </section>
        """
    
    def _escape_html(self, text: str):
        """转义HTML特殊字符"""
        if not text:
            return ""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
    
    def save_report(self, html_content: str):
        """保存报告到文件"""
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"报告已保存到: {self.output_path}")
    
    def run(self):
        """运行完整流程"""
        if not self.load_data():
            print("错误: 无法加载数据文件")
            sys.exit(1)
        
        self.analyze_data()
        html_content = self.generate_html()
        self.save_report(html_content)
        
        return self.output_path


def main():
    parser = argparse.ArgumentParser(
        description="图形显示应用程序性能分析报告生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_report.py
  python generate_report.py -d ./report
  python generate_report.py -d ./report -o ./my_report.html
        """
    )
    
    parser.add_argument("-d", "--data-dir",
                        default=str(OUTPUT_DIR),
                        help="数据目录路径 (默认: ./report)")
    
    parser.add_argument("-o", "--output",
                        default=None,
                        help="输出HTML文件路径 (默认: {data-dir}/report.html)")
    
    args = parser.parse_args()
    
    # 设置默认输出路径
    if not args.output:
        args.output = str(Path(args.data_dir) / "report.html")
    
    generator = PerformanceReportGenerator(args.data_dir, args.output)
    output_path = generator.run()
    
    print(f"\n成功生成性能分析报告: {output_path}")


if __name__ == "__main__":
    main()
