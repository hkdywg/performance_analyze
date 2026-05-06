#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统调用分析器 - 分析系统调用频率和模式
"""

from .base import BaseAnalyzer


class SyscallAnalyzer(BaseAnalyzer):
    """系统调用分析器"""

    def analyze(self) -> None:
        """执行系统调用分析"""
        self._check_syscall_frequency()
        self._check_blocking_calls()

    def _check_syscall_frequency(self) -> None:
        """检查高频系统调用"""
        content = self.get_file_content("syscall_counts.txt")
        if not content or content == "N/A":
            return

        blocking_calls = ['read', 'write', 'poll', 'select', 'epoll',
                        'open', 'close', 'mmap']
        high_freq_calls = []

        for line in content.split('\n'):
            if not line.strip() or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) >= 2:
                syscall = parts[0]
                try:
                    count = int(parts[1])
                    if count > 1000:
                        high_freq_calls.append((syscall, count))
                except ValueError:
                    pass

        if high_freq_calls:
            blocking_calls_high = [(s, c) for s, c in high_freq_calls if s in blocking_calls]
            if blocking_calls_high:
                self.add_suggestion(
                    "系统调用优化建议",
                    f"检测到高频阻塞调用: {', '.join([f'{s}({c})' for s, c in blocking_calls_high[:5]])}",
                    "考虑使用批处理、缓存或异步IO减少系统调用次数。",
                    "syscall"
                )

            file_ops = [(s, c) for s, c in high_freq_calls if s in ['read', 'write', 'open', 'close']]
            if file_ops:
                self.add_suggestion(
                    "文件操作优化",
                    f"高频文件操作: {', '.join([f'{s}({c})' for s, c in file_ops[:3]])}",
                    "考虑使用内存文件系统、预读或文件缓存优化文件访问。",
                    "file_io"
                )

    def _check_blocking_calls(self) -> None:
        """检查阻塞调用"""
        content = self.get_file_content("syscall_counts.txt")
        if not content or content == "N/A":
            return

        blocking_keywords = ['ioctl', 'read', 'write', 'poll', 'select', 'epoll']
        high_count = []

        for line in content.split('\n'):
            if any(call in line.lower() for call in blocking_keywords):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        count = int(parts[-1])
                        syscall = parts[0] if len(parts) > 1 else ""
                        if count > 1000:
                            high_count.append((syscall, count))
                    except ValueError:
                        pass

        if high_count:
            self.add_suggestion(
                "系统调用优化建议",
                f"检测到频繁的系统调用: {', '.join([f'{s[0]}({s[1]})' for s in high_count[:3]])}",
                "考虑使用批处理、缓存或异步IO减少系统调用次数。",
                "syscall"
            )
