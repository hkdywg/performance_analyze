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

    def _parse_smaps_by_filetype(self, content: str, exe_path: str = None) -> Dict:
        """
        解析smaps，按文件类型统计RSS物理内存

        通过解析/proc/{pid}/smaps，可以获取每个内存区域的：
        - 文件路径
        - 该区域的RSS物理内存占用

        Args:
            content: smaps文件内容
            exe_path: 可执行文件路径（用于识别代码段）

        Returns:
            包含RssExe, RssLib, RssFile统计的字典（单位KB）
        """
        result = {
            'rss_exe': 0,    # 代码段RSS
            'rss_lib': 0,    # 共享库RSS
            'rss_file': 0,   # 其他文件映射RSS
        }

        if not content:
            return result

        current_file = None
        current_rss = 0

        for line in content.split('\n'):
            line = line.strip()

            # 检测到新的内存区域开始（地址范围行）
            if re.match(r'^[0-9a-fA-F]+-[0-9a-fA-F]+', line):
                # 处理上一个区域的RSS
                if current_file is not None and current_rss > 0:
                    # 代码段：路径中包含可执行文件名
                    is_exe = exe_path and exe_path.split('/')[-1] in current_file
                    # 共享库：以.so结尾的文件（不包括包含.so的非库文件）
                    is_shared_lib = current_file.endswith('.so') or bool(re.search(r'\.so\.[0-9.]+$', current_file))

                    if is_exe:
                        result['rss_exe'] += current_rss
                    elif is_shared_lib:
                        result['rss_lib'] += current_rss
                    elif current_file:  # 非空路径且非可执行文件/共享库
                        result['rss_file'] += current_rss

                # 解析新区域的路径
                current_file = None
                current_rss = 0
                parts = line.split()
                if len(parts) >= 6:
                    pathname = parts[5]
                    if pathname and not pathname.startswith('['):
                        current_file = pathname

            # 检测到RSS行
            elif line.startswith('Rss:'):
                match = re.search(r':\s*(\d+)', line)
                if match:
                    current_rss = int(match.group(1))

        # 处理最后一个区域
        if current_file is not None and current_rss > 0:
            # 代码段：路径中包含可执行文件名
            is_exe = exe_path and exe_path.split('/')[-1] in current_file
            # 共享库：以.so结尾的文件
            is_shared_lib = current_file.endswith('.so') or bool(re.search(r'\.so\.[0-9.]+$', current_file))

            if is_exe:
                result['rss_exe'] += current_rss
            elif is_shared_lib:
                result['rss_lib'] += current_rss
            elif current_file:  # 非空路径且非可执行文件/共享库
                result['rss_file'] += current_rss

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

    def _parse_maps_classification(self, content: str) -> Dict:
        """解析内存映射分类数据"""
        result = {
            'heap': 0,
            'stack': 0,
            'anonymous': 0,
            'shared_lib': 0,
            'file_map': 0,
            'device': 0,
            'vdso': 0,
            'vsyscall': 0,
            'vvar': 0,
            'virtual_fs': 0,
            'other': 0,
            'major_regions': [],
        }
        if not content:
            return result

        lines = content.split('\n')
        in_major_regions = False
        for line in lines:
            line = line.strip()
            if '=== Major Memory Regions ===' in line:
                in_major_regions = True
                continue
            if '===' in line and in_major_regions:
                in_major_regions = False
                continue

            if in_major_regions:
                if line:
                    result['major_regions'].append(line)
                continue

            # 解析分类统计行
            if line.startswith('Heap:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['heap'] = int(match.group(1))
            elif line.startswith('Stack:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['stack'] = int(match.group(1))
            elif line.startswith('Anonymous:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['anonymous'] = int(match.group(1))
            elif line.startswith('Shared Libraries:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['shared_lib'] = int(match.group(1))
            elif line.startswith('File Mappings:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['file_map'] = int(match.group(1))
            elif line.startswith('Device Mappings:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['device'] = int(match.group(1))
            elif line.startswith('VDSO:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['vdso'] = int(match.group(1))
            elif line.startswith('VSyscall:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['vsyscall'] = int(match.group(1))
            elif line.startswith('VVar:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['vvar'] = int(match.group(1))
            elif line.startswith('Virtual FS:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['virtual_fs'] = int(match.group(1))
            elif line.startswith('Other:'):
                match = re.search(r'(\d+)', line)
                if match:
                    result['other'] = int(match.group(1))

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
        rss_shmem = proc_mem.get('RssShmem', 0)
        
        # 如果RssFile为0，使用RSS - RssAnon - RssShmem估算
        if rss_file == 0 and vm_rss_kb > 0:
            rss_file = max(0, vm_rss_kb - rss_anon - rss_shmem)

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

        # 进程内存饼图 - 显示包含关系
        # RSS = RssAnon + RssFile + RssShmem
        #   RssAnon = Heap(堆) + Stack(栈) + 匿名mmap
        #   RssFile = 代码段 + 共享库 + 其他文件映射
        #   RssShmem = 共享内存（System V IPC + mmap(MAP_SHARED)）
        # 注意：VmData是虚拟空间大小，RssAnon是物理内存中的匿名部分
        
        total_rss = rss_anon + rss_file + rss_shmem
        pie_labels = []
        pie_values = []
        pie_colors = []
        pie_hover_labels = []  # 显示详细说明
        
        if total_rss > 0:
            # 获取实际堆的物理内存占用（从smaps解析）
            heap_rss_kb = 0
            stack_rss_kb = 0
            anon_mmap_rss_kb = 0
            code_rss_kb = 0
            lib_rss_kb = 0
            file_mmap_rss_kb = 0
            
            proc_detail = self.get_file_content("process_memory_detail.txt")
            if proc_detail and proc_detail != "N/A":
                # 从smaps rollup中获取详细分解
                in_smaps = False
                smaps_section = ""
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
                    smaps_data = self._parse_smaps_rollup(smaps_section)
                    private_anon = smaps_data.get('private_anon', 0)
                    private_dirty = smaps_data.get('private_dirty', 0)
                    shared_anon = smaps_data.get('shared_anon', 0)
                    
                    # 匿名映射的RSS = RssAnon
                    # 但需要知道其中堆/栈/匿名mmap的具体分解
                    # 这里使用比例估算，或从maps解析
                    
                # 从process_memory_detail.txt中解析heap/stack的实际RSS
                # 格式类似: [heap]    1000    1000    4096    rw-p    00000000 00:00 0
                current_start = None
                current_end = None
                current_perms = None
                
                for line in proc_detail.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('===') or ':' not in line:
                        continue
                    
                    # 解析 maps 格式: start-end perms offset dev inode pathname
                    parts = line.split()
                    if len(parts) >= 5:
                        addr_range = parts[0]
                        perms = parts[1]
                        pathname = ' '.join(parts[5:]) if len(parts) > 5 else ''
                        
                        if '[heap]' in pathname:
                            # 这是堆，计算大小
                            try:
                                start, end = addr_range.split('-')
                                size = int(end, 16) - int(start, 16)
                                heap_rss_kb = size // 1024  # 虚拟大小近似RSS
                            except:
                                pass
                        elif '[stack]' in pathname:
                            try:
                                start, end = addr_range.split('-')
                                size = int(end, 16) - int(start, 16)
                                stack_rss_kb = size // 1024
                            except:
                                pass
                                
                # 如果从maps无法获取，使用比例估算
                # VmData包含堆，RssAnon是物理匿名内存
                # 实际场景中：RssAnon ≈ 堆的物理占用 + 栈占用 + 匿名mmap
                if heap_rss_kb == 0 and vm_data_kb > 0:
                    # 估算：堆的物理占用通常远小于虚拟大小
                    # 这里用RssAnon中除去栈的部分作为堆
                    stack_kb = proc_mem.get('VmStk', 0)
                    heap_rss_kb = max(0, rss_anon - stack_kb)
            
            # 如果还是没有heap数据，使用VmData作为上限
            if heap_rss_kb == 0:
                heap_rss_kb = vm_data_kb
            
            # 栈
            if stack_rss_kb == 0:
                stack_rss_kb = proc_mem.get('VmStk', 0)
            
            # 匿名mmap（除了堆和栈以外的匿名内存）
            anon_mmap_rss_kb = max(0, rss_anon - heap_rss_kb - stack_rss_kb)
            
            # 代码段和共享库
            # 通过解析/proc/{pid}/smaps获取实际的物理内存(RSS)占用
            exe_kb = proc_mem.get('VmExe', 0)
            lib_kb = proc_mem.get('VmLib', 0)
            
            # 从smaps解析准确的物理内存占用
            exe_rss_kb = 0
            lib_rss_kb = 0
            file_mmap_rss_kb = 0 
            exe_path = None  # 用于调试
            
            if proc_detail and proc_detail != "N/A":
                # 提取完整的smaps内容（每个区域的RSS）
                in_smaps = False
                smaps_content = ""
                for line in proc_detail.split('\n'):
                    if '=== Memory Smaps Full (for RSS analysis) ===' in line:
                        in_smaps = True
                        continue
                    if in_smaps:
                        if line.startswith('==='):
                            break
                        smaps_content += line + "\n"
                
                if smaps_content.strip():
                    # 从maps中查找可执行文件路径（以进程名结尾的路径）
                    exe_path = None
                    comm_match = re.search(r'Name:\s*(\S+)', proc_detail)
                    if comm_match:
                        comm_name = comm_match.group(1)
                        for line in proc_detail.split('\n'):
                            # 跳过非maps行
                            if line.startswith('===') or ':' not in line:
                                continue
                            parts = line.strip().split()
                            if len(parts) >= 6:
                                pathname = ' '.join(parts[5:])
                                # 找到可执行文件（路径包含进程名，排除 [stack] 等特殊映射）
                                if pathname and not pathname.startswith('[') and pathname.endswith(comm_name):
                                    exe_path = pathname
                                    break
                    
                    smaps_stats = self._parse_smaps_by_filetype(smaps_content, exe_path)
                    exe_rss_kb = smaps_stats.get('rss_exe', 0)
                    lib_rss_kb = smaps_stats.get('rss_lib', 0)
                    smaps_file_rss = smaps_stats.get('rss_file', 0)
                    
                    # smaps解析的其他文件映射RSS（不含共享库和代码段）
                    file_mmap_rss_kb = smaps_file_rss
            
            # 构建饼图数据 - 按包含关系组织
            # 外层显示: 匿名映射(RssAnon) vs 文件映射(RssFile) - 来自status
            # 内层显示: 各子项 - 来自smaps解析
            
            pie_outer_labels = ['匿名映射', '文件映射']
            pie_outer_values = [rss_anon, rss_file]
            pie_outer_colors = ['#FF6384', '#36A2EB']
            
            # 内层显示分解
            pie_inner_labels = []
            pie_inner_values = []
            pie_inner_colors = []
            
            if heap_rss_kb > 0:
                pie_inner_labels.append('堆(Heap)')
                pie_inner_values.append(heap_rss_kb)
                pie_inner_colors.append('#FF6384')
            if stack_rss_kb > 0:
                pie_inner_labels.append('栈(Stack)')
                pie_inner_values.append(stack_rss_kb)
                pie_inner_colors.append('#FF9F40')
            if anon_mmap_rss_kb > 0:
                pie_inner_labels.append('匿名mmap')
                pie_inner_values.append(anon_mmap_rss_kb)
                pie_inner_colors.append('#FFCD56')
            if exe_rss_kb > 0:
                pie_inner_labels.append('代码段')
                pie_inner_values.append(exe_rss_kb)
                pie_inner_colors.append('#36A2EB')
            if lib_rss_kb > 0:
                pie_inner_labels.append('共享库')
                pie_inner_values.append(lib_rss_kb)
                pie_inner_colors.append('#4BC0C0')
            if file_mmap_rss_kb > 0:
                pie_inner_labels.append('文件映射')
                pie_inner_values.append(file_mmap_rss_kb)
                pie_inner_colors.append('#9B59B6')
            
            # 使用单一饼图，按比例显示各部分
            pie_labels = []
            pie_values = []
            pie_colors = []
            pie_hover = []
            
            # 匿名映射部分
            if heap_rss_kb > 0:
                pie_labels.append('堆(Heap)')
                pie_values.append(heap_rss_kb)
                pie_colors.append('#FF6384')
                pie_hover.append(f'堆(Heap): {self._format_kb(heap_rss_kb)} ⊆ 匿名映射(RssAnon)')
            if stack_rss_kb > 0:
                pie_labels.append('栈(Stack)')
                pie_values.append(stack_rss_kb)
                pie_colors.append('#FF9F40')
                pie_hover.append(f'栈(Stack): {self._format_kb(stack_rss_kb)} ⊆ 匿名映射(RssAnon)')
            if anon_mmap_rss_kb > 0:
                pie_labels.append('匿名mmap')
                pie_values.append(anon_mmap_rss_kb)
                pie_colors.append('#FFCD56')
                pie_hover.append(f'匿名mmap: {self._format_kb(anon_mmap_rss_kb)} ⊆ 匿名映射(RssAnon)')
            
            # 文件映射部分
            if exe_rss_kb > 0:
                pie_labels.append('代码段')
                pie_values.append(exe_rss_kb)
                pie_colors.append('#36A2EB')
                pie_hover.append(f'代码段: {self._format_kb(exe_rss_kb)} ⊆ 文件映射(RssFile)')
            if lib_rss_kb > 0:
                pie_labels.append('共享库')
                pie_values.append(lib_rss_kb)
                pie_colors.append('#4BC0C0')
                pie_hover.append(f'共享库: {self._format_kb(lib_rss_kb)} ⊆ 文件映射(RssFile)')

                pie_labels.append('文件映射')
                pie_values.append(file_mmap_rss_kb)
                pie_colors.append('#9B59B6')
                pie_hover.append(f'文件映射: {self._format_kb(file_mmap_rss_kb)} ⊆ 文件映射(RssFile)')
            
            # 共享内存部分
            if rss_shmem > 0:
                pie_labels.append('共享内存')
                pie_values.append(rss_shmem)
                pie_colors.append('#E74C3C')
                pie_hover.append(f'共享内存(RssShmem): {self._format_kb(rss_shmem)}')
            
            html += '<h4>进程物理内存(RSS)分布</h4>'
            html += '<p style="color:#666;font-size:12px;margin-bottom:10px;">包含关系: RSS = RssAnon + RssFile + RssShmem</p>'
            html += '<div style="display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start;">'
            html += '<div style="flex:1;min-width:280px;">'
            html += '<canvas id="procMemPieChart"></canvas>'
            html += '</div>'
            html += '<div style="flex:1;min-width:280px;">'
            html += '<table style="width:100%;font-size:12px;">'
            
            # 父级说明
            html += '<tr><td colspan="4" style="font-weight:bold;background:#e8e8e8;padding:5px;">RSS = RssAnon + RssFile + RssShmem</td></tr>'
            html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#FF6384;border-radius:2px;"></span></td><td>匿名映射(RssAnon)</td><td>{self._format_kb(rss_anon)}</td><td>{rss_anon/total_rss*100:.1f}%</td></tr>'
            html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#36A2EB;border-radius:2px;"></span></td><td>文件映射(RssFile)</td><td>{self._format_kb(rss_file)}</td><td>{rss_file/total_rss*100:.1f}%</td></tr>'
            html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#E74C3C;border-radius:2px;"></span></td><td>共享内存(RssShmem)</td><td>{self._format_kb(rss_shmem)}</td><td>{rss_shmem/total_rss*100:.1f}%</td></tr>'
            
            # 子项说明
            html += '<tr><td colspan="4" style="font-weight:bold;background:#f0f0f0;padding:5px;">子项明细 (⊆ 表示从属关系)</td></tr>'
            
            # 匿名映射的子项
            html += '<tr><td colspan="4" style="color:#FF6384;font-size:11px;padding-left:15px;">⊆ 匿名映射(RssAnon)</td></tr>'
            if heap_rss_kb > 0:
                html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#FF6384;border-radius:2px;"></span></td><td>堆(Heap)</td><td>{self._format_kb(heap_rss_kb)}</td><td>{heap_rss_kb/total_rss*100:.1f}%</td></tr>'
            if stack_rss_kb > 0:
                html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#FF9F40;border-radius:2px;"></span></td><td>栈(Stack)</td><td>{self._format_kb(stack_rss_kb)}</td><td>{stack_rss_kb/total_rss*100:.1f}%</td></tr>'
            if anon_mmap_rss_kb > 0:
                html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#FFCD56;border-radius:2px;"></span></td><td>匿名mmap</td><td>{self._format_kb(anon_mmap_rss_kb)}</td><td>{anon_mmap_rss_kb/total_rss*100:.1f}%</td></tr>'
            
            # 文件映射的子项
            html += '<tr><td colspan="4" style="color:#36A2EB;font-size:11px;padding-left:15px;">⊆ 文件映射(RssFile)</td></tr>'
            html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#36A2EB;border-radius:2px;"></span></td><td>代码段</td><td>{self._format_kb(exe_rss_kb)}</td><td>{exe_rss_kb/total_rss*100:.1f}%</td></tr>'
            html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#4BC0C0;border-radius:2px;"></span></td><td>共享库</td><td>{self._format_kb(lib_rss_kb)}</td><td>{lib_rss_kb/total_rss*100:.1f}%</td></tr>'
            html += f'<tr><td style="padding-left:15px;"><span style="display:inline-block;width:10px;height:10px;background:#9B59B6;border-radius:2px;"></span></td><td>文件映射</td><td>{self._format_kb(file_mmap_rss_kb)}</td><td>{file_mmap_rss_kb/total_rss*100:.1f}%</td></tr>'
            
            # 调试信息：exe_path
            html += f'<tr><td colspan="4" style="font-size:10px;color:#999;padding-left:15px;">exe_path: {exe_path or "N/A"}</td></tr>'
            
            # RssShmem是顶层类别，无子项（与RssAnon、RssFile同级）
            
            html += '</table>'
            html += '</div>'
            html += '</div>'
            
            # JavaScript数据
            html += f'<script>var procMemPieData = {{labels: {pie_labels}, values: {pie_values}, colors: {pie_colors}, hoverLabels: {pie_hover}}};</script>'

        # 虚拟内存分布
        vm_data_kb = proc_mem.get('VmData', 0)
        vm_stk_kb = proc_mem.get('VmStk', 0)
        vm_exe_kb = proc_mem.get('VmExe', 0)
        vm_lib_kb = proc_mem.get('VmLib', 0)
        vm_total_kb = proc_mem.get('VmSize', proc_mem.get('VmPeak', vm_data_kb + vm_stk_kb + vm_exe_kb + vm_lib_kb))
        
        if vm_total_kb > 0:
            html += '<h4>进程虚拟内存分布</h4>'
            html += '<p style="color:#666;font-size:12px;margin-bottom:10px;">包含关系: VmSize = VmData + VmStk + VmExe + VmLib + 其他</p>'
            html += '<div style="display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start;">'
            html += '<div style="flex:1;min-width:280px;">'
            html += '<canvas id="procVmPieChart"></canvas>'
            html += '</div>'
            html += '<div style="flex:1;min-width:280px;">'
            html += '<table style="width:100%;font-size:12px;">'
            
            # 子项明细
            html += '<tr><td colspan="4" style="font-weight:bold;background:#f0f0f0;padding:5px;">子项明细</td></tr>'
            if vm_data_kb > 0:
                html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#FF6384;border-radius:2px;"></span></td><td>堆(Heap)</td><td>{self._format_kb(vm_data_kb)}</td><td>{vm_data_kb/vm_total_kb*100:.1f}%</td></tr>'
            if vm_stk_kb > 0:
                html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#FF9F40;border-radius:2px;"></span></td><td>栈(Stack)</td><td>{self._format_kb(vm_stk_kb)}</td><td>{vm_stk_kb/vm_total_kb*100:.1f}%</td></tr>'
            if vm_exe_kb > 0:
                html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#36A2EB;border-radius:2px;"></span></td><td>代码段</td><td>{self._format_kb(vm_exe_kb)}</td><td>{vm_exe_kb/vm_total_kb*100:.1f}%</td></tr>'
            if vm_lib_kb > 0:
                html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#4BC0C0;border-radius:2px;"></span></td><td>共享库</td><td>{self._format_kb(vm_lib_kb)}</td><td>{vm_lib_kb/vm_total_kb*100:.1f}%</td></tr>'
            
            # 虚拟内存总和
            vm_known = vm_data_kb + vm_stk_kb + vm_exe_kb + vm_lib_kb
            if vm_total_kb > vm_known:
                vm_other_kb = vm_total_kb - vm_known
                html += f'<tr><td style="width:12px;"><span style="display:inline-block;width:12px;height:12px;background:#9B59B6;border-radius:2px;"></span></td><td>其他虚拟内存</td><td>{self._format_kb(vm_other_kb)}</td><td>{vm_other_kb/vm_total_kb*100:.1f}%</td></tr>'
            
            html += '</table>'
            html += '</div>'
            html += '</div>'
            
            # 虚拟内存饼图数据
            vm_pie_labels = []
            vm_pie_values = []
            vm_pie_colors = []
            vm_pie_hover = []
            
            if vm_data_kb > 0:
                vm_pie_labels.append('堆(Heap)')
                vm_pie_values.append(vm_data_kb)
                vm_pie_colors.append('#FF6384')
                vm_pie_hover.append(f'堆(Heap): {self._format_kb(vm_data_kb)}')
            if vm_stk_kb > 0:
                vm_pie_labels.append('栈(Stack)')
                vm_pie_values.append(vm_stk_kb)
                vm_pie_colors.append('#FF9F40')
                vm_pie_hover.append(f'栈(Stack): {self._format_kb(vm_stk_kb)}')
            if vm_exe_kb > 0:
                vm_pie_labels.append('代码段')
                vm_pie_values.append(vm_exe_kb)
                vm_pie_colors.append('#36A2EB')
                vm_pie_hover.append(f'代码段: {self._format_kb(vm_exe_kb)}')
            if vm_lib_kb > 0:
                vm_pie_labels.append('共享库')
                vm_pie_values.append(vm_lib_kb)
                vm_pie_colors.append('#4BC0C0')
                vm_pie_hover.append(f'共享库: {self._format_kb(vm_lib_kb)}')
            if vm_total_kb > vm_known:
                vm_pie_labels.append('其他虚拟内存')
                vm_pie_values.append(vm_total_kb - vm_known)
                vm_pie_colors.append('#9B59B6')
                vm_pie_hover.append(f'其他虚拟内存: {self._format_kb(vm_total_kb - vm_known)}')
            
            html += f'<script>var procVmPieData = {{labels: {vm_pie_labels}, values: {vm_pie_values}, colors: {vm_pie_colors}, hoverLabels: {vm_pie_hover}}};</script>'

        # 详细字段表格已移除

        if vmstat_data:
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
