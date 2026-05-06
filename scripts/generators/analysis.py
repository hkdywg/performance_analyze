#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I/O和线程分析生成器 - 生成I/O性能和线程分析的HTML

I/O分析部分支持:
- /proc/{pid}/io 累计数据展示
- IO采样速率数据展示
- IO操作分析
- IO图表数据准备
"""

import re
from typing import Dict, List, Optional
from .base import BaseHtmlGenerator


class IoAnalysisGenerator(BaseHtmlGenerator):
    """I/O性能分析HTML生成器"""

    # 进程IO操作映射表
    IO_FIELDS = {
        'rchar': '字符读取 (rchar)',
        'wchar': '字符写入 (wchar)',
        'syscr': '读系统调用次数 (syscr)',
        'syscw': '写系统调用次数 (syscw)',
        'read_bytes': '实际读取字节 (read_bytes)',
        'write_bytes': '实际写入字节 (write_bytes)',
        'cancelled_write_bytes': '取消的写入字节 (cancelled_write_bytes)',
    }

    def generate(self) -> str:
        return self._generate_io_analysis_section()

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

    def _parse_io_content(self, content: str) -> Dict:
        """解析/proc/{pid}/io内容"""
        result = {}
        for key in self.IO_FIELDS.keys():
            match = re.search(rf'{key}:\s+(\d+)', content)
            if match:
                result[key] = int(match.group(1))
        return result

    def _parse_io_rates(self, csv_content: str) -> Optional[Dict]:
        """解析CSV中的IO速率数据"""
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return None

        # 检查是否有IO列
        header = lines[0]
        if '读IO' not in header and 'read_rate' not in header.lower():
            return None

        read_rates = []
        write_rates = []
        times = []

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 6:
                try:
                    time = float(parts[0])
                    read_rate = float(parts[4]) if parts[4] not in ['N/A', ''] else None
                    write_rate = float(parts[5]) if parts[5] not in ['N/A', ''] else None

                    times.append(time)
                    if read_rate is not None and read_rate >= 0:
                        read_rates.append(read_rate)
                    if write_rate is not None and write_rate >= 0:
                        write_rates.append(write_rate)
                except (ValueError, IndexError):
                    continue

        if not read_rates and not write_rates:
            return None

        return {
            'times': times,
            'read_rates': read_rates,
            'write_rates': write_rates,
            'avg_read': sum(read_rates) / len(read_rates) if read_rates else 0,
            'avg_write': sum(write_rates) / len(write_rates) if write_rates else 0,
            'max_read': max(read_rates) if read_rates else 0,
            'max_write': max(write_rates) if write_rates else 0,
            'total_read_kb': sum(read_rates),
            'total_write_kb': sum(write_rates),
            'sample_count': len(times),
        }

    def _generate_io_analysis_section(self) -> str:
        """生成I/O性能分析章节"""
        io_content = self.get_file_content("app_io.txt")
        csv_content = self.get_file_content("perf_samples.csv")
        vmstat = self.get_file_content("vmstat.txt")

        if not io_content or io_content == "N/A":
            return """
        <section id="io-analysis" class="card">
            <h2>I/O性能分析</h2>
            <div class="no-data">暂无I/O性能数据</div>
        </section>
            """

        io_data = self._parse_io_content(io_content)
        io_rates = self._parse_io_rates(csv_content) if csv_content and csv_content != "N/A" else None
        io_wait = self._extract_io_wait(vmstat)

        # 计算累计IO总量
        total_io_bytes = io_data.get('read_bytes', 0) + io_data.get('write_bytes', 0)
        total_io_mb = total_io_bytes / 1024 / 1024

        # 计算读写比例
        read_bytes = io_data.get('read_bytes', 0)
        write_bytes = io_data.get('write_bytes', 0)
        rw_ratio = read_bytes / write_bytes if write_bytes > 0 else 0

        # 判断IO模式
        io_mode = "读密集型" if rw_ratio > 5 else ("写密集型" if rw_ratio < 0.2 else "均衡型")

        html = f"""
        <section id="io-analysis" class="card">
            <h2>I/O性能分析</h2>

            <div class="grid">
                <div class="stat-box">
                    <div class="value">{self._format_bytes(total_io_bytes)}</div>
                    <div class="label">累计I/O总量</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_mode}</div>
                    <div class="label">I/O模式</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_wait}%</div>
                    <div class="label">系统I/O等待</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_data.get('syscr', 'N/A')}</div>
                    <div class="label">读系统调用</div>
                </div>
            </div>

            <h3>进程I/O统计 (从启动至今累计)</h3>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>值</th>
                        <th>说明</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>字符读取</td>
                        <td>{self._format_bytes(io_data.get('rchar', 0))}</td>
                        <td>通过read/write读取的字符数</td>
                    </tr>
                    <tr>
                        <td>字符写入</td>
                        <td>{self._format_bytes(io_data.get('wchar', 0))}</td>
                        <td>通过read/write写入的字符数</td>
                    </tr>
                    <tr>
                        <td>实际读取</td>
                        <td>{self._format_bytes(read_bytes)}</td>
                        <td>实际从磁盘读取的字节数</td>
                    </tr>
                    <tr>
                        <td>实际写入</td>
                        <td>{self._format_bytes(write_bytes)}</td>
                        <td>实际写入磁盘的字节数</td>
                    </tr>
                    <tr>
                        <td>读系统调用</td>
                        <td>{io_data.get('syscr', 'N/A'):,}</td>
                        <td>读操作系统调用次数</td>
                    </tr>
                    <tr>
                        <td>写系统调用</td>
                        <td>{io_data.get('syscw', 'N/A'):,}</td>
                        <td>写操作系统调用次数</td>
                    </tr>
                    <tr>
                        <td>取消的写入</td>
                        <td>{self._format_bytes(io_data.get('cancelled_write_bytes', 0))}</td>
                        <td>被取消的写入字节数（如写入被截断）</td>
                    </tr>
                    <tr>
                        <td>平均读大小</td>
                        <td>{self._format_bytes(int(read_bytes / max(1, io_data.get('syscr', 1))))}</td>
                        <td>每次读操作的平均字节数</td>
                    </tr>
                    <tr>
                        <td>平均写大小</td>
                        <td>{self._format_bytes(int(write_bytes / max(1, io_data.get('syscw', 1))))}</td>
                        <td>每次写操作的平均字节数</td>
                    </tr>
                </tbody>
            </table>
