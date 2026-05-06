#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML模板定义 - 分离HTML样式和模板以提高可维护性
"""

# HTML头部模板
HTML_HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 性能分析报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .header .meta {{
            margin-top: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}

        .header .meta-item {{
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 5px;
        }}

        /* 导航栏 */
        .nav {{
            background: white;
            padding: 15px 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 10px;
            z-index: 100;
        }}

        .nav ul {{
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}

        .nav a {{
            text-decoration: none;
            color: #667eea;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 5px;
            transition: all 0.3s;
        }}

        .nav a:hover {{
            background: #667eea;
            color: white;
        }}

        /* 内容卡片 */
        .card {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .card h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}

        .card h3 {{
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.3em;
        }}

        /* 状态指示器 */
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}

        .status.normal {{
            background: #d4edda;
            color: #155724;
        }}

        .status.warning {{
            background: #fff3cd;
            color: #856404;
        }}

        .status.error {{
            background: #f8d7da;
            color: #721c24;
        }}

        /* 表格样式 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}

        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        /* 代码块 */
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }}

        /* 问题列表 */
        .issue {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}

        .issue.error {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}

        .issue.success {{
            background: #d4edda;
            border-left-color: #28a745;
        }}

        .issue h4 {{
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        /* 优化建议 */
        .suggestion {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}

        .suggestion .code {{
            background: #d4e5f7;
            padding: 10px 15px;
            border-radius: 5px;
            font-family: monospace;
            margin: 10px 0;
            overflow-x: auto;
        }}

        /* 热点函数调用栈样式 */
        .stack-details {{
            margin: 15px 0;
        }}

        /* 热点函数表格样式 */
        .hot-functions-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }}

        .hot-functions-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        .hot-functions-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }}

        .hot-functions-table td:nth-child(1) {{ width: 60px; text-align: center; }}
        .hot-functions-table td:nth-child(2) {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .hot-functions-table td:nth-child(3) {{ width: 100px; text-align: right; padding-right: 20px; }}
        .hot-functions-table td:nth-child(4) {{ width: 80px; text-align: center; }}
        .hot-functions-table td:nth-child(5) {{ width: 120px; text-align: center; }}

        .hot-functions-table tr:hover {{
            background: #f8f9fa;
        }}

        .hot-functions-table tr.high-usage {{
            background: #fff3cd;
        }}

        .hot-functions-table tr.high-usage:hover {{
            background: #ffeeba;
        }}

        .category-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}

        .category-tag.图形 {{
            background: #e3f2fd;
            color: #1565c0;
        }}

        .category-tag.通用 {{
            background: #f3e5f5;
            color: #7b1fa2;
        }}

        .stack-link {{
            color: #667eea;
            text-decoration: none;
            font-size: 12px;
        }}

        .stack-link:hover {{
            text-decoration: underline;
        }}

        /* SVG火焰图容器 */
        .svg-flamegraph-container {{
            margin: 20px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            border: 1px solid #eee;
        }}

        .svg-wrapper {{
            overflow-x: auto;
            margin: 10px 0;
        }}

        .svg-wrapper svg {{
            max-width: 100%;
            height: auto;
        }}

        .download-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
        }}

        .download-link:hover {{
            background: #5568d3;
        }}

        .back-link {{
            font-size: 12px;
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            margin-left: 15px;
        }}

        .back-link:hover {{
            color: white;
            text-decoration: underline;
        }}

        .stack-function {{
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}

        .stack-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            user-select: none;
            gap: 15px;
        }}

        .stack-header:hover {{
            background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
        }}

        .stack-name {{
            font-weight: bold;
            flex: 1;
            min-width: 0;
            max-width: calc(100% - 140px);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .stack-name code {{
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 13px;
        }}

        .stack-pct {{
            min-width: 90px;
            text-align: right;
            background: rgba(255,255,255,0.3);
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 14px;
        }}

        .stack-toggle {{
            font-size: 12px;
            margin-left: 10px;
        }}

        .stack-content {{
            background: #f8f9fa;
            border-top: 1px solid #ddd;
            padding: 15px;
        }}

        .stack-content pre {{
            margin: 0;
            font-family: 'Courier New', Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        .stack-content pre .func-entry {{
            color: #e83e8c;
            font-weight: bold;
        }}

        /* 网格布局 */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .stat-box {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}

        .stat-box .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-box .label {{
            color: #666;
            margin-top: 5px;
        }}

        /* 图表容器 */
        .chart-container {{
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .chart-container h3 {{
            margin-bottom: 15px;
            color: #333;
        }}

        .chart-container canvas {{
            max-height: 300px;
        }}

        .no-data {{
            text-align: center;
            color: #999;
            padding: 40px;
            font-style: italic;
        }}

        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }}

        /* 响应式 */
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .header .meta {{
                flex-direction: column;
                gap: 10px;
            }}
            .nav ul {{
                flex-direction: column;
            }}
        }}

        /* 目录树 */
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}

        .toc ul {{
            list-style: none;
            padding-left: 20px;
        }}

        .toc li {{
            padding: 5px 0;
        }}

        .toc a {{
            color: #667eea;
            text-decoration: none;
        }}

        .toc a:hover {{
            text-decoration: underline;
        }}

        /* 进度条 */
        .progress {{
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .progress-bar {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s;
        }}

        .progress-bar.low {{ background: #28a745; }}
        .progress-bar.medium {{ background: #ffc107; }}
        .progress-bar.high {{ background: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
"""

