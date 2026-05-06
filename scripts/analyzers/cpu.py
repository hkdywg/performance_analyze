#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPU分析器 - 分析CPU使用率和相关指标
"""

from .base import BaseAnalyzer


class CpuAnalyzer(BaseAnalyzer):
    """CPU性能分析器"""

    def analyze(self) -> None:
        """执行CPU分析"""
        self._check_cpu_usage()
        self._check_cpu_wait()

    def _check_cpu_usage(self) -> None:
        """检查CPU使用率"""
        app_cpu = self.get_file_content("app_cpu.txt")
        if not app_cpu or app_cpu == "N/A":
            return

        # 从top输出获取CPU%
        cpu_values = []
        for line in app_cpu.split('\n'):
            match = self._extract_number(line, r'\d+\.\d+\s+(\d+\.\d+)')
            if match is not None and match > 0:
                cpu_values.append(match)

        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            if avg_cpu > 80:
                self.add_issue(
                    "warning",
                    "应用CPU占用过高",
                    f"平均CPU使用率: {avg_cpu:.1f}%"
                )
                self.add_suggestion(
                    "CPU使用优化",
                    "应用程序CPU占用过高。",
                    "优化渲染逻辑、使用多线程、考虑GPU加速计算。"
                )

    def _check_cpu_wait(self) -> None:
        """检查CPU I/O等待"""
        vmstat = self.get_file_content("vmstat.txt")
        if not vmstat:
            return

        # 从 vmstat 提取 wa 列（第16列）
        wa = self._extract_wa_from_vmstat(vmstat)
        if wa and wa > 30:
            self.add_issue(
                "warning",
                "CPU I/O等待过高",
                f"I/O等待: {wa}%, 可能存在I/O瓶颈"
            )
            self.add_suggestion(
                "I/O性能优化",
                "CPU大量时间在等待I/O操作完成。",
                "检查磁盘I/O模式，考虑使用更快的存储设备或优化I/O调度策略。"
            )

    def score(self) -> float:
        """计算CPU评分"""
        score = 100.0
        app_cpu = self.get_file_content("app_cpu.txt")

        if app_cpu and app_cpu != "N/A":
            cpu_match = self._extract_number(app_cpu, r'\d+\.\d+\s+(\d+\.\d+)')
            if cpu_match:
                if cpu_match > 80:
                    score -= (cpu_match - 80) * 2
                elif cpu_match > 50:
                    score -= (cpu_match - 50)

        return max(0, min(100, score))

    def _extract_wa_from_vmstat(self, vmstat: str):
        """
        从 vmstat 输出中提取 I/O 等待时间百分比 (wa 列)

        vmstat 格式: procs r  b    swpd   free   buff  cache   si   so    bi    bo   in    cs  us  sy  id  wa  st
        wa 是第16列（索引15）
        """
        if not vmstat:
            return None

        lines = vmstat.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
            if line.startswith('procs') or line.startswith('r '):
                continue

            fields = line.split()
            if len(fields) >= 16:
                try:
                    return float(fields[15])
                except (ValueError, IndexError):
                    pass

        return None
