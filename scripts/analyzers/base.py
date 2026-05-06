#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能分析器基类 - 提供基础的数据分析和评分功能
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any


class BaseAnalyzer(ABC):
    """性能分析器基类"""

    def __init__(self, data: Dict):
        """
        初始化分析器

        Args:
            data: 包含所有采集数据的字典
        """
        self.data = data
        self.issues: List[Dict] = []
        self.suggestions: List[Dict] = []

    def get_file_content(self, filename: str) -> str:
        """获取数据文件内容"""
        return self.data.get("files", {}).get(filename, "N/A")

    @abstractmethod
    def analyze(self) -> None:
        """执行分析 - 子类必须实现"""
        pass

    def _extract_value(self, text: str, pattern: str) -> Optional[str]:
        """从文本中提取值"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_number(self, text: str, pattern: str) -> Optional[float]:
        """提取数值"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                return None
        return None

    def _escape_html(self, text: str) -> str:
        """HTML转义"""
        if not text:
            return ""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

    def add_issue(self, severity: str, title: str, detail: str = "") -> None:
        """添加问题"""
        self.issues.append({
            "severity": severity,
            "title": title,
            "detail": detail
        })

    def add_suggestion(self, title: str, content: str = "", action: str = "",
                       category: str = "") -> None:
        """添加建议"""
        suggestion = {"title": title}
        if content:
            suggestion["content"] = content
        if action:
            suggestion["action"] = action
        if category:
            suggestion["category"] = category
        self.suggestions.append(suggestion)


class ScoringMixin:
    """评分混合类 - 提供性能评分功能"""

    def _calculate_base_score(self, value: float, thresholds: Dict[str, float],
                             weight: float = 1.0) -> float:
        """
        计算基础分数

        Args:
            value: 当前值
            thresholds: 阈值字典，如 {"critical": 80, "warning": 50}
            weight: 权重系数

        Returns:
            分数 (0-100)
        """
        score = 100.0

        critical = thresholds.get("critical", 100)
        warning = thresholds.get("warning", 50)

        if value >= critical:
            score -= (value - critical) * 3 * weight
        elif value >= warning:
            score -= (value - warning) * 1.5 * weight
        elif value >= warning * 0.8:
            score -= (value - warning * 0.8) * weight

        return max(0, min(100, score))

    def _get_score_status(self, score: float) -> Tuple[str, str]:
        """
        根据分数获取状态和描述

        Returns:
            (status_class, status_text)
        """
        if score >= 90:
            return "normal", "优秀"
        elif score >= 70:
            return "warning", "良好"
        elif score >= 50:
            return "warning", "需关注"
        else:
            return "error", "较差"


class DataParserMixin:
    """数据解析混合类 - 提供通用的数据解析方法"""

    def parse_memory_info(self, mem_content: str) -> Dict[str, Any]:
        """
        解析内存信息

        Returns:
            {"total": "X GB", "used": "X GB", "available": "X GB", "used_pct": XX.X}
        """
        result = {"total": "N/A", "used": "N/A", "available": "N/A", "used_pct": 0}

        # 尝试解析 free -h 输出 (如: 863.4M, 1.2G)
        mem_match_h = re.search(r"Mem:\s+([\d.]+)([KMGT]?i?\s)", mem_content)
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
            result["total"] = f"{total_gb:.1f} GB"

            # 解析已用和可用
            used_match = re.search(r"Mem:\s+[\d.]+[KMGT]?\s+([\d.]+)([KMGT]?)", mem_content)
            if used_match:
                used_val = float(used_match.group(1))
                used_unit = used_match.group(2)
                if 'G' in used_unit.upper():
                    result["used"] = f"{used_val:.1f} GB"
                elif 'M' in used_unit.upper():
                    result["used"] = f"{used_val:.0f} MB"
            return result

        # 尝试解析 free 输出 (纯数字，单位为KB)
        mem_match = re.search(r"Mem:\s+(\d+)\s+(\d+)", mem_content)
        if mem_match:
            total_kb = int(mem_match.group(1))
            used_kb = int(mem_match.group(2))
            result["total"] = f"{total_kb / 1024 / 1024:.1f} GB"
            result["used"] = f"{used_kb / 1024 / 1024:.1f} GB"
            result["used_pct"] = (used_kb / total_kb) * 100
        return result

    def parse_cpu_from_top(self, top_content: str) -> Dict[str, Any]:
        """
        从top输出解析CPU信息

        Returns:
            {"cpu_pct": "XX.X", "pid": "XXX", "cmd": "..."}
        """
        result = {"cpu_pct": "N/A", "pid": "N/A", "cmd": "N/A"}

        # 解析 top 输出格式: PID USER S VIRT RES SHR CPU% COMMAND
        # 示例: " 3198   309 root     S     626m 72.4   1 14.2 ./kanzi"
        match = re.search(
            r'\s*(\d+)\s+\d+\s+\S+\s+\S+\s+\S+\s+([\d.]+)\s+\S+\s+([\d.]+)\s+(.+)',
            top_content
        )
        if match:
            result["pid"] = match.group(1)
            result["cpu_pct"] = f"{float(match.group(3)):.1f}"
            result["cmd"] = match.group(4).strip()

        return result

    def parse_thread_info(self, status_content: str) -> Dict[str, Any]:
        """
        解析进程状态信息

        Returns:
            {"threads": "XX", "vmrss": "XXX MB", "vmsize": "XXX MB", "state": "..."}
        """
        result = {"threads": "N/A", "vmrss": "N/A", "vmsize": "N/A", "state": "N/A"}

        # 解析线程数
        threads_match = re.search(r"Threads:\s+(\d+)", status_content)
        if threads_match:
            result["threads"] = threads_match.group(1)

        # 解析VmRSS
        rss_match = re.search(r"VmRSS:\s+(\d+)\s+kB", status_content)
        if rss_match:
            result["vmrss"] = f"{int(rss_match.group(1)) / 1024:.0f} MB"

        # 解析VmSize
        vs_match = re.search(r"VmSize:\s+(\d+)\s+kB", status_content)
        if vs_match:
            result["vmsize"] = f"{int(vs_match.group(1)) / 1024:.0f} MB"

        # 解析状态
        state_match = re.search(r"State:\s+(\S+)", status_content)
        if state_match:
            result["state"] = state_match.group(1)

        return result
