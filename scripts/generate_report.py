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
        self.data: Dict = {}
        self.issues: List[Dict] = []
        self.suggestions: List[Dict] = []
        
    def load_data(self) -> bool:
        """加载数据文件"""
        print(f"从 {self.data_dir} 加载数据...")
        
        # 查找JSON汇总文件
        json_files = list(self.data_dir.glob("remote_data_*.json"))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            # 加载所有txt文件
            self._load_text_files()
        
        return bool(self.data)
    
    def _load_text_files(self):
        """从文本文件加载数据"""
        self.data = {"files": {}}
        
        for txt_file in self.data_dir.glob("*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][txt_file.name] = f.read()
            except Exception as e:
                print(f"读取 {txt_file.name} 失败: {e}")
    
    def analyze_data(self):
        """分析数据并识别问题"""
        print("分析性能数据...")
        
        self._check_memory()
        self._check_gpu()
        self._check_cpu()
        self._check_wayland()
        self._check_app_process()
        
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
    
    def _check_gpu(self):
        """检查GPU状态"""
        gpu_util = self.data.get("files", {}).get("gpu_utilization.txt", "")
        
        if gpu_util and gpu_util != "N/A":
            try:
                # 尝试提取GPU利用率
                util_match = re.search(r"(\d+)", gpu_util)
                if util_match:
                    util = int(util_match.group(1))
                    
                    if util > 95:
                        self.issues.append({
                            "severity": "warning",
                            "title": "GPU利用率接近满载",
                            "detail": f"GPU利用率: {util}%"
                        })
                        self.suggestions.append({
                            "title": "GPU渲染优化",
                            "content": "GPU负载过高，可能是渲染管线瓶颈。",
                            "action": "考虑优化着色器、使用GPU压缩纹理、减少绘制调用次数。"
                        })
            except:
                pass
        
        # 检查DRM状态
        drm_state = self.data.get("files", {}).get("drm_state.txt", "")
        if not drm_state or drm_state == "N/A":
            self.issues.append({
                "severity": "warning",
                "title": "DRM调试信息不可用",
                "detail": "无法获取详细的GPU状态信息，可能需要root权限。"
            })
    
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
    
    def generate_html(self) -> str:
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
        
        # GPU状态
        html += self._generate_gpu_section()
        
        # Compositor状态
        html += self._generate_compositor_section()
        
        # 应用性能
        html += self._generate_app_section()
        
        # 问题诊断
        html += self._generate_issues_section()
        
        # 优化建议
        html += self._generate_suggestions_section()
        
        # 页脚
        html += HTML_FOOTER.format(timestamp=timestamp)
        
        return html
    
    def _generate_header(self) -> str:
        """生成报告头部"""
        app_name = self.data.get("app_name", "未知")
        host = self.data.get("ssh_host", "未知")
        server = self.data.get("display_server", "未知")
        compositor = self.data.get("compositor", "未知")
        
        return f"""
        <div class="header">
            <h1>图形显示应用程序性能分析报告</h1>
            <div class="subtitle">{app_name}</div>
            <div class="meta">
                <div class="meta-item">主机: {host}</div>
                <div class="meta-item">显示服务器: {server}</div>
                <div class="meta-item">Compositor: {compositor}</div>
                <div class="meta-item">时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>
        </div>
        """
    
    def _generate_toc(self) -> str:
        """生成目录"""
        return """
        <nav class="nav">
            <ul>
                <li><a href="#overview">系统概览</a></li>
                <li><a href="#gpu">GPU状态</a></li>
                <li><a href="#compositor">Compositor状态</a></li>
                <li><a href="#application">应用性能</a></li>
                <li><a href="#issues">问题诊断</a></li>
                <li><a href="#suggestions">优化建议</a></li>
            </ul>
        </nav>
        """
    
    def _generate_system_overview(self) -> str:
        """生成系统概览部分"""
        # 提取系统信息
        os_release = self.data.get("files", {}).get("os_release.txt", "N/A")
        uname = self.data.get("files", {}).get("uname.txt", "N/A")
        nproc = self.data.get("files", {}).get("nproc.txt", "N/A")
        memory = self.data.get("files", {}).get("memory.txt", "N/A")
        
        # 解析CPU核心数
        cpu_count = nproc.strip() if nproc != "N/A" else "N/A"
        
        # 提取内存信息
        mem_match = re.search(r"Mem:\s+(\d+)\s+(\d+)", memory)
        mem_total = mem_used = "N/A"
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
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{cpu_count}</div>
                    <div class="label">CPU核心数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_total}</div>
                    <div class="label">总内存</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_used}</div>
                    <div class="label">已用内存</div>
                </div>
                <div class="stat-box">
                    <div class="value">{os_name[:15]}</div>
                    <div class="label">操作系统</div>
                </div>
            </div>
            
            <h3>系统详细信息</h3>
            <pre>{self._escape_html(uname[:500])}</pre>
        </section>
        """
    
    def _generate_gpu_section(self) -> str:
        """生成GPU状态部分"""
        drm_devices = self.data.get("files", {}).get("drm_devices.txt", "N/A")
        gpu_vram = self.data.get("files", {}).get("gpu_vram.txt", "N/A")
        gpu_gtt = self.data.get("files", {}).get("gpu_gtt.txt", "N/A")
        gpu_util = self.data.get("files", {}).get("gpu_utilization.txt", "N/A")
        drm_status = self.data.get("files", {}).get("drm_status.txt", "N/A")
        
        # 处理GPU利用率显示
        util_value = "N/A"
        util_class = "normal"
        if gpu_util and gpu_util != "N/A":
            try:
                util_match = re.search(r"(\d+)", gpu_util)
                if util_match:
                    util_value = util_match.group(1) + "%"
                    util_pct = int(util_match.group(1))
                    if util_pct > 90:
                        util_class = "high"
                    elif util_pct > 70:
                        util_class = "medium"
            except:
                pass
        
        # 处理VRAM显示
        vram_display = gpu_vram.strip() if gpu_vram != "N/A" else "不可用"
        if vram_display != "不可用" and vram_display != "N/A":
            try:
                vram_kb = int(re.search(r"(\d+)", vram_display).group(1))
                vram_display = f"{vram_kb / 1024 / 1024:.0f} MB"
            except:
                pass
        
        status = "connected" if "connected" in drm_status.lower() else "unknown"
        status_class = "success" if status == "connected" else "warning"
        
        return f"""
        <section id="gpu" class="card">
            <h2>2. GPU状态</h2>
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{util_value}</div>
                    <div class="label">GPU利用率</div>
                </div>
                <div class="stat-box">
                    <div class="value">{vram_display}</div>
                    <div class="label">VRAM使用</div>
                </div>
                <div class="stat-box">
                    <span class="status {status_class}">{status}</span>
                    <div class="label">显示器状态</div>
                </div>
            </div>
            
            <h3>DRM设备列表</h3>
            <pre>{self._escape_html(drm_devices[:1500])}</pre>
            
            <h3>GPU详细信息</h3>
            <table>
                <tr>
                    <th>项目</th>
                    <th>状态</th>
                </tr>
                <tr>
                    <td>VRAM</td>
                    <td>{vram_display}</td>
                </tr>
                <tr>
                    <td>GTT</td>
                    <td>{gpu_gtt.strip() if gpu_gtt != 'N/A' else '不可用'}</td>
                </tr>
                <tr>
                    <td>利用率</td>
                    <td>{gpu_util.strip() if gpu_util != 'N/A' else '不可用'}</td>
                </tr>
            </table>
        </section>
        """
    
    def _generate_compositor_section(self) -> str:
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
    
    def _generate_app_section(self) -> str:
        """生成应用性能部分"""
        app_process = self.data.get("files", {}).get("app_process.txt", "N/A")
        app_status = self.data.get("files", {}).get("app_status.txt", "N/A")
        app_cpu = self.data.get("files", {}).get("app_cpu.txt", "N/A")
        app_memory = self.data.get("files", {}).get("app_memory.txt", "N/A")
        app_threads = self.data.get("files", {}).get("app_threads.txt", "N/A")
        app_smaps = self.data.get("files", {}).get("app_smaps.txt", "N/A")
        app_pid = self.data.get("files", {}).get("app_pid.txt", "N/A").strip()
        
        # 计算线程数
        thread_count = "N/A"
        if app_threads and app_threads != "N/A":
            thread_count = str(len([l for l in app_threads.split('\n') if l]))
        
        # 提取内存信息
        mem_rss = mem_vs = "N/A"
        if app_smaps and app_smaps != "N/A":
            rss_match = re.search(r"Rss:\s+(\d+)\s+kB", app_smaps)
            vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", app_smaps)
            if rss_match:
                mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
            if vs_match:
                mem_vs = f"{int(vs_match.group(1)) / 1024:.0f} MB"
        
        running = app_process != "N/A" and "grep" not in app_process.lower()
        
        return f"""
        <section id="application" class="card">
            <h2>4. 应用性能</h2>
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{"PID: " + app_pid if app_pid and app_pid != "N/A" else "未运行"}</div>
                    <div class="label">进程状态</div>
                </div>
                <div class="stat-box">
                    <div class="value">{thread_count}</div>
                    <div class="label">线程数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_rss}</div>
                    <div class="label">RSS内存</div>
                </div>
                <div class="stat-box">
                    <div class="value">{mem_vs}</div>
                    <div class="label">VSZ内存</div>
                </div>
            </div>
            
            <h3>进程列表</h3>
            <pre>{self._escape_html(app_process[:1500]) if app_process != 'N/A' else '进程未运行'}</pre>
            
            <h3>CPU使用详情</h3>
            <pre>{self._escape_html(app_cpu[:1500]) if app_cpu != 'N/A' else 'N/A'}</pre>
            
            <h3>内存使用详情</h3>
            <pre>{self._escape_html(app_memory[:1500]) if app_memory != 'N/A' else 'N/A'}</pre>
            
            <h3>内存映射概览</h3>
            <pre>{self._escape_html(app_smaps[:1500]) if app_smaps != 'N/A' else 'N/A'}</pre>
        </section>
        """
    
    def _generate_issues_section(self) -> str:
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
    
    def _generate_suggestions_section(self) -> str:
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
            <h2>6. 优化建议</h2>
            {suggestions_html}
            
            <h3>通用优化策略</h3>
            <div class="suggestion">
                <h4>GPU渲染优化</h4>
                <p>针对嵌入式系统的GPU优化建议：</p>
                <ul style="margin: 10px 0 10px 20px;">
                    <li>使用GPU友好的纹理格式（如ETC、ASTC）</li>
                    <li>合并绘制调用，减少draw call数量</li>
                    <li>使用实例化渲染处理大量相似物体</li>
                    <li>启用GPU压缩纹理减少带宽占用</li>
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
    
    def _escape_html(self, text: str) -> str:
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
