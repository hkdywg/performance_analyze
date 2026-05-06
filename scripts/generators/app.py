#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用性能生成器 - 生成应用性能信息的HTML
"""

import re
from .base import BaseHtmlGenerator


class AppPerformanceGenerator(BaseHtmlGenerator):
    """应用性能HTML生成器"""

    def generate(self) -> str:
        return self._generate_app_section()

    def _generate_app_section(self) -> str:
        """生成应用性能部分"""
        app_process = self.get_file_content("app_process.txt")
        app_cpu = self.get_file_content("app_cpu.txt")
        app_memory = self.get_file_content("app_memory.txt")
        app_threads = self.get_file_content("app_threads.txt")
        app_smaps = self.get_file_content("app_smaps.txt")
        app_status = self.get_file_content("app_status.txt")
        app_pid = self.get_file_content("app_pid.txt").strip() if self.get_file_content("app_pid.txt") != "N/A" else "N/A"

        # 计算线程数
        thread_count = "N/A"
        if app_status and app_status != "N/A":
            threads_match = re.search(r"Threads:\s+(\d+)", app_status)
            if threads_match:
                thread_count = threads_match.group(1)

        # 解析CPU使用率
        app_cpu_raw = str(app_cpu).strip() if app_cpu else "N/A"
        app_cpu_display = app_cpu_raw if app_cpu_raw and app_cpu_raw != "None" else "N/A"
        cpu_pct = "N/A"
        if app_cpu_display != "N/A":
            top_match = re.search(r'\d+\s+\d+\s+\S+\s+\S+\s+\S+\s+([\d.]+)\s+\S+\s+([\d.]+)', app_cpu_display)
            if top_match:
                cpu_pct = f"{top_match.group(2)}%"

        # 提取内存信息
        mem_rss = mem_vs = "N/A"
        mem_pct = "N/A"
        rss_kb = None

        if app_status and app_status != "N/A":
            rss_match = re.search(r"VmRSS:\s+(\d+)\s+kB", app_status)
            vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", app_status)

            if app_smaps and app_smaps != "N/A":
                rss_smaps = re.search(r"Rss:\s+(\d+)\s+kB", app_smaps)
                if rss_smaps:
                    mem_rss = f"{int(rss_smaps.group(1)) / 1024:.0f} MB"
                    rss_kb = int(rss_smaps.group(1))
                elif rss_match:
                    mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
                    rss_kb = int(rss_match.group(1))
            elif rss_match:
                mem_rss = f"{int(rss_match.group(1)) / 1024:.0f} MB"
                rss_kb = int(rss_match.group(1))

            if vs_match:
                mem_vs = f"{int(vs_match.group(1)) / 1024:.0f} MB"

        # 计算内存占比
        if rss_kb:
            mem_info = self.get_file_content("memory.txt")
            if mem_info:
                total_match = re.search(r'Mem:\s+([\d.]+)([KMGT])', mem_info)
                if total_match:
                    total_mem = float(total_match.group(1))
                    unit = total_match.group(2)
                    unit_to_kb = {'K': 1, 'M': 1024, 'G': 1024*1024}
                    total_kb = int(total_mem * unit_to_kb.get(unit, 1024))
                    mem_pct = f"{rss_kb / total_kb * 100:.1f}%"

        running = app_process != "N/A" and "grep" not in app_process.lower()

        return f"""
        <section id="application" class="card">
            <h2>3. 应用性能</h2>

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
