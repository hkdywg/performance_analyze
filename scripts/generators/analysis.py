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



class MemoryAnalysisGenerator(BaseHtmlGenerator):
    """内存分析HTML生成器"""

    VM_FIELDS = {
        'VmPeak': ('峰值虚拟内存', 'KB'),
        'VmSize': ('当前虚拟内存', 'KB'),
        'VmLck': ('已锁定内存', 'KB'),
        'VmPin': ('固定内存', 'KB'),
        'VmRSS': ('物理内存使用', 'KB'),
        'RssAnon': ('匿名映射内存', 'KB'),
        'RssFile': ('文件映射内存', 'KB'),
        'RssShmem': ('共享内存', 'KB'),
        'VmData': ('数据段(堆)', 'KB'),
        'VmStk': ('栈大小', 'KB'),
        'VmExe': ('代码段', 'KB'),
        'VmLib': ('共享库', 'KB'),
        'VmPTE': ('页表大小', 'KB'),
        'VmSwap': ('交换到磁盘', 'KB'),
        'Threads': ('线程数', ''),
        'FDSize': ('文件描述符数', ''),
    }

    def generate(self) -> str:
        return self._generate_memory_analysis_section()

    def _format_kb(self, kb: int) -> str:
        if kb >= 1024 * 1024:
            return f"{kb / 1024 / 1024:.2f} GB"
        elif kb >= 1024:
            return f"{kb / 1024:.2f} MB"
        else:
            return f"{kb} KB"

    def _parse_meminfo(self, content: str) -> Dict:
        result = {}
        key_map = {
            'MemTotal': 'total', 'MemFree': 'free', 'MemAvailable': 'available',
            'Buffers': 'buffers', 'Cached': 'cached', 'SwapCached': 'swap_cached',
            'Active': 'active', 'Inactive': 'inactive', 'SwapTotal': 'swap_total',
            'SwapFree': 'swap_free', 'Dirty': 'dirty', 'Writeback': 'writeback',
            'AnonPages': 'anon_pages', 'Mapped': 'mapped', 'Shmem': 'shmem',
            'KReclaimable': 'reclaimable', 'SReclaimable': 's_reclaimable',
            'SUnreclaim': 's_unreclaim',
        }
        for line in content.split('\n'):
            for key, alias in key_map.items():
                if line.startswith(key):
                    match = re.search(r':\s*(\d+)', line)
                    if match:
                        result[alias] = int(match.group(1))
        return result

    def _parse_process_status(self, content: str) -> Dict:
        result = {}
        for line in content.split('\n'):
            for field in self.VM_FIELDS.keys():
                if line.startswith(field):
                    match = re.search(r':\s*(\d+)', line)
                    if match:
                        result[field] = int(match.group(1))
        return result

    def _parse_smaps_rollup(self, content: str) -> Dict:
        result = {}
        key_map = {
            'Rss': 'rss', 'Pss': 'pss', 'Pss_Anon': 'pss_anon',
            'Pss_File': 'pss_file', 'Pss_Shmem': 'pss_shmem',
            'Shared_Clean': 'shared_clean', 'Shared_Dirty': 'shared_dirty',
            'Private_Clean': 'private_clean', 'Private_Dirty': 'private_dirty',
            'Referenced': 'referenced', 'Anonymous': 'anonymous',
            'LazyFree': 'lazy_free', 'AnonHugePages': 'anon_huge_pages',
            'ShmemPmdMapped': 'shmem_pmd_mapped', 'Shared_Hugetlb': 'shared_hugetlb',
            'Private_Hugetlb': 'private_hugetlb', 'Swap': 'swap',
            'SwapPss': 'swap_pss', 'Locked': 'locked',
        }
        for line in content.split('\n'):
            for key, alias in key_map.items():
                if line.startswith(key):
                    match = re.search(r':\s*(\d+)', line)
                    if match:
                        result[alias] = int(match.group(1))
        return result

    def _parse_vmstat(self, content: str) -> Dict:
        result = {}
        lines = content.strip().split('\n')
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('procs') or stripped.startswith('r '):
                continue
            fields = stripped.split()
            if len(fields) >= 17:
                try:
                    result['r'] = int(fields[0])
                    result['b'] = int(fields[1])
                    result['swpd'] = int(fields[2])
                    result['free'] = int(fields[3])
                    result['buff'] = int(fields[4])
                    result['cache'] = int(fields[5])
                    result['si'] = int(fields[6])
                    result['so'] = int(fields[7])
                    result['bi'] = int(fields[8])
                    result['bo'] = int(fields[9])
                    result['us'] = int(fields[12]) if len(fields) > 12 else 0
                    result['sy'] = int(fields[13]) if len(fields) > 13 else 0
                    result['id'] = int(fields[14]) if len(fields) > 14 else 0
                    result['wa'] = int(fields[15]) if len(fields) > 15 else 0
                except (ValueError, IndexError):
                    pass
        return result

    def _generate_memory_analysis_section(self) -> str:
        meminfo = self.get_file_content("meminfo.txt")
        proc_detail = self.get_file_content("process_memory_detail.txt")
        vmstat = self.get_file_content("vmstat.txt")

        if not meminfo or meminfo == "N/A":
            return """<section id="memory-analysis" class="card">
            <h2>内存分析</h2>
            <div class="no-data">暂无内存数据</div>
        </section>"""

        sys_mem = self._parse_meminfo(meminfo)
        vmstat_data = self._parse_vmstat(vmstat)
        proc_mem = {}
        smaps_rollup = None
        pss_kb = 0

        if proc_detail and proc_detail != "N/A":
            proc_mem = self._parse_process_status(proc_detail)
            smaps_section = ""
            in_smaps = False
            for line in proc_detail.split('\n'):
                if '=== Memory Smaps Rollup ===' in line:
                    in_smaps = True
                    smaps_section = ""
                    continue
                if in_smaps:
                    if line.startswith('==='):
                        break
                    smaps_section += line + "\n"
            if smaps_section.strip():
                smaps_rollup = self._parse_smaps_rollup(smaps_section)
                pss_kb = smaps_rollup.get('pss', 0)
            if pss_kb == 0:
                for line in proc_detail.split('\n'):
                    if 'Total Pss:' in line:
                        match = re.search(r'Total Pss:\s*(\d+)', line)
                        if match:
                            pss_kb = int(match.group(1))

        total_kb = sys_mem.get('total', 0)
        free_kb = sys_mem.get('free', 0)
        avail_kb = sys_mem.get('available', 0)
        used_kb = total_kb - avail_kb
        buffers_kb = sys_mem.get('buffers', 0)
        cached_kb = sys_mem.get('cached', 0)
        swap_total_kb = sys_mem.get('swap_total', 0)
        swap_free_kb = sys_mem.get('swap_free', 0)
        swap_used_kb = swap_total_kb - swap_free_kb
        mem_usage_pct = (used_kb / total_kb * 100) if total_kb > 0 else 0

        vm_rss_kb = proc_mem.get('VmRSS', 0)
        vm_size_kb = proc_mem.get('VmSize', 0)
        vm_data_kb = proc_mem.get('VmData', 0)
        vm_swap_kb = proc_mem.get('VmSwap', 0)
        vm_peak_kb = proc_mem.get('VmPeak', 0)
        rss_anon = proc_mem.get('RssAnon', 0)
        rss_file = proc_mem.get('RssFile', 0)

        # 计算目标进程占系统内存的比例
        proc_mem_pct = (vm_rss_kb / total_kb * 100) if total_kb > 0 else 0
        vsz_rss_ratio = vm_size_kb / max(1, vm_rss_kb)
        swap_usage_pct = (swap_used_kb / swap_total_kb * 100) if swap_total_kb > 0 else 0
        s_reclaimable_kb = sys_mem.get('s_reclaimable', 0)

        html = '<section id="memory-analysis" class="card">'
        html += '<h2>内存分析</h2>'
        html += '<h3>系统内存概览</h3>'
        html += '<div class="grid">'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(total_kb)}</div><div class="label">物理内存总量</div></div>'
        html += f'<div class="stat-box"><div class="value">{mem_usage_pct:.1f}%</div><div class="label">内存使用率</div></div>'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(avail_kb)}</div><div class="label">可用内存</div></div>'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(vm_rss_kb)}</div><div class="label">目标进程RSS</div></div>'
        html += '</div>'

        html += '<h3>系统内存使用分布</h3>'
        html += '<table><thead><tr><th>类型</th><th>大小</th><th>说明</th></tr></thead><tbody>'
        html += f'<tr><td>内核缓冲区</td><td>{self._format_kb(buffers_kb)}</td><td>块设备缓冲区</td></tr>'
        html += f'<tr><td>页缓存</td><td>{self._format_kb(cached_kb)}</td><td>文件页缓存（包括共享库）</td></tr>'
        html += f'<tr><td>SReclaimable</td><td>{self._format_kb(s_reclaimable_kb)}</td><td>可回收的Slab内存</td></tr>'
        html += f'<tr><td>空闲内存</td><td>{self._format_kb(free_kb)}</td><td>完全空闲的内存</td></tr>'
        if swap_total_kb > 0:
            html += f'<tr><td>Swap已用/总量</td><td>{self._format_kb(swap_used_kb)} / {self._format_kb(swap_total_kb)}</td><td>使用率 {swap_usage_pct:.1f}%</td></tr>'
        html += '</tbody></table>'

        html += '<h3>目标进程内存占用</h3>'
        html += f'<p style="color:#666;font-size:12px;margin-bottom:10px;">目标进程RSS占系统内存的 {proc_mem_pct:.1f}%</p>'
        html += '<div class="grid">'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(vm_rss_kb)}</div><div class="label">物理内存 (RSS)</div></div>'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(vm_size_kb)}</div><div class="label">虚拟内存 (VSZ)</div></div>'
        html += f'<div class="stat-box"><div class="value">{vsz_rss_ratio:.2f}x</div><div class="label">VSZ/RSS比率</div></div>'
        html += f'<div class="stat-box"><div class="value">{self._format_kb(pss_kb)}</div><div class="label">PSS内存</div></div>'
        html += '</div>'

        html += '<h4>进程内存类型详解</h4>'
        html += '<table><thead><tr><th>内存类型</th><th>当前值</th><th>说明</th></tr></thead><tbody>'
        html += f'<tr><td>VmRSS</td><td>{self._format_kb(vm_rss_kb)}</td><td>物理内存使用（实际占用RAM）</td></tr>'
        html += f'<tr><td>RssAnon</td><td>{self._format_kb(rss_anon)}</td><td>匿名映射内存（堆、栈等）</td></tr>'
        html += f'<tr><td>RssFile</td><td>{self._format_kb(rss_file)}</td><td>文件映射内存（共享库、mmap文件）</td></tr>'
        html += f'<tr><td>VmData</td><td>{self._format_kb(vm_data_kb)}</td><td>数据段大小（堆）</td></tr>'
        html += f'<tr><td>VmStk</td><td>{self._format_kb(proc_mem.get("VmStk", 0))}</td><td>栈大小</td></tr>'
        html += f'<tr><td>VmExe</td><td>{self._format_kb(proc_mem.get("VmExe", 0))}</td><td>代码段大小</td></tr>'
        html += f'<tr><td>VmLib</td><td>{self._format_kb(proc_mem.get("VmLib", 0))}</td><td>共享库大小</td></tr>'
        html += f'<tr><td>VmPeak</td><td>{self._format_kb(vm_peak_kb)}</td><td>峰值虚拟内存</td></tr>'
        html += f'<tr><td>VmSwap</td><td>{self._format_kb(vm_swap_kb)}</td><td>交换到磁盘的内存</td></tr>'
        html += f'<tr><td>VmLck</td><td>{self._format_kb(proc_mem.get("VmLck", 0))}</td><td>已锁定的内存（mlock）</td></tr>'
        html += '</tbody></table>'

        if smaps_rollup and pss_kb > 0:
            private_clean = smaps_rollup.get('private_clean', 0)
            private_dirty = smaps_rollup.get('private_dirty', 0)
            shared_clean = smaps_rollup.get('shared_clean', 0)
            shared_dirty = smaps_rollup.get('shared_dirty', 0)
            swap_kb = smaps_rollup.get('swap', 0)
            anon_huge = smaps_rollup.get('anon_huge_pages', 0)
            html += '<h3>PSS内存详细分析</h3>'
            html += '<p style="color:#666;font-size:12px;margin-bottom:10px;">PSS (Proportional Set Size): 按比例分摊共享库的内存，计算方式为：私有内存 + 共享内存/共享次数</p>'
            html += '<table><thead><tr><th>类型</th><th>大小</th><th>说明</th></tr></thead><tbody>'
            html += f'<tr><td>Total PSS</td><td>{self._format_kb(pss_kb)}</td><td>比例分摊后的总内存</td></tr>'
            html += f'<tr><td>Private Clean</td><td>{self._format_kb(private_clean)}</td><td>私有干净内存（可回收）</td></tr>'
            html += f'<tr><td>Private Dirty</td><td>{self._format_kb(private_dirty)}</td><td>私有脏内存（不可回收）</td></tr>'
            html += f'<tr><td>Shared Clean</td><td>{self._format_kb(shared_clean)}</td><td>共享干净内存</td></tr>'
            html += f'<tr><td>Shared Dirty</td><td>{self._format_kb(shared_dirty)}</td><td>共享脏内存</td></tr>'
            html += f'<tr><td>Swap</td><td>{self._format_kb(swap_kb)}</td><td>换出到swap的内存</td></tr>'
            if anon_huge > 0:
                html += f'<tr><td>AnonHugePages</td><td>{self._format_kb(anon_huge)}</td><td>透明大页（THP）内存</td></tr>'
            html += '</tbody></table>'

        if vmstat_data:
            html += '<h3>虚拟内存活动</h3>'
            html += '<div class="grid">'
            html += f'<div class="stat-box"><div class="value">{vmstat_data.get("r", "N/A")}</div><div class="label">运行中进程</div></div>'
            html += f'<div class="stat-box"><div class="value">{vmstat_data.get("b", "N/A")}</div><div class="label">阻塞进程</div></div>'
            html += f'<div class="stat-box"><div class="value">{vmstat_data.get("si", 0)} KB/s</div><div class="label">Swap换入</div></div>'
            html += f'<div class="stat-box"><div class="value">{vmstat_data.get("so", 0)} KB/s</div><div class="label">Swap换出</div></div>'
            html += '</div>'

        html += self._generate_memory_suggestions(sys_mem, proc_mem, vmstat_data, smaps_rollup)
        html += """        </section>
        """
        return html

    def _generate_memory_suggestions(self, sys_mem: Dict, proc_mem: Dict, vmstat: Dict, smaps) -> str:
        suggestions = []
        total_kb = sys_mem.get('total', 0)
        avail_kb = sys_mem.get('available', 0)
        used_kb = total_kb - avail_kb
        swap_used = sys_mem.get('swap_total', 0) - sys_mem.get('swap_free', 0)

        if total_kb > 0:
            usage_pct = (used_kb / total_kb) * 100
            if usage_pct > 90:
                suggestions.append(f"<strong>系统内存严重不足</strong>: 内存使用率已达{usage_pct:.1f}%，可用内存仅剩{avail_kb/1024:.0f}MB。建议增加物理内存或优化应用内存使用。")
            elif usage_pct > 80:
                suggestions.append(f"<strong>系统内存紧张</strong>: 内存使用率{usage_pct:.1f}%，建议关注内存泄漏风险。")

        if swap_used > 0:
            swap_total = sys_mem.get('swap_total', 0)
            swap_pct = (swap_used / swap_total * 100) if swap_total > 0 else 0
            if swap_pct > 50:
                suggestions.append(f"<strong>Swap使用过多</strong>: 已使用{swap_used/1024:.0f}MB Swap ({swap_pct:.1f}%)，存在严重内存压力。")
            else:
                suggestions.append(f"<strong>使用Swap</strong>: 已使用{swap_used/1024:.0f}MB Swap，存在一定内存压力。")

        vm_rss_kb = proc_mem.get('VmRSS', 0)
        vm_size_kb = proc_mem.get('VmSize', 0)
        vm_data_kb = proc_mem.get('VmData', 0)

        if vm_rss_kb > 0 and total_kb > 0:
            rss_pct = (vm_rss_kb / total_kb) * 100
            if rss_pct > 50:
                suggestions.append(f"<strong>进程内存占用过高</strong>: RSS占用{vm_rss_kb/1024:.0f}MB，达系统内存{rss_pct:.1f}%。")

        if vm_size_kb > 0 and vm_rss_kb > 0:
            vsz_rss_ratio = vm_size_kb / vm_rss_kb
            if vsz_rss_ratio > 10:
                suggestions.append(f"<strong>内存碎片化或预分配</strong>: VSZ/RSS比率高达{vsz_rss_ratio:.1f}x，存在大量虚拟内存但未实际使用。")

        if vm_data_kb > 100 * 1024:
            suggestions.append(f"<strong>堆内存较大</strong>: VmData={vm_data_kb/1024:.0f}MB，可能存在内存分配优化空间。")

        if vmstat:
            si = vmstat.get('si', 0)
            so = vmstat.get('so', 0)
            if si > 1000:
                suggestions.append(f"<strong>频繁Swap换入</strong>: {si}KB/s 从Swap换入内存，可能存在内存不足。")
            if so > 1000:
                suggestions.append(f"<strong>频繁Swap换出</strong>: {so}KB/s 将内存换出到Swap，物理内存不足。")

        if smaps:
            private_dirty = smaps.get('private_dirty', 0)
            swap = smaps.get('swap', 0)
            if private_dirty > 50 * 1024:
                suggestions.append(f"<strong>私有脏内存较多</strong>: {private_dirty/1024:.0f}MB 私有脏内存无法被回收，考虑优化数据结构。")
            if swap > 10 * 1024:
                suggestions.append(f"<strong>内存被换出</strong>: {swap/1024:.0f}MB 内存被换出到Swap，可能导致性能下降。")

        if not suggestions:
            suggestions.append("<strong>内存状态良好</strong>: 未检测到明显的内存问题。")
        suggestions.append("<strong>优化建议</strong>: 1) 检查内存泄漏 2) 优化数据结构减少内存占用 3) 使用内存池 4) 及时释放不需要的内存 5) 考虑使用共享内存")

        suggestions_html = '<div class="suggestion"><h4>内存优化建议</h4><ul>'
        for s in suggestions:
            suggestions_html += f'<li>{s}</li>'
        suggestions_html += '</ul></div>'
        return suggestions_html


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
                    read_rate = float(parts[4]) if parts[4] not in ['N/A', ''] else None
                    write_rate = float(parts[5]) if parts[5] not in ['N/A', ''] else None

                    times.append(time)
                    if read_rate is not None and read_rate >= 0:
                        read_rates.append(read_rate)
                    if write_rate is not None and write_rate >= 0:
                        write_rates.append(write_rate)
                    
                    # 解析IO系统调用差值 (在第9和第10列)
                    if len(parts) >= 10:
                        syscr_diff = int(parts[8]) if parts[8] not in ['N/A', ''] else None
                        syscw_diff = int(parts[9]) if parts[9] not in ['N/A', ''] else None
                        if syscr_diff is not None and syscr_diff >= 0:
                            syscr_diffs.append(syscr_diff)
                        if syscw_diff is not None and syscw_diff >= 0:
                            syscw_diffs.append(syscw_diff)
                except (ValueError, IndexError):
                    continue

        if not read_rates and not write_rates and not syscr_diffs and not syscw_diffs:
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
            # IO系统调用差值统计
            'syscr_diffs': syscr_diffs,
            'syscw_diffs': syscw_diffs,
            'total_syscr_diff': sum(syscr_diffs) if syscr_diffs else 0,
            'total_syscw_diff': sum(syscw_diffs) if syscw_diffs else 0,
            'avg_syscr_diff': sum(syscr_diffs) / len(syscr_diffs) if syscr_diffs else 0,
            'avg_syscw_diff': sum(syscw_diffs) / len(syscw_diffs) if syscw_diffs else 0,
            'max_syscr_diff': max(syscr_diffs) if syscr_diffs else 0,
            'max_syscw_diff': max(syscw_diffs) if syscw_diffs else 0,
        }

    def _generate_io_analysis_section(self) -> str:
        """生成I/O性能分析章节"""
        # 优先使用 io_samples.csv（包含更多IO信息），其次使用 perf_samples.csv
        io_csv_content = self.get_file_content("io_samples.csv")
        if not io_csv_content or io_csv_content == "N/A":
            io_csv_content = self.get_file_content("perf_samples.csv")
        
        csv_content = io_csv_content
        io_content = self.get_file_content("app_io.txt")
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

        # 获取采样期间的IO统计
        sampling_stats = ""
        if io_rates:
            sampling_stats = f"""
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{io_rates['sample_count']}</div>
                    <div class="label">采样次数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_rates['total_syscr_diff']:,}</div>
                    <div class="label">采样读调用差值</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_rates['total_syscw_diff']:,}</div>
                    <div class="label">采样写调用差值</div>
                </div>
                <div class="stat-box">
                    <div class="value">{io_rates['avg_syscr_diff']:.1f}</div>
                    <div class="label">平均读调用/次</div>
                </div>
            </div>
"""

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
            </div>
