#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能趋势图表生成器 - 生成CPU/内存趋势图的HTML
"""

import json
import re
from .base import BaseHtmlGenerator


class ChartGenerator(BaseHtmlGenerator):
    """性能趋势图表生成器"""

    def generate(self) -> str:
        perf_samples = self.get_file_content("perf_samples.csv")

        if perf_samples == "N/A" or not perf_samples.strip():
            return self._generate_from_fallback()

        return self._generate_from_csv(perf_samples)

    def _generate_from_csv(self, perf_samples: str) -> str:
        """从CSV数据生成图表"""
        lines = perf_samples.strip().split('\n')
        if len(lines) < 2:
            return self._generate_from_fallback()

        time_data = []
        app_cpu_data = []
        app_rss_data = []
        app_vsz_data = []
        valid_data_count = 0

        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 4:
                time_data.append(parts[0])

                cpu_val = parts[1].strip()
                if cpu_val == "N/A" or cpu_val == "" or cpu_val == "0":
                    app_cpu_data.append(None)
                else:
                    try:
                        app_cpu_data.append(float(cpu_val))
                        valid_data_count += 1
                    except ValueError:
                        app_cpu_data.append(None)

                rss_val = parts[2].strip()
                if rss_val == "N/A" or rss_val == "":
                    app_rss_data.append(None)
                else:
                    try:
                        rss_clean = rss_val.lower().replace('m', '').replace('k', '')
                        app_rss_data.append(float(rss_clean))
                        valid_data_count += 1
                    except ValueError:
                        app_rss_data.append(None)

                vsz_val = parts[3].strip()
                if vsz_val == "N/A" or vsz_val == "":
                    app_vsz_data.append(None)
                else:
                    try:
                        vsz_clean = vsz_val.lower().replace('m', '').replace('k', '')
                        app_vsz_data.append(float(vsz_clean))
                        valid_data_count += 1
                    except ValueError:
                        app_vsz_data.append(None)

        if valid_data_count == 0:
            return self._generate_from_fallback()

        max_mem = max(
            max((v for v in app_rss_data if v is not None), default=0),
            max((v for v in app_vsz_data if v is not None), default=0)
        )
        max_mem = max_mem * 1.1 if max_mem > 0 else 100

        return f"""
        <section id="perf-chart" class="card">
            <h2>5. 性能趋势</h2>

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

    def _generate_from_fallback(self) -> str:
        """从备用数据源生成图表"""
        app_cpu = self.get_file_content("app_cpu.txt")
        app_status = self.get_file_content("app_status.txt")

        time_data = []
        app_cpu_data = []
        app_rss_data = []
        app_vsz_data = []

        if app_status and app_status != "N/A" and app_status.strip():
            rss_match = re.search(r"VmRSS:\s+(\d+)\s+kB", app_status)
            vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", app_status)

            if rss_match:
                app_rss_data = [float(rss_match.group(1)) / 1024]
                time_data = ["0"]

            if vs_match:
                app_vsz_data = [float(vs_match.group(1)) / 1024]
                if not time_data:
                    time_data = ["0"]

        if app_cpu and app_cpu != "N/A" and app_cpu.strip():
            match = re.match(
                r'\s*(\d+)\s+\d+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)',
                app_cpu.strip().split('\n')[0]
            )
            if match:
                time_data = ["0"]
                try:
                    app_cpu_data.append(float(match.group(2)))
                except ValueError:
                    app_cpu_data.append(None)

        has_cpu = any(v is not None for v in app_cpu_data)
        has_rss = any(v is not None for v in app_rss_data)
        has_vsz = any(v is not None for v in app_vsz_data)

        if not has_cpu and not has_rss and not has_vsz:
            return """
        <section id="perf-chart" class="card">
            <h2>4. 性能趋势</h2>
            <div class="no-data">暂无性能数据，请运行采集脚本获取数据</div>
        </section>
            """

        max_mem = 100
        valid_rss = [v for v in app_rss_data if v is not None]
        valid_vsz = [v for v in app_vsz_data if v is not None]
        if valid_rss:
            max_mem = max(max_mem, max(valid_rss) * 1.2)
        if valid_vsz:
            max_mem = max(max_mem, max(valid_vsz) * 1.2)

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
            <h2>4. 性能趋势</h2>
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
