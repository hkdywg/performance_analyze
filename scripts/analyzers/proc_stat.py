#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程stat分析器 - 解析/proc/{pid}/stat获取详细进程状态

/proc/{pid}/stat 格式说明：
  pid      (1) 进程ID
  comm     (2) 命令名
  state    (3) 进程状态 (R=运行, S=睡眠, D=不可中断睡眠, Z=僵尸, T=停止, I=空闲)
  ppid     (4) 父进程ID
  pgrp     (5) 进程组ID
  session  (6) 会话ID
  tty_nr   (7) 控制终端
  tpgid    (8) 终端进程组ID
  flags    (9) 进程标志
  minflt   (10) 次要缺页中断数
  cminflt  (11) 子进程次要缺页中断数
  majflt   (12) 主要缺页中断数
  cmajflt  (13) 子进程主要缺页中断数
  utime    (14) 用户态CPU时间(时钟 ticks)
  stime    (15) 内核态CPU时间(时钟 ticks)
  cutime   (16) 子进程用户态CPU时间
  cstime   (17) 子进程内核态CPU时间
  priority (18) 调度优先级
  nice     (19) nice值 (-20到19，越低优先级越高)
  num_threads (20) 线程数
  itrealvalue (21) 迭代器值
  starttime (22) 启动时间(相对于系统启动的时钟 ticks)
  vsize    (23) 虚拟内存大小(字节)
  rss      (24) 内存页数
  rsslim   (25) RSS限制
  startcode (26) 代码段起始地址
  endcode  (27) 代码段结束地址
  startstack (28) 栈起始地址
  kstkesp  (29) 栈指针ESP
  kstkeip  (30) 指令指针EIP
  signal   (31) 待处理信号
  blocked  (32) 阻塞信号
  sigignore (33) 忽略信号
  sigcatch (34) 捕获信号
  wchan    (35) 等待频道
  nswap    (36) 交换空间
  cnswap   (37) 子进程交换空间
  exit_signal (38) 退出信号
  processor (39) 最后执行的CPU编号
  rt_priority (40) 实时优先级
  policy   (41) 调度策略
  blkio_ticks (42) 阻塞I/O延迟
  gtime    (43) 来宾时间
  cgtime   (44) 子进程来宾时间
  start_data (45) 数据段起始地址
  end_data (46) 数据段结束地址
  start_brk (47) 堆起始地址
  arg_start (48) 命令行参数起始地址
  arg_end (49) 命令行参数结束地址
  env_start (50) 环境变量起始地址
  env_end (51) 环境变量结束地址
  exit_code (52) 退出码
