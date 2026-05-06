#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络分析器 - 分析网络性能
"""

from .base import BaseAnalyzer


class NetworkAnalyzer(BaseAnalyzer):
    """网络性能分析器"""

    def analyze(self) -> None:
        """执行网络分析"""
        self._check_network_traffic()
        self._check_network_errors()

    def _check_network_traffic(self) -> None:
        """检查网络流量"""
        net_dev = self.get_file_content("net_dev.txt")
        if not net_dev or net_dev == "N/A":
            return

        lines = net_dev.split('\n')
        for line in lines:
            if 'lo:' in line or 'eth' in line or 'enp' in line:
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        rx_bytes = int(parts[1])
                        tx_bytes = int(parts[9])
                        # 可以添加流量分析逻辑
                    except (ValueError, IndexError):
                        pass

    def _check_network_errors(self) -> None:
        """检查网络错误"""
        net_stat = self.get_file_content("net_stat.txt")
        if not net_stat or net_stat == "N/A":
            return

        # 检查是否有丢包、错误等
        if 'error' in net_stat.lower() or 'drop' in net_stat.lower():
            self.add_suggestion(
                "网络错误检测",
                "检测到网络错误或丢包",
                "检查网络连接状态和网卡配置。",
                "network"
            )