"""

        # 如果有采样数据，添加采样期间的IO统计
        if sampling_stats:
            html += f"""
            <h3>采样期间I/O统计</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>读取</th>
                        <th>写入</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>采样期间系统调用总数</td>
                        <td>{io_rates['total_syscr_diff']:,} 次</td>
                        <td>{io_rates['total_syscw_diff']:,} 次</td>
                    </tr>
                    <tr>
                        <td>平均每次采样调用</td>
                        <td>{io_rates['avg_syscr_diff']:.1f} 次</td>
                        <td>{io_rates['avg_syscw_diff']:.1f} 次</td>
                    </tr>
                    <tr>
                        <td>最大单次采样调用</td>
                        <td>{io_rates['max_syscr_diff']} 次</td>
                        <td>{io_rates['max_syscw_diff']} 次</td>
                    </tr>
                    <tr>
                        <td>平均IO速率</td>
                        <td>{io_rates['avg_read']/1024:.2f} MB/s</td>
                        <td>{io_rates['avg_write']/1024:.2f} MB/s</td>
                    </tr>
                    <tr>
                        <td>峰值IO速率</td>
                        <td>{io_rates['max_read']/1024:.2f} MB/s</td>
                        <td>{io_rates['max_write']/1024:.2f} MB/s</td>
                    </tr>
                </tbody>
            </table>
