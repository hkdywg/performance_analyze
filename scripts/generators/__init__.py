#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML生成器模块

包含各类HTML生成器：
- base: 基础生成器
- system: 系统概览生成器
- app: 应用性能生成器
- compositor: Compositor状态生成器
- chart: 图表生成器
- flamegraph: 火焰图生成器
- score: 评分生成器
- analysis: I/O和线程分析生成器
- proc_stat: 进程stat信息生成器
"""

from .base import BaseHtmlGenerator
from .system import SystemOverviewGenerator
from .app import AppPerformanceGenerator
from .compositor import CompositorGenerator
from .chart import ChartGenerator
from .flamegraph import FlamegraphGenerator
from .score import ScoreGenerator
from .analysis import IoAnalysisGenerator, ThreadAnalysisGenerator
from .proc_stat import ProcStatGenerator

__all__ = [
    'BaseHtmlGenerator',
    'SystemOverviewGenerator',
    'AppPerformanceGenerator',
    'CompositorGenerator',
    'ChartGenerator',
    'FlamegraphGenerator',
    'ScoreGenerator',
    'IoAnalysisGenerator',
    'ThreadAnalysisGenerator',
    'ProcStatGenerator',
]
