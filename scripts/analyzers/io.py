#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I/O分析器 - 分析磁盘I/O性能

支持:
- 解析 /proc/{pid}/io 累计数据
- 解析采样CSV中的IO速率数据
- 计算IO吞吐率和操作频率
- 检测IO异常模式
"""

import re
from typing import Dict, List, Optional, Tuple
from .base import BaseAnalyzer


class IoAnalyzer(BaseAnalyzer):
    """I/O性能分析器"""

    def analyze(self) -> None:
        """执行I/O分析"""
        self._check_app_io()
        self._check_system_io_wait()
        self._check_iostat()
        self._analyze_io_samples()
        self._check_io_operations()

    def _check_app_io(self) -> None:
        """检查应用I/O统计（累计值）"""
        io_content = self.get_file_content("app_io.txt")
        if not io_content or io_content == "N/A":
            return

        reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
        writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")
        syscr = self._extract_value(io_content, r"syscr:\s+(\d+)")  # 读系统调用次数
        syscw = self._extract_value(io_content, r"syscw:\s+(\d+)")  # 写系统调用次数
        cancelled = self._extract_value(io_content, r"cancelled_write_bytes:\s+(\d+)")

        if reads and writes:
            try:
                reads_kb = int(reads) / 1024
                writes_kb = int(writes) / 1024
                total_io = reads_kb + writes_kb

                if total_io > 100000:  # 100MB
                    self.add_issue(
                        "warning",
                        "应用程序I/O量较大",
                        f"应用程序I/O总量: {total_io/1024:.2f}MB "
                        f"(读: {reads_kb/1024:.2f}MB, 写: {writes_kb/1024:.2f}MB)"
                    )

                # 检查读写比例
                if writes_kb > 0:
                    rw_ratio = reads_kb / writes_kb
                    if rw_ratio < 0.1:
                        self.add_suggestion(
                            "读写比例分析",
                            f"写操作远大于读操作 (读/写={rw_ratio:.2f})",
                            "写入量远大于读取量，可能存在频繁写日志或缓存同步操作。考虑优化写入策略。",
                            "io"
                        )

                # 检查取消的写入
                if cancelled:
                    cancelled_kb = int(cancelled) / 1024
                    if cancelled_kb > writes_kb * 0.5:
                        self.add_issue(
                            "warning",
                            "大量写入被取消",
                            f"取消的写入字节: {cancelled_kb:.2f}KB，占总写入的较大比例"
                        )
            except (ValueError, ZeroDivisionError):
                pass

        # 系统调用次数分析
        if syscr and syscw:
            try:
                total_syscalls = int(syscr) + int(syscw)
                if total_syscalls > 100000:
                    self.add_suggestion(
                        "I/O系统调用频繁",
                        f"总I/O系统调用次数: {total_syscalls:,}",
                        "考虑使用缓冲I/O、合并写操作或异步I/O减少系统调用次数。",
                        "io"
                    )
            except ValueError:
                pass

    def _check_system_io_wait(self) -> None:
        """检查系统I/O等待"""
        vmstat = self.get_file_content("vmstat.txt")
        if not vmstat:
            return

        wa = self._extract_wa_from_vmstat(vmstat)
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
            if 'Device' in line or 'sda' in line or 'mmcblk' in line or 'nvme' in line:
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

    def _analyze_io_samples(self) -> None:
        """分析采样CSV中的IO数据"""
        csv_content = self.get_file_content("io_samples.csv")
        if not csv_content or csv_content == "N/A":
            csv_content = self.get_file_content("perf_samples.csv")
        if not csv_content or csv_content == "N/A":
            return

        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return

        # 检查是否有IO列
        header = lines[0]
        if '读IO' not in header and 'read_rate' not in header.lower():
            return

        read_rates = []
        write_rates = []
        syscr_diffs = []  # 读系统调用差值
        syscw_diffs = []  # 写系统调用差值
        times = []

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 6:
                try:
                    time = float(parts[0])
                    # IO速率在第5和第6列
                    read_rate = parts[4] if len(parts) > 4 else 'N/A'
                    write_rate = parts[5] if len(parts) > 5 else 'N/A'

                    if read_rate != 'N/A' and read_rate != '':
                        read_rates.append(float(read_rate))
                    if write_rate != 'N/A' and write_rate != '':
                        write_rates.append(float(write_rate))
                    times.append(time)
                    
                    # 解析IO系统调用差值 (在第9和第10列)
                    if len(parts) >= 10:
                        syscr_diff = parts[8] if len(parts) > 8 else 'N/A'
                        syscw_diff = parts[9] if len(parts) > 9 else 'N/A'
                        if syscr_diff != 'N/A' and syscr_diff != '':
                            syscr_diffs.append(int(syscr_diff))
                        if syscw_diff != 'N/A' and syscw_diff != '':
                            syscw_diffs.append(int(syscw_diff))
                except (ValueError, IndexError):
                    continue

        if not read_rates and not write_rates:
            return

        # 计算统计信息
        if read_rates:
            avg_read = sum(read_rates) / len(read_rates)
            max_read = max(read_rates)
            peak_read = sorted(read_rates, reverse=True)[:3]  # Top 3峰值

            if max_read > 10000:  # > 10MB/s
                self.add_issue(
                    "warning",
                    "检测到高I/O读取峰值",
                    f"最大读取速率: {max_read/1024:.2f}MB/s，平均: {avg_read/1024:.2f}MB/s"
                )

            # 检查IO抖动
            if len(read_rates) > 5:
                variance = sum((x - avg_read) ** 2 for x in read_rates) / len(read_rates)
                std_dev = variance ** 0.5
                if std_dev > avg_read * 2 and avg_read > 100:
                    self.add_suggestion(
                        "I/O读取不稳定",
                        f"读取速率波动大 (标准差={std_dev/1024:.2f}MB/s)",
                        "I/O模式不稳定，可能存在频繁的缓存刷新或批量读写操作。",
                        "io"
                    )

        if write_rates:
            avg_write = sum(write_rates) / len(write_rates)
            max_write = max(write_rates)

            if max_write > 5000:  # > 5MB/s
                self.add_issue(
                    "warning",
                    "检测到高I/O写入",
                    f"最大写入速率: {max_write/1024:.2f}MB/s，平均: {avg_write/1024:.2f}MB/s"
                )
        
        # 分析IO系统调用差值
        if syscr_diffs:
            total_syscr_diff = sum(syscr_diffs)
            max_syscr_diff = max(syscr_diffs)
            avg_syscr_diff = total_syscr_diff / len(syscr_diffs) if syscr_diffs else 0
            
            if total_syscr_diff > 10000:
                self.add_suggestion(
                    "采样期间读系统调用频繁",
                    f"采样期间总读系统调用次数: {total_syscr_diff:,}, 平均每次采样: {avg_syscr_diff:.1f}",
                    "考虑使用缓冲I/O减少系统调用次数，或合并多次小读操作为一次大读操作。",
                    "io"
                )
        
        if syscw_diffs:
            total_syscw_diff = sum(syscw_diffs)
            max_syscw_diff = max(syscw_diffs)
            avg_syscw_diff = total_syscw_diff / len(syscw_diffs) if syscw_diffs else 0
            
            if total_syscw_diff > 10000:
                self.add_suggestion(
                    "采样期间写系统调用频繁",
                    f"采样期间总写系统调用次数: {total_syscw_diff:,}, 平均每次采样: {avg_syscw_diff:.1f}",
                    "考虑使用缓冲写、批量写入或延迟写策略减少系统调用次数。",
                    "io"
                )

    def _check_io_operations(self) -> None:
        """检查IO操作模式"""
        io_content = self.get_file_content("app_io.txt")
        if not io_content or io_content == "N/A":
            return

        syscr = self._extract_value(io_content, r"syscr:\s+(\d+)")
        syscw = self._extract_value(io_content, r"syscw:\s+(\d+)")
        reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
        writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")

        if syscr and reads:
            try:
                read_size = int(reads) / max(1, int(syscr))  # 每次读的大小
                if read_size > 1024 * 1024:  # > 1MB per read
                    self.add_suggestion(
                        "大块读操作",
                        f"平均每次读操作大小: {read_size/1024/1024:.2f}MB",
                        "大块读取可能导致I/O阻塞，考虑分批读取或使用直接I/O。",
                        "io"
                    )
            except (ValueError, ZeroDivisionError):
                pass

        if syscw and writes:
            try:
                write_size = int(writes) / max(1, int(syscw))  # 每次写的大小
                if write_size > 512 * 1024:  # > 512KB per write
                    self.add_suggestion(
                        "大块写操作",
                        f"平均每次写操作大小: {write_size/1024:.2f}KB",
                        "考虑使用缓冲写、批量写入或延迟写策略优化写入性能。",
                        "io"
                    )
            except (ValueError, ZeroDivisionError):
                pass

    def score(self) -> float:
        """计算I/O评分"""
        io_score = 100.0

        # 基于vmstat的IO等待评分
        vmstat = self.get_file_content("vmstat.txt")
        if vmstat:
            wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
            if wa and wa > 30:
                io_score -= (wa - 30) * 2
            elif wa and wa > 20:
                io_score -= (wa - 20) * 0.5

        # 基于累计IO量的评分
        io_content = self.get_file_content("app_io.txt")
        if io_content and io_content != "N/A":
            reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
            writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")

            if reads and writes:
                try:
                    total_mb = (int(reads) + int(writes)) / 1024 / 1024
                    if total_mb > 1000:  # > 1GB
                        io_score -= min(20, (total_mb - 1000) / 100)
                    elif total_mb > 100:  # > 100MB
                        io_score -= min(10, (total_mb - 100) / 50)
                except ValueError:
                    pass

        # 基于采样数据的峰值评分
        csv_content = self.get_file_content("perf_samples.csv")
        if csv_content and csv_content != "N/A" and '读IO' in csv_content:
            lines = csv_content.strip().split('\n')
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split(',')
                if len(parts) >= 6:
                    try:
                        read_rate = float(parts[4]) if parts[4] != 'N/A' and parts[4] != '' else 0
                        write_rate = float(parts[5]) if parts[5] != 'N/A' and parts[5] != '' else 0
                        max_rate = max(read_rate, write_rate)

                        if max_rate > 50000:  # > 50MB/s
                            io_score -= 10
                        elif max_rate > 20000:  # > 20MB/s
                            io_score -= 5
                        break
                    except (ValueError, IndexError):
                        pass

        return max(0, min(100, io_score))

    def get_io_stats(self) -> dict:
        """获取I/O统计数据"""
        io_content = self.get_file_content("app_io.txt")
        vmstat = self.get_file_content("vmstat.txt")

        stats = {
            "rchar_kb": "N/A",
            "wchar_kb": "N/A",
            "syscr": "N/A",
            "syscw": "N/A",
            "read_bytes_human": "N/A",
            "write_bytes_human": "N/A",
            "cancelled_write_kb": "N/A",
            "io_wait": "N/A",
            "avg_read_rate_kbs": "N/A",
            "avg_write_rate_kbs": "N/A",
            "max_read_rate_kbs": "N/A",
            "max_write_rate_kbs": "N/A",
        }

        if io_content and io_content != "N/A":
            rchar = self._extract_value(io_content, r"rchar:\s+(\d+)")
            wchar = self._extract_value(io_content, r"wchar:\s+(\d+)")
            syscr = self._extract_value(io_content, r"syscr:\s+(\d+)")
            syscw = self._extract_value(io_content, r"syscw:\s+(\d+)")
            reads = self._extract_value(io_content, r"read_bytes:\s+(\d+)")
            writes = self._extract_value(io_content, r"write_bytes:\s+(\d+)")
            cancelled = self._extract_value(io_content, r"cancelled_write_bytes:\s+(\d+)")

            if rchar:
                stats["rchar_kb"] = f"{int(rchar)/1024:.2f}"
            if wchar:
                stats["wchar_kb"] = f"{int(wchar)/1024:.2f}"
            if syscr:
                stats["syscr"] = syscr
            if syscw:
                stats["syscw"] = syscw
            if reads:
                stats["read_bytes_human"] = self._format_bytes(int(reads))
            if writes:
                stats["write_bytes_human"] = self._format_bytes(int(writes))
            if cancelled:
                stats["cancelled_write_kb"] = f"{int(cancelled)/1024:.2f}"

        if vmstat:
            wa = self._extract_wa_from_vmstat(vmstat)
            if wa is not None:
                stats["io_wait"] = str(int(wa))

        # 从采样数据计算速率
        csv_content = self.get_file_content("perf_samples.csv")
        if csv_content and csv_content != "N/A" and '读IO' in csv_content:
            rates = self._parse_io_rates(csv_content)
            if rates:
                stats["avg_read_rate_kbs"] = f"{rates['avg_read']:.2f}"
                stats["avg_write_rate_kbs"] = f"{rates['avg_write']:.2f}"
                stats["max_read_rate_kbs"] = f"{rates['max_read']:.2f}"
                stats["max_write_rate_kbs"] = f"{rates['max_write']:.2f}"

        return stats

    def _parse_io_rates(self, csv_content: str) -> Optional[Dict]:
        """解析CSV中的IO速率数据"""
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return None

        read_rates = []
        write_rates = []

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 6:
                try:
                    read_rate = float(parts[4]) if parts[4] != 'N/A' and parts[4] != '' else None
                    write_rate = float(parts[5]) if parts[5] != 'N/A' and parts[5] != '' else None
                    if read_rate is not None and read_rate > 0:
                        read_rates.append(read_rate)
                    if write_rate is not None and write_rate > 0:
                        write_rates.append(write_rate)
                except (ValueError, IndexError):
                    continue

        if not read_rates and not write_rates:
            return None

        return {
            'avg_read': sum(read_rates) / len(read_rates) if read_rates else 0,
            'avg_write': sum(write_rates) / len(write_rates) if write_rates else 0,
            'max_read': max(read_rates) if read_rates else 0,
            'max_write': max(write_rates) if write_rates else 0,
            'total_read_kb': sum(read_rates) if read_rates else 0,
            'total_write_kb': sum(write_rates) if write_rates else 0,
        }

    def _format_bytes(self, bytes_val: int) -> str:
        """格式化字节大小"""
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val/1024/1024/1024:.2f} GB"
        elif bytes_val >= 1024 * 1024:
            return f"{bytes_val/1024/1024:.2f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val/1024:.2f} KB"
        else:
            return f"{bytes_val} B"

    def get_io_samples_for_chart(self) -> List[Dict]:
        """获取用于图表的采样数据"""
        csv_content = self.get_file_content("perf_samples.csv")
        if not csv_content or csv_content == "N/A" or '读IO' not in csv_content:
            return []

        samples = []
        lines = csv_content.strip().split('\n')

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 6:
                try:
                    sample = {
                        'time': float(parts[0]),
                        'cpu': float(parts[1]) if parts[1] != 'N/A' else 0,
                        'rss': float(parts[2]) if parts[2] != 'N/A' else 0,
                        'vsize': float(parts[3]) if parts[3] != 'N/A' else 0,
                        'read_rate': float(parts[4]) if parts[4] != 'N/A' and parts[4] != '' else 0,
                        'write_rate': float(parts[5]) if parts[5] != 'N/A' and parts[5] != '' else 0,
                    }
                    samples.append(sample)
                except (ValueError, IndexError):
                    continue

        return samples

    def _extract_wa_from_vmstat(self, vmstat: str) -> Optional[float]:
        """
        从 vmstat 输出中提取 I/O 等待时间百分比 (wa 列)
        
        vmstat 标准格式: procs r b swpd free buff cache si so bi bo in cs us sy id wa st
        字段数: 17 (索引0-16)
        
        本脚本生成格式: "      0  0  0 643628 1432 28888    0    0     0     0     0     0   0   0  100   0   0"
        分割后有18个字段，wa在索引16
        
        wa值应该是0-100的百分比，不是free列的1432
        """
        if not vmstat:
            return None

        lines = vmstat.strip().split('\n')
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # 跳过表头和数据行
            if stripped.startswith('procs') or stripped.startswith('r '):
                continue

            fields = stripped.split()
            
            # 尝试多种列数情况
            # 本脚本生成格式(18字段): wa在索引16
            if len(fields) == 18:
                try:
                    wa = int(fields[16])
                    # wa应该是0-100的百分比
                    if 0 <= wa <= 100:
                        return float(wa)
                except (ValueError, IndexError):
                    pass
            # 标准vmstat格式(17字段): wa在索引15
            elif len(fields) == 17:
                try:
                    wa = int(fields[15])
                    if 0 <= wa <= 100:
                        return float(wa)
                except (ValueError, IndexError):
                    pass
            elif len(fields) >= 16:
                try:
                    wa = int(fields[15])
                    if 0 <= wa <= 100:
                        return float(wa)
                except (ValueError, IndexError):
                    pass

        return None
