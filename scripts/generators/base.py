#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础HTML生成器 - 提供通用的HTML生成功能
"""

import json
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加路径以导入templates
SCRIPT_DIR = Path(__file__).parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from templates import (
    HTML_HEADER, HTML_FOOTER, NAV_HTML,
    CHART_JS_SCRIPT, STACK_TOGGLE_SCRIPT
)


class BaseHtmlGenerator(ABC):
    """HTML生成器基类"""

    def __init__(self, data: Dict, issues: List, suggestions: List):
        """
        初始化HTML生成器

        Args:
            data: 包含所有数据的字典
            issues: 问题列表
            suggestions: 建议列表
        """
        self.data = data
        self.issues = issues
        self.suggestions = suggestions

    def get_file_content(self, filename: str) -> str:
        """获取数据文件内容"""
        return self.data.get("files", {}).get(filename, "N/A")

    def _escape_html(self, text: str) -> str:
        """HTML转义"""
        if not text:
            return ""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

    def _extract_value(self, text: str, pattern: str) -> Optional[str]:
        """从文本中提取值"""
        if not text:
            return None
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_number(self, text: str, pattern: str) -> Optional[float]:
        """提取数值"""
        if not text:
            return None
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                return None
        return None

    @abstractmethod
    def generate(self) -> str:
        """生成HTML片段 - 子类必须实现"""
        pass

    def generate_header(self) -> str:
        """生成报告头部"""
        app_name = self.data.get("app_name", "未知")
        host = self.data.get("ssh_host", "未知")
        server = self.data.get("display_server", "未知")
        compositor = self.data.get("compositor", "未知")

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        return f"""
        <div class="header">
            <h1>AR-HUD应用程序性能分析报告</h1>
            <div class="subtitle">{app_name}</div>
            <div class="meta">
                <div class="meta-item">主机: {host}</div>
                <div class="meta-item">显示服务器: {server}</div>
                <div class="meta-item">Compositor: {compositor}</div>
                <div class="meta-item">时间: {timestamp}</div>
            </div>
        </div>
        """

    def generate_nav(self) -> str:
        """生成导航栏"""
        return NAV_HTML

    def generate_issues_section(self) -> str:
        """生成问题诊断部分"""
        if not self.issues:
            issues_html = """
            <div class="issue success">
                <h4>未发现明显问题</h4>
                <p>系统运行状态良好，未检测到明显的性能问题。</p>
            </div>
            """
        else:
            issues_html = ""
            for issue in self.issues:
                severity_class = issue.get("severity", "warning")
                title = issue.get("title", "未知问题")
                detail = issue.get("detail", "")

                issues_html += f"""
                <div class="issue {severity_class}">
                    <h4><span class="status {severity_class}">{severity_class.upper()}</span> {title}</h4>
                    <p>{detail}</p>
                </div>
                """

        return f"""
        <section id="issues" class="card">
            <h2>4. 问题诊断</h2>
            {issues_html}
        </section>
        """

    def generate_suggestions_section(self) -> str:
        """生成优化建议部分"""
        if not self.suggestions:
            suggestions_html = '<p class="no-data">暂无优化建议</p>'
        else:
            suggestions_html = ""
            for sug in self.suggestions:
                title = sug.get("title", "")
                content = sug.get("content", "")
                action = sug.get("action", "")

                suggestions_html += f"""
                <div class="suggestion">
                    <h4>{title}</h4>
                    {f'<p>{content}</p>' if content else ''}
                    {f'<p>{action}</p>' if action else ''}
                </div>
                """

        suggestions_html = ""
        for sug in self.suggestions:
            title = sug.get("title", "")
            content = sug.get("content", "")
            action = sug.get("action", "")

            suggestions_html += f"""
            <div class="suggestion">
                <h4>{title}</h4>
                {f'<p>{content}</p>' if content else ''}
                {f'<p>{action}</p>' if action else ''}
            </div>
            """


    def generate_footer(self) -> str:
        """生成页脚"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return HTML_FOOTER.format(timestamp=timestamp)