"""

        html += f"""
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

        # 添加优化建议
        html += self._generate_io_suggestions(io_data, io_rates, io_wait)

        html += """
        </section>
        """
        return html

    def _extract_io_wait(self, vmstat: str) -> str:
        """
        提取I/O等待时间
        
        vmstat 标准格式: procs r b swpd free buff cache si so bi bo in cs us sy id wa st
        字段数: 17 (索引0-16)
        
        本脚本生成格式: "      0  0  0 643628 1432 28888    0    0     0     0     0     0   0   0  100   0   0"
        分割后有18个字段，wa在索引16
        
        wa值应该是0-100的百分比，不是free列的1432
        """
        if not vmstat:
            return "N/A"
        
        lines = vmstat.strip().split('\n')
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # 跳过表头行
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
                        return str(wa)
                except (ValueError, IndexError):
                    pass
            # 标准vmstat格式(17字段): wa在索引15
            elif len(fields) == 17:
                try:
                    wa = int(fields[15])
                    if 0 <= wa <= 100:
                        return str(wa)
                except (ValueError, IndexError):
                    pass
            # 其他情况
            elif len(fields) >= 16:
                try:
                    wa = int(fields[15])
                    if 0 <= wa <= 100:
                        return str(wa)
                except (ValueError, IndexError):
                    pass
        
        return "N/A"

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
                suggestions.append("<strong>读密集型应用</strong>: 读取量远大于读取，建议增加缓存提高读取性能。")

        # 累计IO量分析
        total_io = read_bytes + write_bytes
        if total_io > 1024 * 1024 * 1024:  # > 1GB
            suggestions.append(f"<strong>高I/O应用</strong>: 累计I/O量超过1GB ({total_io/1024/1024/1024:.2f}GB)，建议优化I/O模式或使用更快存储。")

        # 采样期间IO系统调用差值分析
        if io_rates:
            # 读系统调用差值分析
            if io_rates['total_syscr_diff'] > 10000:
                suggestions.append(f"<strong>采样期间读系统调用频繁</strong>: 共{io_rates['total_syscr_diff']:,}次，平均每次采样{io_rates['avg_syscr_diff']:.1f}次。建议使用缓冲I/O减少系统调用。")
            
            # 写系统调用差值分析
            if io_rates['total_syscw_diff'] > 10000:
                suggestions.append(f"<strong>采样期间写系统调用频繁</strong>: 共{io_rates['total_syscw_diff']:,}次，平均每次采样{io_rates['avg_syscw_diff']:.1f}次。建议使用缓冲写或批量写入。")

            # IO速率峰值分析
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


