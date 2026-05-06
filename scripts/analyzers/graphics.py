#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图形学分析器 - 分析OpenGL/Vulkan/DRM等图形相关性能
"""

import re
from typing import Dict, List, Tuple
from .base import BaseAnalyzer


class GraphicsAnalyzer(BaseAnalyzer):
    """图形学性能分析器"""

    def analyze(self) -> None:
        """执行图形学分析"""
        self._check_opengl_info()
        self._check_vulkan_info()
        self._check_frame_timing()

    def _check_opengl_info(self) -> None:
        """检查OpenGL信息"""
        opengl_info = self.get_file_content("opengl_info.txt")
        if not opengl_info or opengl_info == "N/A":
            return

        # 检查GL版本
        gl_version = re.search(r'OpenGL version string:\s*(.+)', opengl_info)
        if gl_version:
            version_str = gl_version.group(1).strip()
            version_match = re.search(r'(\d+)\.(\d+)', version_str)
            if version_match:
                major, minor = int(version_match.group(1)), int(version_match.group(2))
                if major < 3:
                    self.add_issue(
                        "info",
                        "OpenGL配置建议",
                        "OpenGL版本较低（<3.0），无法使用现代渲染优化技术。建议升级到OpenGL ES 3.0或更高版本。"
                    )
                elif major == 3 and minor < 2:
                    self.add_suggestion(
                        "OpenGL版本建议",
                        "OpenGL 3.x版本",
                        "建议考虑使用Compute Shader等更现代的特性。",
                        "opengl"
                    )

        # 检查纹理压缩支持
        compressions = []
        if 'GL_OES_compressed_ETC1_RGB8_texture' in opengl_info or 'GL_ETC1_RGB8_OES' in opengl_info:
            compressions.append('ETC1')
        if 'GL_OES_texture_compression_astc' in opengl_info or 'GL_ASTC' in opengl_info:
            compressions.append('ASTC')
        if 'GL_S3TC' in opengl_info or 'GL_EXT_texture_compression_s3tc' in opengl_info:
            compressions.append('DXT/BC')

        if compressions:
            self.add_suggestion(
                "纹理压缩格式建议",
                f"GPU支持的纹理压缩格式: {', '.join(compressions)}",
                f"使用 {compressions[0]} 格式可显著减少纹理内存占用和带宽使用。",
                "texture"
            )
        else:
            self.add_issue(
                "info",
                "OpenGL配置建议",
                "未检测到GPU压缩纹理支持，建议评估纹理数据格式优化。"
            )

        # 检查V-Sync设置
        if 'v-sync' in opengl_info.lower() or 'vsync' in opengl_info.lower():
            self.add_suggestion(
                "垂直同步设置检查",
                "检测到V-Sync配置",
                "对于固定帧率应用，可考虑使用Triple Buffering优化显示延迟。",
                "vsync"
            )

    def _check_vulkan_info(self) -> None:
        """检查Vulkan信息"""
        vulkan_info = self.get_file_content("vulkan_info.txt")
        if not vulkan_info or vulkan_info == "N/A":
            return

        if 'VK_KHR_timeline_semaphore' in vulkan_info or 'timeline semaphore' in vulkan_info.lower():
            self.add_suggestion(
                "Vulkan Timeline Semaphore",
                "GPU支持Timeline Semaphore同步机制",
                "使用Timeline Semaphore替代传统Fence可减少同步开销，提高多线程渲染效率。",
                "vulkan"
            )

        if 'VK_KHR_display' in vulkan_info:
            self.add_suggestion(
                "Vulkan显示扩展支持",
                "GPU支持原生显示扩展",
                "可考虑使用VK_KHR_display直接控制显示输出，减少 compositor 开销。",
                "vulkan_display"
            )

    def _check_frame_timing(self) -> None:
        """分析帧渲染时机相关指标"""
        app_cpu = self.get_file_content("app_cpu.txt")
        if not app_cpu:
            return

        # 从CPU使用率推断帧率稳定性
        cpu_values = re.findall(r"^\s*\d+\s+[\d.]+\s+(\d+\.?\d*)", app_cpu, re.MULTILINE)
        if cpu_values:
            try:
                values = [float(v) for v in cpu_values if float(v) > 0]
                if values:
                    avg_cpu = sum(values) / len(values)
                    max_cpu = max(values)
                    std_dev = (sum((v - avg_cpu) ** 2 for v in values) / len(values)) ** 0.5

                    if max_cpu > 90:
                        self.add_issue(
                            "warning",
                            "帧渲染CPU负载过高",
                            f"峰值CPU使用率 {max_cpu:.1f}%，可能导致帧率不稳定"
                        )
                        self.add_suggestion(
                            "帧率稳定性优化",
                            "CPU使用率波动较大，可能导致帧时间不稳定。",
                            "建议：1) 使用帧时间预算管理 2) 实现异步渲染管线 3) 将CPU密集操作移至GPU 4) 使用多线程渲染分离逻辑和渲染。",
                            "frame_rate"
                        )

                    if std_dev > avg_cpu * 0.3 and avg_cpu > 50:
                        self.add_suggestion(
                            "渲染负载均衡",
                            "检测到渲染负载不均匀，可能导致周期性卡顿。",
                            "建议实现脏矩形更新、视锥剔除、LOD等技术减少每帧渲染负载差异。",
                            "load_balance"
                        )
            except (ValueError, ZeroDivisionError):
                pass

    def _analyze_hot_functions(self, hot_funcs: List[Tuple[str, float]]) -> None:
        """分析热点函数"""
        graphics_hot = []
        general_hot = []

        for func, pct in hot_funcs:
            func_lower = func.lower()
            if any(kw in func_lower for kw in ['gl', 'egl', 'drm', 'gpu', 'shader',
                                                  'texture', 'render', 'blit', 'flip',
                                                  'sync', ' Mesa', 'intel', 'i915',
                                                  'libgles', 'libsrv', 'pvrsrv']):
                graphics_hot.append((func, pct))
            else:
                general_hot.append((func, pct))

        # 报告热点函数
        if graphics_hot:
            top_graphics = graphics_hot[:3]
            self.add_suggestion(
                "GPU/图形渲染热点检测",
                f"检测到以下图形渲染函数占用较高CPU时间: {', '.join([f'{f[0]} ({f[1]:.1f}%)' for f in top_graphics])}",
                self._get_graphics_hot_suggestion(top_graphics),
                "graphics"
            )

        if general_hot:
            top_general = general_hot[:5]
            self.add_issue(
                "warning",
                "通用热点函数",
                f"检测到高CPU占用的非图形函数: {', '.join([f[0] for f in top_general])}"
            )
            self.add_suggestion(
                "CPU热点优化",
                f"热点函数: {', '.join([f'{f[0]} ({f[1]:.1f}%)' for f in top_general])}",
                "检查这些函数是否有优化空间，考虑算法优化、缓存、并行化等方式。",
                "general"
            )

    def _get_graphics_hot_suggestion(self, hot_funcs: List[Tuple[str, float]]) -> str:
        """根据热点图形函数生成具体建议"""
        suggestions = []
        for func, pct in hot_funcs:
            func_lower = func.lower()
            if 'shader' in func_lower:
                suggestions.append(f"着色器 {func} 占用{pct:.1f}%，考虑简化着色器逻辑或使用更低精度的数据类型。")
            elif 'texture' in func_lower or 'tex' in func_lower:
                suggestions.append(f"纹理操作 {func} 占用{pct:.1f}%，考虑使用GPU压缩纹理格式（ETC/ASTC/BC）。")
            elif 'blit' in func_lower or 'copy' in func_lower:
                suggestions.append(f"数据传输 {func} 占用{pct:.1f}%，考虑使用PBO或DMA传输优化。")
            elif 'sync' in func_lower or 'wait' in func_lower:
                suggestions.append(f"同步操作 {func} 占用{pct:.1f}%，考虑使用Fence或Timeline同步机制。")
            elif 'drm' in func_lower or 'modeset' in func_lower:
                suggestions.append(f"DRM调用 {func} 占用{pct:.1f}%，检查显示模式设置是否有缓存空间。")
            elif 'egl' in func_lower or 'gl' in func_lower:
                suggestions.append(f"OpenGL/EGL调用 {func} 占用{pct:.1f}%，检查是否有冗余的状态切换。")

        if not suggestions:
            return "分析热点函数，建议使用GPU Profiler进行深入分析。"
        return " ".join(suggestions[:3])

    def score(self) -> float:
        """计算图形性能评分"""
        graphics_score = 100.0

        # 检查OpenGL版本
        opengl_info = self.get_file_content("opengl_info.txt")
        if opengl_info and opengl_info != "N/A":
            gl_version = re.search(r'OpenGL version string:\s*(.+)', opengl_info)
            if gl_version:
                version_str = gl_version.group(1)
                version_match = re.search(r'(\d+)\.(\d+)', version_str)
                if version_match:
                    major, minor = int(version_match.group(1)), int(version_match.group(2))
                    if major < 3:
                        graphics_score -= 20
                    elif major == 3 and minor < 2:
                        graphics_score -= 10

        return max(0, min(100, graphics_score))
