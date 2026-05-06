#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统概览生成器 - 生成系统信息的HTML
"""

import re
from .base import BaseHtmlGenerator


class SystemOverviewGenerator(BaseHtmlGenerator):
    """系统概览HTML生成器"""

    def generate(self) -> str:
        return self._generate_system_overview()

    def _generate_system_overview(self) -> str:
        """生成系统概览部分"""
        os_release = self.get_file_content("os_release.txt")
        uname = self.get_file_content("uname.txt")
        nproc = self.get_file_content("nproc.txt")
        memory = self.get_file_content("memory.txt")

        cpu_count = nproc.strip() if nproc != "N/A" else "N/A"

        # 解析内存信息
        mem_total = mem_used = "N/A"
        mem_match_h = re.search(r"Mem:\s+([\d.]+)([KMGT]?i?\s)", memory)
        if mem_match_h:
            total_val = float(mem_match_h.group(1))
            total_unit = mem_match_h.group(2).strip()
            if 'T' in total_unit.upper():
                total_gb = total_val * 1024
            elif 'G' in total_unit.upper():
                total_gb = total_val
            elif 'M' in total_unit.upper():
                total_gb = total_val / 1024
            else:
                total_gb = total_val / 1024 / 1024
            mem_total = f"{total_gb:.1f} GB"

            used_match = re.search(r"Mem:\s+[\d.]+[KMGT]?\s+([\d.]+)([KMGT]?)", memory)
            if used_match:
                used_val = float(used_match.group(1))
                used_unit = used_match.group(2)
                if 'G' in used_unit.upper():
                    mem_used = f"{used_val:.1f} GB"
                elif 'M' in used_unit.upper():
                    mem_used = f"{used_val:.0f} MB"
        else:
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