# HTML页脚模板
HTML_FOOTER = """
    </div>
    <div class="footer">
        <p>报告生成时间: {timestamp}</p>
        <p>图形显示应用程序性能分析系统</p>
    </div>
</body>
</html>
"""

# JavaScript脚本模板
CHART_JS_SCRIPT = '''
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof perfChartData !== 'undefined' && perfChartData.times.length > 0) {
            const perfCtx = document.getElementById('perfChart');
            if (perfCtx) {
                const hasCpuData = perfChartData.appCpu.some(v => v !== null && v !== undefined);
                const hasRssData = perfChartData.appRss.some(v => v !== null && v !== undefined);
                const hasVszData = perfChartData.appVsz.some(v => v !== null && v !== undefined);

                if (!hasCpuData && !hasRssData && !hasVszData) {
                    perfCtx.parentElement.innerHTML += '<div class="no-data" style="padding:40px;text-align:center;color:#999;">采集数据失败：目标进程采样数据全为 N/A<br>请检查：1) 目标进程是否在运行 2) SSH连接是否正常 3) 采样权限是否足够</div>';
                    perfCtx.style.display = 'none';
                } else {
                    const validIndices = [];
                    const validTimes = [];
                    const validCpu = [];
                    const validRss = [];
                    const validVsz = [];

                    for (let i = 0; i < perfChartData.times.length; i++) {
                        if (perfChartData.appCpu[i] !== null ||
                            perfChartData.appRss[i] !== null ||
                            perfChartData.appVsz[i] !== null) {
                            validIndices.push(i);
                            validTimes.push(perfChartData.times[i]);
                            validCpu.push(perfChartData.appCpu[i]);
                            validRss.push(perfChartData.appRss[i]);
                            validVsz.push(perfChartData.appVsz[i]);
                        }
                    }

                    const datasets = [];

                    if (hasCpuData) {
                        datasets.push({
                            label: 'CPU %',
                            data: validCpu,
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.1)',
                            tension: 0.3,
                            fill: true,
                            yAxisID: 'y',
                            spanGaps: true
                        });
                    }

                    if (hasRssData) {
                        datasets.push({
                            label: 'RSS (MB)',
                            data: validRss,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            tension: 0.3,
                            fill: true,
                            yAxisID: 'y1',
                            spanGaps: true
                        });
                    }

                    if (hasVszData) {
                        datasets.push({
                            label: 'VSZ (MB)',
                            data: validVsz,
                            borderColor: 'rgb(153, 102, 255)',
                            backgroundColor: 'rgba(153, 102, 255, 0.1)',
                            tension: 0.3,
                            fill: false,
                            yAxisID: 'y1',
                            spanGaps: true
                        });
                    }

                    new Chart(perfCtx, {
                        type: 'line',
                        data: {
                            labels: validTimes.map(t => t + 's'),
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            plugins: {
                                legend: { position: 'top' },
                                tooltip: { callbacks: {} }
                            },
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    beginAtZero: true,
                                    max: 100,
                                    title: { display: true, text: 'CPU %' }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    beginAtZero: true,
                                    suggestedMax: maxMemValue > 0 ? maxMemValue : 100,
                                    grid: { drawOnChartArea: false }
                                }
                            }
                        }
                    });
                }
            }
        }
    });
    </script>
'''

# 调用栈折叠功能脚本
STACK_TOGGLE_SCRIPT = '''
    <script>
    function toggleStack(id) {
        var content = document.getElementById(id);
        if (content) {
            if (content.style.display === 'none' || content.style.display === '') {
                content.style.display = 'block';
                var header = content.previousElementSibling;
                if (header && header.classList.contains('stack-header')) {
                    var toggle = header.querySelector('.stack-toggle');
                    if (toggle) toggle.textContent = '▲';
                }
            } else {
                content.style.display = 'none';
                var header = content.previousElementSibling;
                if (header && header.classList.contains('stack-header')) {
                    var toggle = header.querySelector('.stack-toggle');
                    if (toggle) toggle.textContent = '▼';
                }
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.stack-content').forEach(function(el) {
            el.style.display = 'none';
        });
    });

    if (window.location.hash) {
        var hash = window.location.hash.substring(1);
        var targetEl = document.getElementById(hash);
        if (targetEl) {
            setTimeout(function() {
                targetEl.scrollIntoView({ behavior: 'smooth' });
                if (targetEl.classList.contains('stack-content')) {
                    targetEl.style.display = 'block';
                }
                if (targetEl.classList.contains('stack-header')) {
                    var content = targetEl.nextElementSibling;
                    if (content && content.classList.contains('stack-content')) {
                        content.style.display = 'block';
                        var toggle = targetEl.querySelector('.stack-toggle');
                        if (toggle) toggle.textContent = '▲';
                    }
                }
            }, 300);
        }
    }
    </script>
'''

# 导航栏HTML模板
NAV_HTML = """
        <nav class="nav">
            <ul>
                <li><a href="#overview">系统概览</a></li>
                <li><a href="#compositor">Compositor状态</a></li>
                <li><a href="#application">应用性能</a></li>
                <li><a href="#issues">问题诊断</a></li>
                <li><a href="#perf-chart">性能趋势</a></li>
                <li><a href="#flamegraph">火焰图</a></li>
                <li><a href="#graphics">图形优化</a></li>
                <li><a href="#io-analysis">I/O性能</a></li>
                <li><a href="#threads-analysis">线程分析</a></li>
                <li><a href="#suggestions">优化建议</a></li>
            </ul>
        </nav>
"""
