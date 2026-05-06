#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰图分析器 - 分析CPU热点和调用栈
"""

import re
from typing import Dict, List, Tuple
from .base import BaseAnalyzer


class FlamegraphAnalyzer(BaseAnalyzer):
    """火焰图数据分析器"""

    def __init__(self, data: Dict):
        super().__init__(data)
        self.hot_functions: List[Tuple[str, float]] = []
        self.graphics_funcs: List[Tuple[str, float]] = []

    def analyze(self) -> None:
        """执行火焰图分析"""
        self._extract_hot_functions()
        self._analyze_graphics_calls()

    def _extract_hot_functions(self) -> None:
        """从perf报告中提取热点函数"""
        perf_report = self.get_file_content("perf_report.txt")
        perf_report_with_stack = self.get_file_content("perf_report_with_stack.txt")

        # 确定使用哪个报告
        source = perf_report
        if not source or source == "N/A" or len(source.strip()) < 100 or \
           "not owned" in source or "采集失败" in source:
            source = perf_report_with_stack

        if not source or source == "N/A" or "采集失败" in source:
            return

        hot_funcs = []
        seen = set()

        for line in source.split('\n'):
            if not line.strip() or line.strip().startswith('#'):
                continue

            # perf report 格式
            match = re.match(
                r'\s*(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+(\S+)\s+\[.\]\s+(\S+)',
                line
            )
            if match:
                pct = float(match.group(1))
                shared_obj = match.group(2).strip()
                symbol = match.group(3).strip()

                if symbol.startswith('0x'):
                    short_addr = symbol[2:10] if len(symbol) > 10 else symbol[2:]
                    func = f"{shared_obj}:0x{short_addr}"
                else:
                    func = symbol

                if func and func != '[unknown]':
                    key = (func, pct)
                    if key not in seen:
                        seen.add(key)
                        hot_funcs.append((func, pct))
                    continue

            # kernel 符号格式
            match2 = re.match(
                r'\s*(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+(\S+)\s+\[k\]\s+(0x\S+)',
                line
            )
            if match2:
                pct = float(match2.group(1))
                shared_obj = match2.group(2).strip()
                addr = match2.group(3).strip()

                if shared_obj == 'kernel.kallsyms':
                    short_addr = addr[-8:] if len(addr) > 8 else addr
                    func = f"[k]0x{short_addr}"
                else:
                    func = shared_obj

                if func:
                    key = (func, pct)
                    if key not in seen:
                        seen.add(key)
                        hot_funcs.append((func, pct))

        self.hot_functions = hot_funcs[:20]

    def _analyze_graphics_calls(self) -> None:
        """分析图形函数调用"""
        func_counts = self.get_file_content("function_counts.txt")
        if not func_counts or func_counts == "N/A" or "N/A" in func_counts:
            return

        high_freq_funcs = []
        graphics_keywords = ['gl', 'egl', 'drm', 'gpu', ' Mesa']

        for line in func_counts.split('\n'):
            match = re.match(r'([gl|egl|drm][\w]+)\s+(\d+)', line, re.IGNORECASE)
            if match:
                func = match.group(1)
                count = int(match.group(2))
                if count > 10000:
                    high_freq_funcs.append((func, count))
                    if any(kw in func.lower() for kw in graphics_keywords):
                        self.graphics_funcs.append((func, count))

        if high_freq_funcs:
            self.add_suggestion(
                "高频图形API调用检测",
                f"检测到 {len(high_freq_funcs)} 个高频调用的图形函数，可能存在冗余调用。",
                f"高频函数: {', '.join([f[0] for f in high_freq_funcs[:5]])}。建议检查调用链，合并相同状态的绘制调用。",
                "api_calls"
            )

    def get_hot_functions_by_category(self) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """按类别获取热点函数"""
        graphics_funcs = []
        general_funcs = []
        graphics_keywords = ['gl', 'egl', 'drm', 'gpu', 'shader', 'texture', 'render',
                           ' Mesa', 'intel', 'i915', 'libgles', 'libsrv', 'pvrsrv']

        for func, pct in self.hot_functions:
            func_lower = func.lower()
            if any(kw in func_lower for kw in graphics_keywords):
                graphics_funcs.append((func, pct))
            else:
                general_funcs.append((func, pct))

        return graphics_funcs, general_funcs

    def get_syscall_counts(self) -> List[Tuple[str, int]]:
        """获取系统调用统计"""
        syscall_content = self.get_file_content("syscall_counts.txt")
        if not syscall_content or syscall_content == "N/A" or "N/A" in syscall_content:
            return []

        counts = []
        for line in syscall_content.split('\n'):
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    syscall = parts[0]
                    count = int(parts[1])
                    if count > 1000:
                        counts.append((syscall, count))
                except ValueError:
                    pass

        return sorted(counts, key=lambda x: x[1], reverse=True)[:10]
