#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰图生成器 - 生成火焰图和热点分析的HTML
"""

import re
import json
from typing import List, Tuple, Set, Dict
from .base import BaseHtmlGenerator


class FlamegraphGenerator(BaseHtmlGenerator):
    """火焰图HTML生成器"""

    def generate(self) -> str:
        return self._generate_flamegraph_section()

    def _generate_flamegraph_section(self) -> str:
        """生成火焰图分析章节"""
        perf_report = self.get_file_content("perf_report.txt")
        perf_flamegraph_svg = self.get_file_content("perf_flamegraph.svg")
        stack_counts = self.get_file_content("stack_counts.txt")
        syscall_counts = self.get_file_content("syscall_counts.txt")
        function_counts = self.get_file_content("function_counts.txt")
        perf_report_with_stack = self.get_file_content("perf_report_with_stack.txt")

        # 检查SVG内容
        svg_content = perf_flamegraph_svg if perf_flamegraph_svg else ""
        svg_display = "block" if svg_content and len(svg_content) > 100 else "none"

        # 解析热点函数
        hot_functions, graphics_func_names = self._extract_hot_functions(
            perf_report, perf_report_with_stack
        )

        # 生成热点函数调用栈
        hot_stacks_html = ""
        if stack_counts and stack_counts != "N/A" and hot_functions:
            hot_stacks_html = self._generate_hot_function_stacks(
                stack_counts, perf_report_with_stack, hot_functions[:10]
            )

        # 系统调用和函数计数
        syscall_html = self._generate_syscall_section(syscall_counts)
        func_count_html = self._generate_func_count_section(function_counts)

        # 热点函数表格
        hot_funcs_html, call_stack_note = self._generate_hot_functions_table(
            hot_functions, graphics_func_names, stack_counts, perf_report_with_stack, perf_report
        )

        return f"""
        <section id="flamegraph" class="card">
            <h2>火焰图与热点分析</h2>

            <div class="grid">
                <div class="stat-box">
                    <div class="value">{len(hot_functions)}</div>
                    <div class="label">检测到的热点函数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{len(graphics_func_names)}</div>
                    <div class="label">图形相关热点</div>
                </div>
                <div class="stat-box">
                    <div class="value">{f"{hot_functions[0][1]:.1f}%" if hot_functions else "0.0%"}</div>
                    <div class="label">最高热点占比</div>
                </div>
            </div>

            <div class="svg-flamegraph-container" style="display: {svg_display}; margin: 20px 0;">
                <h3>火焰图 (SVG)</h3>
                <p class="tip">点击火焰图中的函数可以查看详细信息。</p>
                <div class="svg-wrapper">
                    {svg_content}
                </div>
                <a href="perf_flamegraph.svg" download="perf_flamegraph.svg" class="download-link">下载SVG火焰图</a>
            </div>
            {'<p class="no-data">SVG火焰图暂不可用（需在本地执行perf生成）</p>' if svg_display == 'none' else ''}

            <h3>热点函数列表</h3>
            {hot_funcs_html}
            {call_stack_note}

            {hot_stacks_html}

            <h3>perf采样报告</h3>
            <pre>{self._escape_html(perf_report[:5000]) if perf_report != 'N/A' else 'perf数据不可用'}</pre>

            {syscall_html}
            {func_count_html}

            <div class="suggestion">
                <h4>热点分析方法</h4>
                <p>1. 查看上方热点函数列表，优先关注占比>5%的函数（高亮行）</p>
                <p>2. 图形相关热点（gl*/egl*/drm*）建议检查着色器复杂度、纹理格式、绘制调用次数</p>
                <p>3. 通用热点需评估是否有算法优化空间或缓存可能</p>
            </div>
        </section>
        """

    def _extract_hot_functions(self, perf_report: str,
                                perf_report_with_stack: str) -> Tuple[List[Tuple[str, float]], Set[str]]:
        """提取热点函数"""
        hot_functions = []
        seen = set()

        source = perf_report
        if not source or source == "N/A" or len(source.strip()) < 100 or \
           "not owned" in source or "采集失败" in source:
            source = perf_report_with_stack

        if not source or source == "N/A" or "采集失败" in source:
            return [], set()

        graphics_keywords = ['gl', 'egl', 'drm', 'gpu', 'shader', 'texture', 'render',
                        ' Mesa', 'intel', 'i915', 'libgles', 'libsrv', 'pvrsrv']
        graphics_func_names = set()

        for line in source.split('\n'):
            if not line.strip() or line.strip().startswith('#'):
                continue

            # 用户空间符号
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
                        hot_functions.append((func, pct))
                        if any(kw in func.lower() for kw in graphics_keywords):
                            graphics_func_names.add(func)
                    continue

            # kernel符号
            match2 = re.match(
                r'\s*(\d+\.?\d*)%\s+\d+\.?\d*%\s+\S+\s+(\S+)\s+\[k\]\s+(0x\S+)',
                line
            )
            if match2:
                pct = float(match2.group(1))
                shared_obj = match2.group(2).strip()
                addr = match2.group(3).strip()

                func = f"[k]0x{addr[-8:]}" if shared_obj == 'kernel.kallsyms' else shared_obj
                if func:
                    key = (func, pct)
                    if key not in seen:
                        seen.add(key)
                        hot_functions.append((func, pct))

        return hot_functions[:20], graphics_func_names

    def _generate_hot_functions_table(self, hot_functions: List, graphics_func_names: Set,
                                     stack_counts: str, perf_report_with_stack: str,
                                     perf_report: str) -> Tuple[str, str]:
        """生成热点函数表格"""
        if not hot_functions:
            call_stack_note = '''
                <div class="issue warning" style="margin-top: 15px;">
                    <h4>注意：未能解析出热点函数</h4>
                    <p>perf报告存在但未能解析出热点函数。</p>
                </div>'''
            return '<p class="no-data">暂无热点函数数据</p>', call_stack_note

        has_callchain = stack_counts and stack_counts != "N/A" and \
                       "no callchain" not in stack_counts.lower()
        if not has_callchain and perf_report_with_stack and len(perf_report_with_stack) > 1000:
            has_callchain = True

        hot_funcs_html = """
            <table class="hot-functions-table">
                <tr><th>排名</th><th>函数名</th><th>CPU占比</th><th>类别</th><th>操作</th></tr>"""

        for i, (func, pct) in enumerate(hot_functions[:15]):
            category = "图形" if func in graphics_func_names else "通用"
            func_id_clean = re.sub(r'[^a-zA-Z0-9]', '_', func[:30]).replace('_', '')
            func_id = f"stack_{func_id_clean}"
            highlight_class = "high-usage" if pct >= 5 else ""

            if has_callchain and pct >= 0.5:
                action_link = f'<a href="#{func_id}" class="stack-link" onclick="toggleStack(\'{func_id}_content\'); return false;">查看调用栈</a>'
            else:
                action_link = '<span class="no-data">无调用栈数据</span>'

            hot_funcs_html += f"""<tr class="{highlight_class}">
                <td>{i+1}</td>
                <td title="{self._escape_html(func)}"><code>{self._escape_html(func[:64] + "..." if len(func) > 64 else func)}</code></td>
                <td>{pct:.2f}%</td>
                <td><span class="category-tag {category.lower()}">{category}</span></td>
                <td>{action_link}</td>
            </tr>"""

        hot_funcs_html += "</table>"

        call_stack_note = ""
        if not has_callchain:
            call_stack_note = '''
                <div class="issue warning" style="margin-top: 15px;">
                    <h4>注意：调用栈数据不可用</h4>
                    <p>当前perf数据采集时未使用"-g"参数，因此没有调用链信息。</p>
                    <p>如需查看详细调用栈，请在远程设备上使用以下命令重新采集perf数据：</p>
                    <div class="code">perf record -F 99 -p &lt;PID&gt; -a -g -o /tmp/perf.data -- sleep 10</div>
                </div>'''

        return hot_funcs_html, call_stack_note

    def _generate_hot_function_stacks(self, stack_counts: str, perf_report: str,
                                      hot_functions: List) -> str:
        """生成热点函数调用栈"""
        html = "<h3 id='hot-stacks'>热点函数调用栈详情</h3><div class='stack-details'>"

        for func, pct in hot_functions:
            if pct < 0.5:
                continue

            func_id_clean = re.sub(r'[^a-zA-Z0-9]', '_', func[:30]).replace('_', '')
            func_id = f"stack_{func_id_clean}"
            display_func = func[:64] + "..." if len(func) > 64 else func

            stack_html = self._extract_call_stack(stack_counts, perf_report, func)

            html += f"""
                <div class="stack-function" id="{func_id}">
                    <div class="stack-header" onclick="toggleStack('{func_id}_content')">
                        <span class="stack-name" title="{self._escape_html(func)}"><code>{self._escape_html(display_func)}</code></span>
                        <span class="stack-pct">{pct:.2f}%</span>
                        <span class="stack-toggle">▼</span>
                    </div>
                    <div class="stack-content" id="{func_id}_content">
                        <pre>{stack_html if stack_html else '(无详细调用栈数据)'}</pre>
                    </div>
                </div>
            """

        html += "</div>"
        return html

    def _extract_call_stack(self, stack_counts: str, perf_report: str, func_name: str) -> str:
        """提取调用栈"""
        lines = stack_counts.split('\n')
        stack_frames = []
        found_target = False
        current_stack = []

        search_addr_part = None
        if func_name.startswith('0x') or '0x' in func_name:
            addr_match = re.search(r'0x([0-9a-f]+)', func_name)
            if addr_match:
                full_addr = addr_match.group(1)
                search_addr_part = full_addr[-6:] if len(full_addr) >= 6 else full_addr.lstrip('0')

        for line in lines:
            stripped = line.strip()

            if re.match(r'^\S+\s+\d+\s+\[\d+\]\s+\d+\.\d+:', stripped):
                if found_target and current_stack:
                    stack_frames.extend(current_stack)
                current_stack = []
                found_target = False
                continue

            if search_addr_part:
                addr_match = re.search(r'[0-9a-f]{6,}', stripped)
                if addr_match and (search_addr_part in addr_match.group(0)[-6:] or search_addr_part in addr_match.group(0)):
                    found_target = True
            elif func_name.lower() in stripped.lower():
                found_target = True

            if stripped and line.startswith('\t'):
                match = re.match(r'([0-9a-f]+)\s+\[unknown\]\s+\(([^)]+)\)', stripped)
                if match:
                    addr, module = match.group(1), match.group(2)
                    if 'libc' in module:
                        module_name = 'libc'
                    elif 'libGL' in module:
                        module_name = 'libGLES'
                    elif 'libsrv' in module:
                        module_name = 'libsrv_um'
                    elif 'pvrsrv' in module:
                        module_name = 'pvrsrvkm'
                    elif 'kanzi' in module:
                        module_name = 'kanzi'
                    else:
                        import os
                        module_name = os.path.basename(module)
                    current_stack.append(f"{module_name}:{addr[-8:]}")

        if found_target and current_stack:
            stack_frames.extend(current_stack)

        if not stack_frames:
            return ""

        stack_frames.reverse()
        deduped = []
        seen_frames = set()
        for f in stack_frames[:20]:
            if f not in seen_frames:
                seen_frames.add(f)
                deduped.append(f)

        result = []
        for i, frame in enumerate(deduped):
            if i == 0:
                result.append(f'<span class="func-entry">└─ {frame}</span>')
            else:
                result.append(f"{'&nbsp;&nbsp;&nbsp;' * (i - 1)}└─ {frame}")

        return '\n'.join(result)

    def _generate_syscall_section(self, syscall_counts: str) -> str:
        """生成系统调用部分"""
        if not syscall_counts or syscall_counts == "N/A" or "N/A" in syscall_counts:
            return ""

        lines = [l for l in syscall_counts.split('\n') if l.strip()][:10]
        if not lines:
            return ""

        return "<h3>系统调用统计</h3><pre>" + "\n".join(self._escape_html(l) for l in lines) + "</pre>"

    def _generate_func_count_section(self, function_counts: str) -> str:
        """生成函数计数部分"""
        if not function_counts or function_counts == "N/A" or "N/A" in function_counts:
            return ""

        lines = [l for l in function_counts.split('\n') if l.strip() and not l.startswith('#')][:15]
        if not lines:
            return ""

        return "<h3>图形函数调用频率</h3><pre>" + "\n".join(self._escape_html(l) for l in lines) + "</pre>"