"""

import re
from typing import Dict, List, Optional, Tuple
from .base import BaseAnalyzer


class ProcessStatAnalyzer(BaseAnalyzer):
    """进程stat信息分析器"""

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

    def analyze(self) -> None:
        """执行stat分析"""
        stat_content = self.get_file_content("app_stat.txt")
        if not stat_content or stat_content == "N/A":
            return

        parsed = self._parse_stat(stat_content)
        if not parsed:
            return

        self._check_process_state(parsed)
        self._check_cpu_time(parsed)
        self._check_context_switches(parsed)
        self._check_memory_faults(parsed)
        self._check_threading(parsed)

    def _parse_stat(self, content: str) -> Optional[Dict]:
        """
        解析 /proc/{pid}/stat 内容

        Returns:
            解析后的字段字典
        """
        content = content.strip()
        if not content:
            return None

        # 找到comm字段 (在括号内)
        bracket_match = re.search(r'\((\S+)\)', content)
        if not bracket_match:
            return None

        comm = bracket_match.group(1)

        # 提取括号外的数据部分
        data_part = content[bracket_match.end():].strip()
        fields = data_part.split()

        if len(fields) < 20:
            return None

        # 构建解析结果
        result = {
            'comm': comm,
            'state': fields[0],
            'ppid': int(fields[1]),
            'pgrp': int(fields[2]),
            'session': int(fields[3]),
            'tty_nr': int(fields[4]),
            'tpgid': int(fields[5]),
            'flags': fields[6],
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

        if len(fields) >= 42:
            result['blkio_ticks'] = int(fields[41])

        return result

    def _get_clock_ticks(self) -> int:
        """获取系统时钟每秒ticks数"""
        try:
            with open('/proc/self/stat', 'r') as f:
                pass
        except:
            pass

        # 常见的CLK_TCK值，通常是100
        return 100

    def _check_process_state(self, parsed: Dict) -> None:
        """检查进程状态"""
        state = parsed.get('state', '')
        state_desc = self.STATE_DESCRIPTIONS.get(state, '未知')

        if state == 'D':
            self.add_issue(
                "error",
                "进程处于不可中断睡眠状态(D)",
                "进程正在等待I/O操作完成，可能是磁盘或网络I/O阻塞"
            )
            self.add_suggestion(
                "I/O阻塞排查",
                "进程处于不可中断睡眠状态，通常表示等待I/O完成。",
                "检查磁盘I/O性能、网络连接状态，或使用iostat/iotop排查具体I/O来源。"
            )
        elif state == 'Z':
            self.add_issue(
                "error",
                "检测到僵尸进程",
                "进程已终止但未被父进程回收"
            )
            self.add_suggestion(
                "僵尸进程处理",
                "需要父进程调用wait()回收子进程资源。",
                "检查父进程代码，确保正确处理子进程退出状态。"
            )
        elif state == 'T':
            self.add_issue(
                "warning",
                "进程已停止(T)",
                "进程收到SIGSTOP信号或被调试器暂停"
            )

    def _check_cpu_time(self, parsed: Dict) -> None:
        """检查CPU时间"""
        utime = parsed.get('utime', 0)
        stime = parsed.get('stime', 0)
        cutime = parsed.get('cutime', 0)
        cstime = parsed.get('cstime', 0)

        total_time = utime + stime + cutime + cstime
        kernel_time = stime + cstime

        if total_time > 0:
            kernel_ratio = kernel_time / total_time
            if kernel_ratio > 0.5:
                self.add_issue(
                    "warning",
                    "内核态CPU占用过高",
                    f"内核态CPU占比: {kernel_ratio*100:.1f}%，可能存在系统调用或内核操作瓶颈"
                )
                self.add_suggestion(
                    "内核态优化",
                    "应用在内核态消耗过多CPU时间。",
                    "检查系统调用频率，使用strace分析内核操作，优化I/O模式。"
                )

    def _check_context_switches(self, parsed: Dict) -> None:
        """检查上下文切换"""
        # voluntary_ctxt_switches 和 nonvoluntary_ctxt_switches 在 status 中
        status = self.get_file_content("app_status.txt")
        if not status or status == "N/A":
            return

        vol_cs = self._extract_number(status, r'voluntary_ctxt_switches:\s+(\d+)')
        invol_cs = self._extract_number(status, r'nonvoluntary_ctxt_switches:\s+(\d+)')

        if vol_cs and vol_cs > 10000:
            self.add_suggestion(
                "主动上下文切换频繁",
                f"主动上下文切换次数: {vol_cs}",
                "可能存在锁竞争或同步问题，考虑使用无锁数据结构或减少锁粒度。",
                "threads"
            )

        if invol_cs and invol_cs > 10000:
            self.add_suggestion(
                "被动上下文切换频繁",
                f"被动上下文切换次数: {invol_cs}",
                "可能CPU核心不足或进程被频繁抢占，考虑绑定CPU核心或调整优先级。",
                "threads"
            )

    def _check_memory_faults(self, parsed: Dict) -> None:
        """检查内存缺页"""
        minflt = parsed.get('minflt', 0)
        majflt = parsed.get('majflt', 0)

        if majflt > 100:
            self.add_issue(
                "warning",
                "主要缺页中断过多",
                f"主要缺页中断: {majflt}，可能导致内存抖动"
            )
            self.add_suggestion(
                "内存访问优化",
                "主要缺页中断过多表示频繁访问未在内存中的页面。",
                "考虑使用内存池、预分配内存或madvise调整内存策略。"
            )

    def _check_threading(self, parsed: Dict) -> None:
        """检查线程信息"""
        num_threads = parsed.get('num_threads', 0)
        if num_threads > 32:
            self.add_suggestion(
                "线程数过多",
                f"当前线程数: {num_threads}",
                "过多线程会增加调度开销，考虑使用线程池或工作队列模式。",
                "threads"
            )

    def score(self) -> float:
        """计算进程状态评分"""
        score = 100.0
        stat_content = self.get_file_content("app_stat.txt")

        if not stat_content or stat_content == "N/A":
            return score

        parsed = self._parse_stat(stat_content)
        if not parsed:
            return score

        # 进程状态扣分
        state = parsed.get('state', '')
        if state in ['D', 'Z']:
            score -= 30
        elif state == 'T':
            score -= 10

        # 内核态CPU占用扣分
        utime = parsed.get('utime', 0)
        stime = parsed.get('stime', 0)
        if utime + stime > 0:
            kernel_ratio = stime / (utime + stime)
            if kernel_ratio > 0.5:
                score -= 15

        # 线程数扣分
        num_threads = parsed.get('num_threads', 0)
        if num_threads > 32:
            score -= min(20, (num_threads - 32) * 2)

        return max(0, min(100, score))

    def get_formatted_stats(self) -> Dict:
        """
        获取格式化的统计数据，用于报告展示

        Returns:
            包含可读格式的统计数据
        """
        stat_content = self.get_file_content("app_stat.txt")
        if not stat_content or stat_content == "N/A":
            return {}

        parsed = self._parse_stat(stat_content)
        if not parsed:
            return {}

        # 计算CPU时间
        clk_tck = self._get_clock_ticks()
        utime_sec = parsed.get('utime', 0) / clk_tck
        stime_sec = parsed.get('stime', 0) / clk_tck

        return {
            'comm': parsed.get('comm', 'N/A'),
            'state': parsed.get('state', 'N/A'),
            'state_desc': self.STATE_DESCRIPTIONS.get(parsed.get('state', ''), '未知'),
            'ppid': parsed.get('ppid', 0),
            'num_threads': parsed.get('num_threads', 0),
            'nice': parsed.get('nice', 0),
            'priority': parsed.get('priority', 0),
            'utime': f"{utime_sec:.2f}s",
            'stime': f"{stime_sec:.2f}s",
            'total_cpu_time': f"{utime_sec + stime_sec:.2f}s",
            'minflt': parsed.get('minflt', 0),
            'majflt': parsed.get('majflt', 0),
            'vsize_mb': parsed.get('vsize', 0) / 1024 / 1024,
            'rss_pages': parsed.get('rss', 0),
            'processor': parsed.get('processor', 0),
            'rt_priority': parsed.get('rt_priority', 0),
            'policy': self._get_policy_name(parsed.get('policy', 0)),
        }

    def _get_policy_name(self, policy: int) -> str:
        """获取调度策略名称"""
        policies = {
            0: 'SCHED_NORMAL',
            1: 'SCHED_FIFO',
            2: 'SCHED_RR',
            3: 'SCHED_BATCH',
            5: 'SCHED_IDLE',
            6: 'SCHED_DEADLINE',
        }
        return policies.get(policy, f'UNKNOWN({policy})')

    def get_raw_stat(self) -> str:
        """获取原始stat内容"""
        return self.get_file_content("app_stat.txt")