class LockAnalysisGenerator(BaseHtmlGenerator):
    """锁分析HTML生成器 - 使用perf lock命令分析锁争用"""

    def generate(self) -> str:
        return self._generate_lock_analysis_section()

    def _parse_lock_report(self, content: str) -> dict:
        """解析perf lock report输出"""
        result = {
            'locks': [],
            'total_count': 0,
            'has_content': False,
        }
        
        if not content or content == "N/A" or not content.strip():
            return result
        
        result['has_content'] = True
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和表头
            if not line or line.startswith('Name') or line.startswith('===') or line.startswith('Total') or line.startswith('Samples'):
                continue
            
            # 解析锁信息行
            # 格式: Name  %t   %m    Avg   wait_index  wait +  morsels  idx  contentions  call_site
            # 例如: &inode->i_lock  0.01  100.00   0.00    0.00   0.00 +    0.00     1     1         0xffffffff81234567
            parts = line.split()
            if len(parts) >= 10:
                try:
                    lock_info = {
                        'name': parts[0],
                        'time_pct': float(parts[1]) if parts[1] != 'N/A' else 0,
                        'avg_wait': float(parts[4]) if parts[4] != 'N/A' else 0,
                        'contentions': int(parts[8]) if parts[8] != 'N/A' else 0,
                        'call_site': parts[9] if len(parts) > 9 else '',
                    }
                    result['locks'].append(lock_info)
                    result['total_count'] += 1
                except (ValueError, IndexError):
                    continue
        
        return result

    def _parse_lock_contention(self, content: str) -> dict:
        """解析perf lock contention输出"""
        result = {
            'contentions': [],
            'total': 0,
        }
        
        if not content or content == "N/A" or not content.strip():
            return result
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和表头
            if not line or line.startswith('Name') or line.startswith('==='):
                continue
            
            parts = line.split()
            if len(parts) >= 3:
                try:
                    contention = {
                        'name': parts[0],
                        'type': parts[1] if len(parts) > 1 else '',
                        'calls': int(parts[2]) if parts[2].isdigit() else 0,
                    }
                    result['contentions'].append(contention)
                    result['total'] += contention['calls']
                except (ValueError, IndexError):
                    continue
        
        return result

    def _generate_lock_analysis_section(self) -> str:
        """生成锁分析章节"""
        lock_report = self.get_file_content("perf_lock.txt")
        lock_contention = self.get_file_content("lock_contention.txt")

        if not lock_report or lock_report == "N/A" or not lock_report.strip():
            return """
        <section id="lock-analysis" class="card">
            <h2>锁分析</h2>
            <div class="no-data">暂无锁分析数据（perf lock需要root权限）</div>
        </section>
            """

        # 解析锁数据
        lock_data = self._parse_lock_report(lock_report)
        contention_data = self._parse_lock_contention(lock_contention if lock_contention else lock_report)

        if not lock_data['has_content'] or not lock_data['locks']:
            return """
        <section id="lock-analysis" class="card">
            <h2>锁分析</h2>
            <div class="no-data">锁分析数据为空或操作系统未开启LOCKDEP</div>
        </section>
            """

        # 获取热点锁
        hot_locks = sorted(lock_data['locks'], key=lambda x: x['contentions'], reverse=True)[:10]
        critical_locks = [l for l in lock_data['locks'] if l['time_pct'] > 1.0][:5]

        # 生成热点锁表格
        hot_locks_table = self._generate_hot_locks_table(hot_locks)

        # 生成分析建议
        suggestions_html = self._generate_lock_suggestions(lock_data, contention_data)

        html = f"""
        <section id="lock-analysis" class="card">
            <h2>锁分析</h2>
            
            <div class="grid">
                <div class="stat-box">
                    <div class="value">{lock_data['total_count']}</div>
                    <div class="label">检测到的锁数量</div>
                </div>
                <div class="stat-box">
                    <div class="value">{contention_data['total']}</div>
                    <div class="label">总争用次数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{len(critical_locks)}</div>
                    <div class="label">热点锁数量</div>
                </div>
            </div>
"""

        # 如果有热点锁，显示详细信息
        if hot_locks:
            html += f"""
            <h3>锁争用排名 (Top 10)</h3>
            {hot_locks_table}
"""

        # 添加完整的锁列表
        if lock_data['locks']:
            html += f"""
            <h3>所有锁详情</h3>
            <details>
                <summary style="cursor:pointer;padding:10px;background:#f5f5f5;border-radius:5px;">
                    点击展开完整锁列表 ({len(lock_data['locks'])} 个)
                </summary>
                <div style="margin-top:10px;max-height:400px;overflow-y:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>锁名称</th>
                                <th>时间占比(%)</th>
                                <th>平均等待(ms)</th>
                                <th>争用次数</th>
                                <th>调用点</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            for lock in lock_data['locks']:
                html += f"""
                            <tr>
                                <td style="word-break:break-all;">{lock['name']}</td>
                                <td>{lock['time_pct']:.2f}</td>
                                <td>{lock['avg_wait']:.2f}</td>
                                <td>{lock['contentions']}</td>
                                <td style="word-break:break-all;font-size:12px;">{lock['call_site']}</td>
                            </tr>