"""

        # 如果有采样数据，添加采样分析部分
        if io_rates:
            html += f"""
            <h3>I/O采样分析 (采样{io_rates['sample_count']}次)</h3>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>读取速率</th>
                        <th>写入速率</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>平均速率</td>
                        <td>{io_rates['avg_read']/1024:.2f} MB/s</td>
                        <td>{io_rates['avg_write']/1024:.2f} MB/s</td>
                    </tr>
                    <tr>
                        <td>峰值速率</td>
                        <td>{io_rates['max_read']/1024:.2f} MB/s</td>
                        <td>{io_rates['max_write']/1024:.2f} MB/s</td>
                    </tr>
                    <tr>
                        <td>累计传输</td>
                        <td>{io_rates['total_read_kb']/1024:.2f} MB</td>
                        <td>{io_rates['total_write_kb']/1024:.2f} MB</td>
                    </tr>
                </tbody>
            </table>
"""

        # 添加优化建议
        html += self._generate_io_suggestions(io_data, io_rates, io_wait)

        html += """
        </section>
        """
        return html

    def _extract_io_wait(self, vmstat: str) -> str:
        """提取I/O等待时间"""
        if not vmstat:
            return "N/A"
        wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
        return str(wa) if wa else "N/A"

    def _generate_io_suggestions(self, io_data: Dict, io_rates: Optional[Dict], io_wait: str) -> str:
        """生成I/O优化建议"""
        suggestions = []

        # I/O等待分析
        if io_wait and io_wait != 'N/A':
            try:
                wait_val = float(io_wait)
                if wait_val > 30:
                    suggestions.append(f"<strong>I/O等待过高</strong>: 系统{wait_val}%时间在等待I/O，可能存在存储瓶颈。")
                elif wait_val > 20:
                    suggestions.append(f"<strong>I/O等待较高</strong>: 系统{wait_val}%时间在等待I/O，建议关注存储性能。")
            except ValueError:
                pass

        # 读写比例分析
        read_bytes = io_data.get('read_bytes', 0)
        write_bytes = io_data.get('write_bytes', 0)
        if write_bytes > 0:
            rw_ratio = read_bytes / write_bytes
            if rw_ratio < 0.1:
                suggestions.append("<strong>写密集型应用</strong>: 写入量远大于读取，考虑使用写缓存或延迟写策略。")
            elif rw_ratio > 10:
                suggestions.append("<strong>读密集型应用</strong>: 读取量远大于写入，建议增加缓存提高读取性能。")

        # 累计IO量分析
        total_io = read_bytes + write_bytes
        if total_io > 1024 * 1024 * 1024:  # > 1GB
            suggestions.append(f"<strong>高I/O应用</strong>: 累计I/O量超过1GB ({total_io/1024/1024/1024:.2f}GB)，建议优化I/O模式或使用更快存储。")

        # 采样峰值分析
        if io_rates:
            if io_rates['max_read'] > 50 * 1024:  # > 50MB/s
                suggestions.append(f"<strong>高读取峰值</strong>: 检测到{io_rates['max_read']/1024:.1f}MB/s的读取峰值，考虑使用缓冲读取。")
            if io_rates['max_write'] > 20 * 1024:  # > 20MB/s
                suggestions.append(f"<strong>高写入峰值</strong>: 检测到{io_rates['max_write']/1024:.1f}MB/s的写入峰值，考虑批量写入。")

            # IO稳定性分析
            if io_rates['avg_read'] > 0:
                variance = sum((x - io_rates['avg_read']) ** 2 for x in io_rates['read_rates']) / len(io_rates['read_rates'])
                std_dev = variance ** 0.5
                if std_dev > io_rates['avg_read'] * 2 and io_rates['avg_read'] > 100:
                    suggestions.append("<strong>I/O不稳定</strong>: 读取速率波动大，可能存在批量操作或缓存抖动。")

        # 取消写入分析
        cancelled = io_data.get('cancelled_write_bytes', 0)
        if cancelled > write_bytes * 0.1 and write_bytes > 0:
            suggestions.append(f"<strong>写入浪费</strong>: {cancelled/1024:.1f}KB写入被取消，可能存在频繁的seek或截断操作。")

        if not suggestions:
            return '<p><strong>评估:</strong> I/O性能状况良好，暂无特别优化建议。</p>'

        suggestions_html = '<div class="suggestion"><h4>I/O优化建议</h4><ul>'
        for s in suggestions:
            suggestions_html += f'<li>{s}</li>'
        suggestions_html += '</ul></div>'
        return suggestions_html


class ThreadAnalysisGenerator(BaseHtmlGenerator):
    """线程分析HTML生成器"""

    def generate(self) -> str:
        return self._generate_threads_analysis_section()

    def _generate_threads_analysis_section(self) -> str:
        """生成线程与锁分析章节"""
        content = self.get_file_content("app_threads.txt")
        status_content = self.get_file_content("app_status.txt")

        if not content or content == "N/A":
            return """
        <section id="threads-analysis" class="card">
            <h2>线程与锁分析</h2>
            <div class="no-data">暂无线程数据</div>
        </section>
            """

        return f"""
        <section id="threads-analysis" class="card">
            <h2>线程与锁分析</h2>

            <h3>线程统计</h3>
            <table>
                <tr><th>状态</th><th>数量</th><th>占比</th></tr>
                {self._generate_thread_row(content, 'R', '运行中', 0)}
                {self._generate_thread_row(content, 'S', '睡眠中', 0)}
                {self._generate_thread_row(content, 'D', '不可中断', 0)}
            </table>

            <h3>线程分析</h3>
            {self._generate_thread_suggestions(content, status_content)}
        </section>
        """

    def _generate_thread_row(self, content: str, state: str, label: str, offset: int) -> str:
        """生成线程统计行"""
        count = 0
        if content and content != "N/A":
            lines = content.split('\n')
            for line in lines:
                if state in line:
                    count += 1

        total = count + offset
        if total > 0:
            percentage = (count / total) * 100
            return f"<tr><td>{label} ({state})</td><td>{count}</td><td>{percentage:.1f}%</td></tr>"
        return f"<tr><td>{label} ({state})</td><td>{count}</td><td>N/A</td></tr>"

    def _generate_thread_suggestions(self, content: str, status_content: str) -> str:
        """生成线程分析建议"""
        suggestions = []

        lines = content.split('\n')
        thread_count = sum(1 for line in lines if line.strip() and ' ' in line) - 1

        if thread_count > 32:
            suggestions.append(f"线程数量较多 ({thread_count}个)，可能增加上下文切换开销。")

        d_count = sum(1 for line in lines if 'D' in line and ' ' in line)
        if d_count > 0:
            suggestions.append(f"检测到 {d_count} 个不可中断睡眠线程，可能阻塞在I/O操作。")

        s_count = sum(1 for line in lines if 'S' in line and ' ' in line)
        if thread_count > 0:
            sleep_ratio = (s_count / thread_count) * 100
            if sleep_ratio > 90:
                suggestions.append(f"大量线程处于睡眠状态 ({sleep_ratio:.1f}%)，可能存在线程设计问题。")

        if not suggestions:
            return '<p>线程运行状态良好，暂无特别优化建议。</p>'

        return "<div class='suggestion'>" + "<p>" + "</p><p>".join(suggestions) + "</p></div>"
