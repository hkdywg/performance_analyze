#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存分析器 - 分析内存使用和泄漏检测
"""

from .base import BaseAnalyzer


class MemoryAnalyzer(BaseAnalyzer):
    """内存性能分析器"""

    def analyze(self) -> None:
        """执行内存分析"""
        self._check_memory_usage()
        self._check_memory_leak()

    def _check_memory_usage(self) -> None:
        """检查内存使用率"""
        mem_content = self.get_file_content("memory.txt")
        if not mem_content or mem_content == "N/A":
            return

        # 解析内存信息
        total = self._extract_value(mem_content, r"Mem:\s+(\d+)")
        available = self._extract_value(mem_content, r"Mem:\s+\d+\s+(\d+)")

        if total and available:
            try:
                total_mb = int(total) / 1024
                avail_mb = int(available) / 1024
                used_pct = (1 - int(available) / int(total)) * 100

                if used_pct > 90:
                    self.add_issue(
                        "error",
                        "内存使用率过高",
                        f"当前内存使用率: {used_pct:.1f}%, 可用内存: {avail_mb:.0f}MB"
                    )
                    self.add_suggestion(
                        "内存优化建议",
                        "当前内存使用率过高，可能导致系统性能下降。",
                        "检查并优化应用程序内存使用，考虑增加内存或优化内存分配策略。"
                    )
                elif used_pct > 75:
                    self.add_issue(
                        "warning",
                        "内存使用率偏高",
                        f"当前内存使用率: {used_pct:.1f}%"
                    )
            except (ValueError, ZeroDivisionError):
                pass

    def _check_memory_leak(self) -> None:
        """检查内存泄漏"""
        app_smaps = self.get_file_content("app_smaps.txt")
        if not app_smaps:
            return

        rss = self._extract_value(app_smaps, r"Rss:\s+(\d+)\s+kB")
        if rss:
            rss_mb = int(rss) / 1024
            if rss_mb > 500:
                self.add_suggestion(
                    "内存使用监控",
                    f"应用RSS内存: {rss_mb:.0f}MB",
                    "持续监控内存使用趋势，检测可能的内存泄漏。"
                )

    def score(self) -> float:
        """计算内存评分"""
        mem_score = 100.0
        mem_content = self.get_file_content("memory.txt")

        if not mem_content or mem_content == "N/A":
            return mem_score

        total = self._extract_value(mem_content, r"Mem:\s+(\d+)")
        available = self._extract_value(mem_content, r"Mem:\s+\d+\s+(\d+)")

        if total and available:
            try:
                total_kb = int(total)
                avail_kb = int(available)
                used_pct = (1 - avail_kb / total_kb) * 100

                if used_pct > 90:
                    mem_score -= (used_pct - 90) * 3
                elif used_pct > 75:
                    mem_score -= (used_pct - 75) * 1.5
                elif used_pct > 60:
                    mem_score -= (used_pct - 60)
            except (ValueError, ZeroDivisionError):
                pass

        return max(0, min(100, mem_score))
