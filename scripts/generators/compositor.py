#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compositor生成器 - 生成Wayland/Weston或DRM信息的HTML
"""

from .base import BaseHtmlGenerator


class CompositorGenerator(BaseHtmlGenerator):
    """Compositor状态HTML生成器"""

    def generate(self) -> str:
        return self._generate_compositor_section()

    def _generate_compositor_section(self) -> str:
        """生成Compositor状态部分"""
        display_server = self.data.get("display_server", "wayland")

        if display_server == "wayland":
            return self._generate_wayland_section()
        else:
            return self._generate_drm_section()

    def _generate_wayland_section(self) -> str:
        """生成Wayland/Weston部分"""
        weston_info = self.get_file_content("weston_info.txt")
        weston_log = self.get_file_content("weston_log.txt")
        compositor_procs = self.get_file_content("compositor_process.txt")

        has_errors = "error" in weston_log.lower() if weston_log != "N/A" else False

        return f"""
        <section id="compositor" class="card">
            <h2>2. Compositor状态 (Wayland/Weston)</h2>

            <div class="grid">
                <div class="stat-box">
                    <div class="value">{"运行中" if weston_info != "N/A" else "未运行"}</div>
                    <div class="label">Weston状态</div>
                </div>
                <div class="stat-box">
                    <div class="value">{"<span class='status warning'>有错误</span>" if has_errors else "<span class='status normal'>正常</span>"}</div>
                    <div class="label">日志状态</div>
                </div>
            </div>

            <h3>Weston信息</h3>
            <pre>{self._escape_html(weston_info[:2000]) if weston_info != 'N/A' else 'Weston未运行或无法获取信息'}</pre>

            <h3>Compositor进程</h3>
            <pre>{self._escape_html(compositor_procs[:1000]) if compositor_procs != 'N/A' else 'N/A'}</pre>

            <h3>最近日志</h3>
            <pre>{self._escape_html(weston_log[:2000]) if weston_log != 'N/A' else 'N/A'}</pre>
        </section>
        """

    def _generate_drm_section(self) -> str:
        """生成DRM直接模式部分"""
        drm_nodes = self.get_file_content("drm_nodes.txt")
        fbset = self.get_file_content("fbset.txt")
        framebuffer = self.get_file_content("framebuffer.txt")

        return f"""
        <section id="compositor" class="card">
            <h2>2. DRM状态 (无Compositor)</h2>

            <h3>DRM设备节点</h3>
            <pre>{self._escape_html(drm_nodes[:1000]) if drm_nodes != 'N/A' else 'N/A'}</pre>

            <h3>Framebuffer信息</h3>
            <pre>{self._escape_html(fbset[:1500]) if fbset != 'N/A' else 'N/A'}</pre>

            <h3>虚拟显示尺寸</h3>
            <pre>{framebuffer if framebuffer != 'N/A' else 'N/A'}</pre>
        </section>
        """
