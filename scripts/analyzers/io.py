#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I/O分析器 - 分析磁盘I/O性能
"""

from .base import BaseAnalyzer


class IoAnalyzer(BaseAnalyzer):
    """I/O性能分析器"""

    def analyze(self) -> None:
        """执行I/O分析"""
        self._check_app_io()
        self._check_system_io_wait()
        self._check_iostat()

    def _check_app_io(self) -> None:
        """检查应用I/O统计"""
        io_content = self.get_file_content("app_io.txt")
        if not io_content or io_content == "N/A":
            return

        reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
        writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")

        if reads and writes:
            try:
                reads_kb = int(reads) / 1024
                writes_kb = int(writes) / 1024
                total_io = reads_kb + writes_kb

                if total_io > 100000000:  # 100MB
                    self.add_issue(
                        "warning",
                        "应用程序I/O量较大",
                        f"应用程序I/O总量: {total_io/1024/1024:.2f}MB "
                        f"(读: {reads_kb/1024/1024:.2f}MB, 写: {writes_kb/1024/1024:.2f}MB)"
                    )

                if reads_kb > 1048576 or writes_kb > 1048576:  # 1MB
                    self.add_suggestion(
                        "I/O优化建议",
                        "检测到较大单次I/O操作",
                        "考虑使用批处理、内存缓存或异步I/O减少单次操作大小。"
                    )
            except (ValueError, ZeroDivisionError):
                pass

    def _check_system_io_wait(self) -> None:
        """检查系统I/O等待"""
        vmstat = self.get_file_content("vmstat.txt")
        if not vmstat:
            return

        wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
        if wa and wa > 20:
            self.add_issue(
                "warning",
                "系统I/O等待较高",
                f"I/O等待时间: {wa}%，可能存在I/O瓶颈"
            )
            self.add_suggestion(
                "I/O优化建议",
                "CPU大量时间在等待I/O操作完成",
                "检查磁盘I/O模式，考虑使用更快的存储设备或优化I/O调度策略。"
            )

    def _check_iostat(self) -> None:
        """分析iostat输出"""
        iostat = self.get_file_content("iostat.txt")
        if not iostat or iostat == "N/A":
            return

        lines = iostat.split('\n')
        for line in lines:
            if 'Device' in line or 'sda' in line or 'mmcblk' in line:
                parts = line.split()
                if len(parts) >= 8:
                    device = parts[0]
                    try:
                        util = float(parts[5])  # utilization
                        if util > 80:
                            self.add_suggestion(
                                f"磁盘I/O设备 {device} 负载高",
                                f"设备利用率: {util}%",
                                f"检查 {device} 设备是否为存储瓶颈，考虑升级存储设备或优化文件系统。",
                                "io"
                            )
                    except (ValueError, IndexError):
                        pass

    def score(self) -> float:
        """计算I/O评分"""
        io_score = 100.0
        vmstat = self.get_file_content("vmstat.txt")

        if vmstat:
            wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
            if wa and wa > 30:
                io_score -= (wa - 30) * 2

        return max(0, min(100, io_score))

    def get_io_stats(self) -> dict:
        """获取I/O统计数据"""
        io_content = self.get_file_content("app_io.txt")
        vmstat = self.get_file_content("vmstat.txt")

        stats = {
            "read_bytes": "N/A",
            "write_bytes": "N/A",
            "io_wait": "N/A"
        }

        if io_content and io_content != "N/A":
            reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
            writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")
            if reads:
                stats["read_bytes"] = f"{int(reads)/1024/1024:.2f} MB"
            if writes:
                stats["write_bytes"] = f"{int(writes)/1024/1024:.2f} MB"

        if vmstat:
            wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
            if wa is not None:
                stats["io_wait"] = str(wa)

        return stats
