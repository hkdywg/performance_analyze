#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能报告生成器 - 主入口

协调分析器和HTML生成器生成完整的HTML报告。

使用方式:
    python3 report_generator.py -d ./report
    python3 report_generator.py --data-dir ./report --output report.html
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 添加scripts目录到路径（支持从scripts目录或父目录运行）
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from templates import HTML_HEADER, HTML_FOOTER, CHART_JS_SCRIPT, STACK_TOGGLE_SCRIPT
from scripts.analyzers import (
    CpuAnalyzer, MemoryAnalyzer, IoAnalyzer, ThreadAnalyzer,
    NetworkAnalyzer, GraphicsAnalyzer, FlamegraphAnalyzer, SyscallAnalyzer,
    ProcessStatAnalyzer
)
from scripts.generators import (
    SystemOverviewGenerator, AppPerformanceGenerator, CompositorGenerator,
    ChartGenerator, FlamegraphGenerator, ScoreGenerator,
    IoAnalysisGenerator, LockAnalysisGenerator, ProcStatGenerator
)


class PerformanceReportGenerator:
    """性能报告生成器主类"""

    def __init__(self, data_dir: str, output_path: str = None):
        """
        初始化报告生成器

        Args:
            data_dir: 数据目录路径
            output_path: 输出HTML文件路径
        """
        self.data_dir = Path(data_dir)
        self.output_path = output_path or str(self.data_dir / "report.html")
        self.data: Dict = {}
        self.issues: List = []
        self.suggestions: List = []
        self.scores: Dict[str, float] = {}

    def load_data(self) -> bool:
        """加载数据文件"""
        print(f"从 {self.data_dir} 加载数据...")

        # 查找JSON汇总文件
        json_files = list(self.data_dir.glob("remote_data_*.json"))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            # 重新加载所有数据文件
            self._load_all_data_files()
        else:
            # 加载所有txt文件
            self._load_text_files()

        return bool(self.data)

    def _load_all_data_files(self):
        """重新加载所有数据文件"""
        self.data.setdefault("files", {})

        # 加载所有txt文件
        for txt_file in self.data_dir.glob("*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][txt_file.name] = f.read()
            except Exception as e:
                print(f"读取 {txt_file.name} 失败: {e}")

        # 加载CSV文件
        for csv_file in self.data_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][csv_file.name] = f.read()
            except Exception as e:
                print(f"读取 {csv_file.name} 失败: {e}")

        # 加载SVG文件
        for svg_file in self.data_dir.glob("*.svg"):
            try:
                with open(svg_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.data["files"][svg_file.name] = f.read()
            except Exception as e:
                print(f"读取 {svg_file.name} 失败: {e}")

    def _load_text_files(self):
        """从文本文件加载数据"""
        self.data = {"files": {}}

        for pattern in ["*.txt", "*.csv", "*.svg", "*.json"]:
            for data_file in self.data_dir.glob(pattern):
                try:
                    with open(data_file, 'r', encoding='utf-8', errors='ignore') as f:
                        self.data["files"][data_file.name] = f.read()
                except Exception as e:
                    print(f"读取 {data_file.name} 失败: {e}")

    def analyze(self):
        """执行性能分析"""
        print("开始性能分析...")

        # CPU分析
        cpu_analyzer = CpuAnalyzer(self.data)
        cpu_analyzer.analyze()
        self.issues.extend(cpu_analyzer.issues)
        self.suggestions.extend(cpu_analyzer.suggestions)
        self.scores['CPU'] = cpu_analyzer.score()

        # 内存分析
        memory_analyzer = MemoryAnalyzer(self.data)
        memory_analyzer.analyze()
        self.issues.extend(memory_analyzer.issues)
        self.suggestions.extend(memory_analyzer.suggestions)
        self.scores['Memory'] = memory_analyzer.score()

        # I/O分析
        io_analyzer = IoAnalyzer(self.data)
        io_analyzer.analyze()
        self.issues.extend(io_analyzer.issues)
        self.suggestions.extend(io_analyzer.suggestions)
        self.scores['I/O'] = io_analyzer.score()

        # 线程分析
        thread_analyzer = ThreadAnalyzer(self.data)
        thread_analyzer.analyze()
        self.issues.extend(thread_analyzer.issues)
        self.suggestions.extend(thread_analyzer.suggestions)
        self.scores['Threads'] = thread_analyzer.score()

        # 图形学分析
        graphics_analyzer = GraphicsAnalyzer(self.data)
        graphics_analyzer.analyze()
        self.issues.extend(graphics_analyzer.issues)
        self.suggestions.extend(graphics_analyzer.suggestions)
        self.scores['Graphics'] = graphics_analyzer.score()

        # 火焰图分析
        flame_analyzer = FlamegraphAnalyzer(self.data)
        flame_analyzer.analyze()
        self.issues.extend(flame_analyzer.issues)
        self.suggestions.extend(flame_analyzer.suggestions)

        # 系统调用分析
        syscall_analyzer = SyscallAnalyzer(self.data)
        syscall_analyzer.analyze()
        self.issues.extend(syscall_analyzer.issues)
        self.suggestions.extend(syscall_analyzer.suggestions)

        # 进程stat分析
        proc_stat_analyzer = ProcessStatAnalyzer(self.data)
        proc_stat_analyzer.analyze()
        self.issues.extend(proc_stat_analyzer.issues)
        self.suggestions.extend(proc_stat_analyzer.suggestions)
        self.scores['ProcStat'] = proc_stat_analyzer.score()

        print(f"分析完成: 发现 {len(self.issues)} 个问题, {len(self.suggestions)} 条建议")

    def _calculate_total_score(self) -> float:
        """计算总评分"""
        score = 100.0

        weights = {
            'CPU': 0.2,
            'Memory': 0.2,
            'I/O': 0.15,
            'Threads': 0.1,
            'Graphics': 0.15
        }

        for key, weight in weights.items():
            if key in self.scores:
                score -= (100 - self.scores[key]) * weight

        return max(0, min(100, score))

    def _identify_bottleneck(self) -> str:
        """识别主要瓶颈"""
        if not self.scores:
            return "无明显瓶颈"

        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1])
        return sorted_scores[0][0] if sorted_scores[0][1] < 80 else "无明显瓶颈"

    def generate_html(self) -> str:
        """生成完整HTML报告"""
        print("生成HTML报告...")

        title = self.data.get("app_name", "性能分析报告")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = HTML_HEADER.format(title=title)

        # 生成各部分内容
        html += self._generate_header()
        html += self._generate_nav()

        # 系统概览
        gen = SystemOverviewGenerator(self.data, [], [])
        html += gen.generate()

        # Compositor状态
        # gen = CompositorGenerator(self.data, [], [])
        # html += gen.generate()

        # 应用性能
        gen = AppPerformanceGenerator(self.data, [], [])
        html += gen.generate()

        # 问题诊断
        # gen = SystemOverviewGenerator(self.data, self.issues, self.suggestions)
        # html += gen.generate_issues_section()

        # 性能趋势图表
        gen = ChartGenerator(self.data, [], [])
        html += gen.generate()

        # 火焰图分析
        gen = FlamegraphGenerator(self.data, [], [])
        html += gen.generate()

        # I/O分析
        gen = IoAnalysisGenerator(self.data, [], [])
        html += gen.generate()

        # 锁分析
        gen = LockAnalysisGenerator(self.data, [], [])
        html += gen.generate()

        # 进程stat信息
        gen = ProcStatGenerator(self.data, [], [])
        html += gen.generate()

        # 性能评分
        total_score = self._calculate_total_score()
        bottleneck = self._identify_bottleneck()
        gen = ScoreGenerator(self.data, self.issues, self.suggestions,
                            self.scores, total_score, bottleneck)
        html += gen.generate()

        # 优化建议
        # html += gen.generate_suggestions_section()

        # JavaScript脚本
        html += CHART_JS_SCRIPT
        html += STACK_TOGGLE_SCRIPT

        # 页脚
        html += HTML_FOOTER.format(timestamp=timestamp)

        return html

    def _generate_header(self) -> str:
        """生成报告头部"""
        app_name = self.data.get("app_name", "未知")
        host = self.data.get("ssh_host", "未知")
        server = self.data.get("display_server", "未知")
        compositor = self.data.get("compositor", "未知")

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        return f"""
        <div class="header">
            <h1>AR-HUD应用程序性能分析报告</h1>
            <div class="meta">
                <div class="meta-item">主机: {host}</div>
                <div class="meta-item">应用: {app_name}</div>
                <div class="meta-item">时间: {timestamp}</div>
            </div>
        </div>
        """

    def _generate_nav(self) -> str:
        """生成导航栏"""
        return """
        <nav class="nav">
            <ul>
                <li><a href="#overview">系统概览</a></li>
                <li><a href="#application">应用基础信息</a></li>
                <li><a href="#perf-chart">性能趋势</a></li>
                <li><a href="#flamegraph">火焰图与热点分析</a></li>
                <li><a href="#io-analysis">I/O性能</a></li>
                <li><a href="#lock-analysis">锁分析</a></li>
                <li><a href="#proc-stat">进程Stat详情</a></li>
                <li><a href="#suggestions">性能综合评估</a></li>
            </ul>
        </nav>
        """

    def save_report(self, html: str):
        """保存报告到文件"""
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"报告已保存到: {output_path}")

    def generate(self):
        """生成完整报告"""
        if not self.load_data():
            print("错误: 无法加载数据")
            return False

        self.analyze()

        html = self.generate_html()
        self.save_report(html)

        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='图形显示应用程序性能分析报告生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-d', '--data-dir',
        default='./report',
        help='数据目录路径 (默认: ./report)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='输出HTML文件路径 (默认: <data-dir>/report.html)'
    )
    parser.add_argument(
        '--no-open',
        action='store_true',
        help='生成后不自动打开报告'
    )

    args = parser.parse_args()

    # 创建生成器并生成报告
    generator = PerformanceReportGenerator(args.data_dir, args.output)
    success = generator.generate()

    if success and not args.no_open:
        # 尝试使用默认浏览器打开报告
        report_path = Path(generator.output_path)
        if report_path.exists():
            try:
                import webbrowser
                webbrowser.open(str(report_path.absolute()))
            except Exception:
                pass

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