"""
            html += """
                        </tbody>
                    </table>
                </div>
            </details>
"""

        html += f"""
            <h3>锁分析</h3>
            {suggestions_html}
        </section>
        """
        return html

    def _generate_hot_locks_table(self, hot_locks: list) -> str:
        """生成热点锁表格"""
        if not hot_locks:
            return "<p>无热点锁数据</p>"
        
        rows = ""
        for i, lock in enumerate(hot_locks, 1):
            # 根据争用次数设置警告级别
            warning_class = ""
            if lock['contentions'] > 1000:
                warning_class = "status error"
            elif lock['contentions'] > 100:
                warning_class = "status warning"
            
            rows += f"""
                <tr>
                    <td>{i}</td>
                    <td style="word-break:break-all;">{lock['name']}</td>
                    <td><span class="{warning_class}">{lock['contentions']}</span></td>
                    <td>{lock['time_pct']:.2f}</td>
                    <td>{lock['avg_wait']:.2f}</td>
                </tr>
"""
        
        return f"""
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>锁名称</th>
                        <th>争用次数</th>
                        <th>时间占比(%)</th>
                        <th>平均等待(ms)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
"""

    def _generate_lock_suggestions(self, lock_data: dict, contention_data: dict) -> str:
        """生成锁分析建议"""
        suggestions = []
        
        # 分析热点锁
        hot_locks = sorted(lock_data['locks'], key=lambda x: x['contentions'], reverse=True)
        
        if hot_locks:
            top_lock = hot_locks[0]
            if top_lock['contentions'] > 1000:
                suggestions.append(
                    f"<strong>严重锁争用</strong>: 锁 <code>{top_lock['name']}</code> 争用次数达到 "
                    f"{top_lock['contentions']:,} 次，是主要的性能瓶颈。建议优化锁的使用方式。"
                )
            elif top_lock['contentions'] > 100:
                suggestions.append(
                    f"<strong>存在锁争用</strong>: 锁 <code>{top_lock['name']}</code> 争用次数为 "
                    f"{top_lock['contentions']} 次，建议关注。"
                )
        
        # 分析高等待时间锁
        long_wait_locks = [l for l in lock_data['locks'] if l['avg_wait'] > 10]
        if long_wait_locks:
            suggestions.append(
                f"<strong>锁等待时间长</strong>: 检测到 {len(long_wait_locks)} 个锁的平均等待时间超过10ms，"
                f"可能导致线程阻塞。建议检查锁持有时间和锁粒度。"
            )
        
        # 分析高时间占比锁
        time_locks = [l for l in lock_data['locks'] if l['time_pct'] > 5]
        if time_locks:
            suggestions.append(
                f"<strong>高占用锁</strong>: {time_locks[0]['name']} 占用了 {time_locks[0]['time_pct']:.2f}% 的时间，"
                f"需要重点优化。"
            )
        
        # 性能优化建议
        if lock_data['total_count'] > 50:
            suggestions.append(
                f"<strong>锁数量较多</strong>: 检测到 {lock_data['total_count']} 个不同的锁，"
                f"建议评估是否可以合并或减少锁的使用。"
            )
        
        # 通用优化建议
        if not suggestions:
            suggestions.append("<strong>锁状态正常</strong>: 未检测到明显的锁争用问题。")
        
        # 添加通用优化建议
        suggestions.append(
            "<strong>优化建议</strong>: "
            "1) 减少锁的持有时间 2) 减小锁的粒度 3) 使用读写锁替代互斥锁 "
            "4) 考虑无锁数据结构 5) 避免在锁内执行耗时操作"
        )
        
        suggestions_html = '<div class="suggestion"><ul>'
        for s in suggestions:
            suggestions_html += f'<li>{s}</li>'
        suggestions_html += '</ul></div>'
        return suggestions_html
