#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程stat信息生成器 - 生成进程/proc/{pid}/stat的HTML展示

此模块解析进程stat信息并生成格式化的HTML展示，
包括CPU时间、上下文切换、内存缺页等详细指标。
"""

import re
from .base import BaseHtmlGenerator


class ProcStatGenerator(BaseHtmlGenerator):
    """进程stat信息HTML生成器"""

    # 进程状态描述
    STATE_DESCRIPTIONS = {
        'R': '运行中',
        'S': '可中断睡眠',
        'D': '不可中断睡眠(等待I/O)',
        'Z': '僵尸进程',
        'T': '已停止',
        'I': '空闲',
        'W': '换页中',
        'X': '已退出',
    }

    # 调度策略名称
    POLICY_NAMES = {
        0: 'SCHED_NORMAL',
        1: 'SCHED_FIFO',
        2: 'SCHED_RR',
        3: 'SCHED_BATCH',
        5: 'SCHED_IDLE',
        6: 'SCHED_DEADLINE',
    }

    def generate(self) -> str:
        """生成HTML片段"""
        return self._generate_proc_stat_section()

    def _parse_stat(self, content: str) -> dict:
        """
        解析 /proc/{pid}/stat 内容

        Args:
            content: stat文件原始内容

        Returns:
            解析后的字段字典
        """
        content = content.strip()
        if not content:
            return {}

        # 找到comm字段 (在括号内)
        bracket_match = re.search(r'\((\S+)\)', content)
        if not bracket_match:
            return {}

        comm = bracket_match.group(1)

        # 提取括号外的数据部分
        data_part = content[bracket_match.end():].strip()
        fields = data_part.split()

        if len(fields) < 20:
            return {}

        # 构建解析结果
        result = {
            'comm': comm,
            'state': fields[0],
            'ppid': int(fields[1]),
            'pgrp': int(fields[2]),
            'session': int(fields[3]),
            'minflt': int(fields[7]),
            'cminflt': int(fields[8]),
            'majflt': int(fields[9]),
            'cmajflt': int(fields[10]),
            'utime': int(fields[11]),
            'stime': int(fields[12]),
            'cutime': int(fields[13]),
            'cstime': int(fields[14]),
            'priority': int(fields[15]),
            'nice': int(fields[16]),
            'num_threads': int(fields[17]),
        }

        if len(fields) >= 20:
            result['starttime'] = int(fields[19])

        if len(fields) >= 22:
            result['vsize'] = int(fields[20])
            result['rss'] = int(fields[21])

        if len(fields) >= 39:
            result['processor'] = int(fields[38])

        if len(fields) >= 40:
            result['rt_priority'] = int(fields[39])

        if len(fields) >= 41:
            result['policy'] = int(fields[40])

        return result

    def _get_clock_ticks(self) -> int:
        """获取系统时钟每秒ticks数，默认为100"""
        return 100

    def _format_memory(self, kb: int) -> str:
        """格式化内存大小"""
        if kb >= 1024 * 1024:
            return f"{kb / 1024 / 1024:.1f} GB"
        elif kb >= 1024:
            return f"{kb / 1024:.0f} MB"
        else:
            return f"{kb} KB"

    def _get_state_badge(self, state: str) -> str:
        """获取状态徽章HTML"""
        state_classes = {
            'R': 'normal',  # 运行 - 绿色
            'S': 'normal',  # 睡眠 - 绿色
            'D': 'error',   # 不可中断睡眠 - 红色
            'Z': 'error',   # 僵尸 - 红色
            'T': 'warning', # 停止 - 黄色
            'I': 'normal',  # 空闲 - 绿色
        }
        badge_class = state_classes.get(state, 'warning')
        state_desc = self.STATE_DESCRIPTIONS.get(state, '未知')
        return f'<span class="status {badge_class}">{state_desc}</span>'

    def _generate_proc_stat_section(self) -> str:
        """生成进程stat信息部分"""
        stat_content = self.get_file_content("app_stat.txt")

        if not stat_content or stat_content == "N/A" or not stat_content.strip():
            return """
        <section id="proc-stat" class="card">
            <h2>进程Stat信息</h2>
            <p class="no-data">暂无进程stat数据</p>
        </section>
            """

        parsed = self._parse_stat(stat_content)
        if not parsed:
            return """
        <section id="proc-stat" class="card">
            <h2>进程Stat信息</h2>
            <p class="no-data">无法解析进程stat数据</p>
        </section>
            """

        clk_tck = self._get_clock_ticks()

        # 计算CPU时间
        utime_sec = parsed.get('utime', 0) / clk_tck
        stime_sec = parsed.get('stime', 0) / clk_tck
        cutime_sec = parsed.get('cutime', 0) / clk_tck
        cstime_sec = parsed.get('cstime', 0) / clk_tck
        total_cpu_time = utime_sec + stime_sec
        total_cpu_time_with_children = utime_sec + stime_sec + cutime_sec + cstime_sec

        # 计算内核态占比
        kernel_ratio = 0
        if total_cpu_time > 0:
            kernel_ratio = stime_sec / total_cpu_time * 100

        # 内存大小
        vsize_mb = parsed.get('vsize', 0) / 1024 / 1024
        rss_pages = parsed.get('rss', 0)
        # RSS页数转换为KB (假设4KB页)
        rss_kb = rss_pages * 4

        # 上下文切换
        status_content = self.get_file_content("app_status.txt")
        vol_cs = invol_cs = 0
        if status_content and status_content != "N/A":
            vol_match = re.search(r'voluntary_ctxt_switches:\s+(\d+)', status_content)
            invol_match = re.search(r'nonvoluntary_ctxt_switches:\s+(\d+)', status_content)
            if vol_match:
                vol_cs = int(vol_match.group(1))
            if invol_match:
                invol_cs = int(invol_match.group(1))

        # 获取调度策略名称
        policy = parsed.get('policy', 0)
        policy_name = self.POLICY_NAMES.get(policy, f'UNKNOWN({policy})')

        state = parsed.get('state', 'N/A')
        state_badge = self._get_state_badge(state)

        return f"""
        <section id="proc-stat" class="card">
            <h2>进程Stat详细信息</h2>

            <h3>CPU时间分析</h3>
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
                        <td>用户态CPU时间 (utime)</td>
                        <td>{utime_sec:.2f}s</td>
                        <td>进程在用户态运行的CPU时间</td>
                    </tr>
                    <tr>
                        <td>内核态CPU时间 (stime)</td>
                        <td>{stime_sec:.2f}s</td>
                        <td>进程在内核态运行的CPU时间</td>
                    </tr>
                    <tr>
                        <td>子进程用户态时间</td>
                        <td>{cutime_sec:.2f}s</td>
                        <td>所有已终止子进程的用户态时间</td>
                    </tr>
                    <tr>
                        <td>子进程内核态时间</td>
                        <td>{cstime_sec:.2f}s</td>
                        <td>所有已终止子进程的内核态时间</td>
                    </tr>
                    <tr>
                        <td>累计CPU时间</td>
                        <td>{total_cpu_time_with_children:.2f}s</td>
                        <td>进程及子进程总CPU时间</td>
                    </tr>
                    <tr>
                        <td>内核态占比</td>
                        <td>{kernel_ratio:.1f}%</td>
                        <td>内核态时间占总CPU时间比例</td>
                    </tr>
                </tbody>
            </table>

            <h3>进程属性</h3>
            <table>
                <thead>
                    <tr>
                        <th>属性</th>
                        <th>值</th>
                        <th>说明</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>PID</td>
                        <td>{parsed.get('pid', 'N/A')}</td>
                        <td>进程ID</td>
                    </tr>
                    <tr>
                        <td>PPID</td>
                        <td>{parsed.get('ppid', 'N/A')}</td>
                        <td>父进程ID</td>
                    </tr>
                    <tr>
                        <td>进程组ID</td>
                        <td>{parsed.get('pgrp', 'N/A')}</td>
                        <td>进程所属进程组</td>
                    </tr>
                    <tr>
                        <td>会话ID</td>
                        <td>{parsed.get('session', 'N/A')}</td>
                        <td>进程所属会话</td>
                    </tr>
                    <tr>
                        <td>调度优先级 (priority)</td>
                        <td>{parsed.get('priority', 'N/A')}</td>
                        <td>内核调度优先级</td>
                    </tr>
                    <tr>
                        <td>Nice值</td>
                        <td>{parsed.get('nice', 'N/A')}</td>
                        <td>进程nice值 (-20~19)</td>
                    </tr>
                    <tr>
                        <td>实时优先级</td>
                        <td>{parsed.get('rt_priority', 0)}</td>
                        <td>实时调度优先级 (0表示非实时)</td>
                    </tr>
                    <tr>
                        <td>调度策略</td>
                        <td>{policy_name}</td>
                        <td>CPU调度策略</td>
                    </tr>
                    <tr>
                        <td>最近运行CPU</td>
                        <td>{parsed.get('processor', 'N/A')}</td>
                        <td>最后执行时的CPU核心编号</td>
                    </tr>
                </tbody>
            </table>

            <h3>内存信息</h3>
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
                        <td>虚拟内存大小</td>
                        <td>{vsize_mb:.1f} MB</td>
                        <td>进程虚拟地址空间大小</td>
                    </tr>
                    <tr>
                        <td>物理内存 (RSS)</td>
                        <td>{self._format_memory(rss_kb)}</td>
                        <td>驻留集大小，实际使用的物理内存</td>
                    </tr>
                </tbody>
            </table>

            <h3>上下文切换</h3>
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>次数</th>
                        <th>说明</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>主动上下文切换</td>
                        <td>{vol_cs:,}</td>
                        <td>进程主动放弃CPU (等待资源)</td>
                    </tr>
                    <tr>
                        <td>被动上下文切换</td>
                        <td>{invol_cs:,}</td>
                        <td>进程被时间片耗尽抢占</td>
                    </tr>
                    <tr>
                        <td>总上下文切换</td>
                        <td>{vol_cs + invol_cs:,}</td>
                        <td>总切换次数</td>
                    </tr>
                </tbody>
            </table>

            <h3>原始数据</h3>
            <pre>{self._escape_html(stat_content[:2000])}</pre>
        </section>
        """
