#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能评分生成器 - 生成性能评分HTML
"""

from typing import Dict
from .base import BaseHtmlGenerator


class ScoreGenerator(BaseHtmlGenerator):
    """性能评分HTML生成器"""

    def __init__(self, data: Dict, issues: list, suggestions: list,
                 scores: dict, total_score: float, bottleneck: str):
        super().__init__(data, issues, suggestions)
        self.scores = scores
        self.total_score = total_score
        self.bottleneck = bottleneck

    def generate(self) -> str:
        return self._generate_performance_score_section()

    def _generate_performance_score_section(self) -> str:
        """生成性能评分章节"""
        weights = [s[1] for s in self.scores.items()]

        return f"""
        <section id="performance-score" class="card">
            <h2>7. 性能综合评估</h2>
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="stat-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <div class="value" style="font-size: 3em; color: white;">{self.total_score:.0f}</div>
                    <div class="label" style="color: rgba(255,255,255,0.9);">综合评分</div>
                </div>
                <div class="stat-box">
                    <div class="value" style="color: #667eea;">{self.bottleneck}</div>
                    <div class="label">主要瓶颈</div>
                </div>
            </div>
            <h3>分项评分</h3>
            <table>
                <tr><th>维度</th><th>得分</th><th>评价</th><th>权重</th></tr>
                {self._generate_score_row('CPU', self.scores.get('CPU', 100))}
                {self._generate_score_row('Memory', self.scores.get('Memory', 100))}
                {self._generate_score_row('I/O', self.scores.get('I/O', 100))}
                {self._generate_score_row('Threads', self.scores.get('Threads', 100))}
                {self._generate_score_row('Graphics', self.scores.get('Graphics', 100))}
            </table>
            <h3>性能优化优先级</h3>
            <div class="suggestion">
                <h4>优化策略建议</h4>
                {self._generate_optimization_priority()}
            </div>
        </section>
        """

    def _generate_score_row(self, category: str, score: float) -> str:
        """生成评分表格行"""
        if score >= 90:
            status = '<span class="status normal">优秀</span>'
        elif score >= 70:
            status = '<span class="status warning">良好</span>'
        elif score >= 50:
            status = '<span class="status warning">需关注</span>'
        else:
            status = '<span class="status error">较差</span>'

        if score >= 90:
            weight_desc = '30% - 不影响整体性能'
        elif score >= 70:
            weight_desc = '20% - 轻微影响'
        elif score >= 50:
            weight_desc = '15% - 中等影响'
        else:
            weight_desc = '10% - 严重影响'

        return f"""
                <tr>
                    <td>{category}</td>
                    <td>{score:.1f}</td>
                    <td>{status}</td>
                    <td>{weight_desc}</td>
                </tr>
        """

    def _generate_optimization_priority(self) -> str:
        """生成优化优先级建议"""
        sorted_items = sorted(self.scores.items(), key=lambda x: x[1])

        if sorted_items[0][1] < 50:
            return f"当前性能存在严重问题，建议立即进行深度性能优化。优先解决 {self.bottleneck} 相关问题。"
        elif sorted_items[0][1] < 70:
            return f"性能状况良好，但仍有优化空间。建议关注 {self.bottleneck} 相关优化，可提升系统响应速度。"
        else:
            return "性能表现优异，建议继续监控性能指标，保持当前优化水平。"
