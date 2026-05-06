#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I/O和线程分析生成器 - 生成I/O性能和线程分析的HTML
"""

from .base import BaseHtmlGenerator


class IoAnalysisGenerator(BaseHtmlGenerator):
    """I/O性能分析HTML生成器"""

    def generate(self) -> str:
        return self._generate_io_analysis_section()

    def _generate_io_analysis_section(self) -> str:
        """生成I/O性能分析章节"""
        io_content = self.get_file_content("app_io.txt")
        vmstat = self.get_file_content("vmstat.txt")

        if not io_content or io_content == "N/A":
            return """
        <section id="io-analysis" class="card">
            <h2>7. I/O性能分析</h2>
            <div class="no-data">暂无I/O性能数据</div>
        </section>
            """

        read_pattern = r'read_bytes:\s+(\d+)'
        write_pattern = r'write_bytes:\s+(\d+)'

        def format_mb(v):
            return f"{int(v)/1024/1024:.2f} MB"

        return f"""
        <section id="io-analysis" class="card">
            <h2>5. I/O性能分析</h2>
            <h3>应用程序I/O统计</h3>
            <table>
                <tr><th>指标</th><th>值</th><th>评估</th></tr>
                {self._generate_io_row('读取字节数', io_content, read_pattern, format_mb)}
                {self._generate_io_row('写入字节数', io_content, write_pattern, format_mb)}
            </table>
            <h3>系统I/O等待</h3>
            <div class="stat-box">
                <div class="value">{self._extract_io_wait(vmstat)}%</div>
                <div class="label">I/O等待时间占比</div>
            </div>
            {self._generate_io_suggestions(io_content, vmstat)}
        </section>
        """

    def _generate_io_row(self, label: str, content: str, pattern: str, formatter) -> str:
        """生成I/O指标行"""
        value = self._extract_value(content, pattern)
        if value:
            formatted_value = formatter(value)
            return f"<tr><td>{label}</td><td>{formatted_value}</td><td>{self._evaluate_io_value(value)}</td></tr>"
        return f"<tr><td>{label}</td><td>N/A</td><td>未知</td></tr>"

    def _evaluate_io_value(self, value: str) -> str:
        """评估I/O值"""
        try:
            val = int(value)
            if val < 10000:
                return '<span class="status normal">正常</span>'
            elif val < 1000000:
                return '<span class="status warning">较高</span>'
            else:
                return '<span class="status error">很高</span>'
        except ValueError:
            return "未知"

    def _extract_io_wait(self, vmstat: str) -> str:
        """提取I/O等待时间"""
        if not vmstat:
            return "N/A"
        wa = self._extract_number(vmstat, r"\d+\s+\d+\s+\d+\s+\d+\s+(\d+)\s+")
        return str(wa) if wa else "N/A"

    def _generate_io_suggestions(self, io_content: str, vmstat: str) -> str:
        """生成I/O优化建议"""
        suggestions = []

        io_wait = self._extract_io_wait(vmstat)
        if io_wait and io_wait != 'N/A' and float(io_wait) > 20:
            suggestions.append(f"系统I/O等待时间较高 ({io_wait}%)，建议检查磁盘I/O瓶颈。")

        reads = self._extract_value(io_content, r'read_bytes:\s+(\d+)')
        writes = self._extract_value(io_content, r'write_bytes:\s+(\d+)')

        if reads:
            try:
                reads_mb = int(reads) / 1024 / 1024
                if reads_mb > 1:
                    suggestions.append(f"检测到较大单次读取操作 ({reads_mb:.2f}MB)，考虑使用内存缓存。")
            except ValueError:
                pass

        if writes:
            try:
                writes_mb = int(writes) / 1024 / 1024
                if writes_mb > 1:
                    suggestions.append(f"检测到较大单次写入操作 ({writes_mb:.2f}MB)，考虑使用批处理。")
            except ValueError:
                pass

        if not suggestions:
            return '<p>当前I/O性能状况良好，暂无特别优化建议。</p>'

        return "<div class='suggestion'>" + "<p>" + "</p><p>".join(suggestions) + "</p></div>"


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
            <h2>6. 线程与锁分析</h2>
            <div class="no-data">暂无线程数据</div>
        </section>
            """

        return f"""
        <section id="threads-analysis" class="card">
            <h2>8. 线程与锁分析</h2>

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
