#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程分析器 - 分析线程状态和锁竞争
"""

from .base import BaseAnalyzer


class ThreadAnalyzer(BaseAnalyzer):
    """线程性能分析器"""

    def analyze(self) -> None:
        """执行线程分析"""
        self._check_thread_states()
        self._check_thread_count()

    def _check_thread_states(self) -> None:
        """检查线程状态分布"""
        content = self.get_file_content("app_threads.txt")
        if not content or content == "N/A":
            return

        lines = content.split('\n')
        thread_states = {'R': 0, 'S': 0, 'D': 0}
        total = 0

        for line in lines:
            if not line.strip() or ' ' not in line:
                continue

            for state in ['R', 'S', 'D']:
                if state in line:
                    thread_states[state] += 1
                    total += 1
                    break

        # 检查不可中断睡眠线程（D状态）
        if thread_states['D'] > 0:
            self.add_issue(
                "error",
                "检测到不可中断睡眠线程",
                f"{thread_states['D']} 个线程处于不可中断状态(D)，可能阻塞在I/O操作"
            )

        # 检查睡眠线程占比
        if total > 0:
            sleep_ratio = thread_states['S'] / total
            if sleep_ratio > 0.9:
                self.add_suggestion(
                    "线程休眠状态优化",
                    "大量线程处于睡眠状态",
                    "考虑使用事件驱动架构或异步IO减少线程数量。",
                    "threads"
                )

    def _check_thread_count(self) -> None:
        """检查线程数量"""
        content = self.get_file_content("app_threads.txt")
        if not content or content == "N/A":
            return

        lines = content.split('\n')
        thread_count = sum(1 for line in lines if line.strip() and ' ' in line) - 1

        if thread_count > 32:
            self.add_suggestion(
                "线程数量优化建议",
                f"当前线程数: {thread_count}",
                "考虑减少线程数量，合理使用线程池，避免线程数量过多导致上下文切换开销。",
                "threads"
            )

    def score(self) -> float:
        """计算线程评分"""
        thread_score = 100.0
        content = self.get_file_content("app_threads.txt")

        if not content or content == "N/A":
            return thread_score

        lines = content.split('\n')
        thread_count = sum(1 for line in lines if line.strip() and ' ' in line) - 1

        if thread_count > 32:
            thread_score -= (thread_count - 32) * 2
        elif thread_count > 16:
            thread_score -= (thread_count - 16)

        return max(0, min(100, thread_score))

    def get_thread_stats(self) -> dict:
        """获取线程统计数据"""
        content = self.get_file_content("app_threads.txt")
        stats = {"total": 0, "running": 0, "sleeping": 0, "uninterruptible": 0}

        if not content or content == "N/A":
            return stats

        lines = content.split('\n')
        thread_count = sum(1 for line in lines if line.strip() and ' ' in line) - 1
        stats["total"] = max(0, thread_count)

        for line in lines:
            for state, key in [('R', 'running'), ('S', 'sleeping'), ('D', 'uninterruptible')]:
                if state in line:
                    stats[key] += 1
                    break

        return stats
