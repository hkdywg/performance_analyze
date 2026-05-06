# Linux 图形显示应用性能分析工具

一款专为嵌入式Linux系统设计的图形显示应用程序性能分析工具，通过SSH远程连接目标系统，采集GPU、CPU、内存、帧率等性能数据，自动生成可视化的HTML分析报告。

## 功能特点

### 核心能力
- **通用DRM接口**：支持所有主流GPU（Intel、AMD、NVIDIA、ARM Mali等）
- **Wayland/DRM支持**：专为嵌入式图形系统设计（不支持X11）
- **SSH远程分析**：无需在目标设备安装额外软件
- **自动化报告**：一键生成完整的HTML性能分析报告
- **火焰图分析**：使用perf生成CPU热点火焰图
- **锁争用分析**：使用perf lock分析线程锁竞争问题

### 分析维度
| 类别 | 分析内容 |
|------|----------|
| 系统资源 | CPU使用率、内存使用、磁盘I/O、网络I/O |
| 应用性能 | 进程CPU/内存占用、文件描述符、上下文切换 |
| 热点分析 | 函数级CPU占用（火焰图） |
| 锁分析 | 锁争用统计、等待时间分析 |

## 项目结构

```
performance/
├── SKILL.md                      # Linux系统性能分析Skill
├── SKILL_GRAPHICS.md            # 图形分析Skill（用于Cursor AI）
├── README.md                    # 本文件
├── config/
│   ├── config.yaml              # 配置文件
│   └── config.yaml.example      # 配置示例
├── scripts/
│   ├── analyze_remote.sh         # 远程数据采集脚本
│   ├── generate_report.py       # 报告生成器
│   ├── report_generator.py      # 报告生成器（主程序）
│   ├── config.py                # 配置加载模块
│   ├── upload_data.py           # 数据上传脚本
│   ├── generators/             # HTML生成器模块
│   │   ├── __init__.py
│   │   ├── base.py              # 基础生成器
│   │   ├── system.py            # 系统概览生成器
│   │   ├── app.py               # 应用信息生成器
│   │   ├── chart.py             # 图表生成器
│   │   ├── flamegraph.py        # 火焰图生成器
│   │   ├── analysis.py          # I/O和锁分析生成器
│   │   ├── proc_stat.py         # 进程stat生成器
│   │   └── score.py             # 性能评分生成器
│   └── analyzers/              # 数据分析模块
│       ├── __init__.py
│       ├── cpu.py
│       ├── memory.py
│       ├── io.py
│       ├── thread.py
│       ├── network.py
│       ├── graphics.py
│       ├── flamegraph.py
│       ├── syscall.py
│       └── process_stat.py
├── references/                  # 参考文档
│   ├── cpu.md
│   ├── memory.md
│   ├── io.md
│   ├── gpu.md
│   ├── wayland.md
│   └── embedded.md
└── FlameGraph/                  # 火焰图工具（可选，需自行下载）
```

## 安装

### 依赖要求

**本地环境**：
- Python 3.8+
- pyyaml
- paramiko（SSH连接）
- Flask（可选，用于本地预览）

**目标设备**：
- Linux kernel 4.0+
- perf 工具（部分功能需要root权限）
- top, free, df 等基础工具

### 安装步骤

```bash
# 1. 克隆项目
cd ~/ywg_workspace/prj
git clone <repo-url> performance
cd performance

# 2. 安装Python依赖
pip3 install pyyaml paramiko

# 3. 下载FlameGraph工具（可选，用于火焰图）
git clone https://github.com/brendangregg/FlameGraph.git
```

## 配置

编辑 `config/config.yaml` 配置文件：

```yaml
# SSH连接配置
ssh_host: "192.168.1.100"       # 目标设备IP
ssh_port: 22                    # SSH端口
ssh_user: "root"                # SSH用户名
ssh_key: "~/.ssh/id_rsa"       # SSH密钥路径（可选）

# 目标应用配置
app_name: "wayland-app"         # 应用名称（用于匹配进程）
process_pattern: "wayland-app"  # 进程匹配模式（支持正则）

# 采集配置
duration: 10                    # 采集持续时间（秒）
display_server: "wayland"       # 显示服务器类型：wayland 或 drm
compositor: "weston"            # Compositor名称

# 输出配置
output_dir: "./report"          # 输出目录
```

### 配置参数说明

| 参数 | 说明 | 必填 |
|------|------|------|
| ssh_host | 目标设备IP地址 | 是 |
| ssh_port | SSH端口 | 否（默认22） |
| ssh_user | SSH用户名 | 是 |
| ssh_key | SSH私钥路径 | 否（可使用密码） |
| app_name | 目标应用名称 | 是 |
| process_pattern | 进程匹配模式（支持正则） | 是 |
| duration | 采集持续时间（秒） | 否（默认10） |
| display_server | 显示服务器类型 | 是 |
| compositor | Compositor名称 | 否 |

## 使用方法

### 完整分析流程

```bash
# 1. 配置目标设备
vim config/config.yaml

# 2. 运行数据采集（需要SSH连接）
./scripts/analyze_remote.sh -c config/config.yaml

# 3. 生成HTML报告
python3 scripts/generate_report.py -d ./report

# 4. 查看报告
# 使用浏览器打开 report/report.html
```

### 单独使用各模块

```bash
# 仅采集数据
./scripts/analyze_remote.sh -c config/config.yaml

# 仅生成报告
python3 scripts/generate_report.py -d ./report

# 使用不同配置
./scripts/analyze_remote.sh -c config/production.yaml
python3 scripts/generate_report.py -d ./report -o report_prod.html
```

### SSH密钥配置（免密码登录）

```bash
# 生成本地SSH密钥（如果还没有）
ssh-keygen -t rsa

# 复制公钥到目标设备
ssh-copy-id root@192.168.1.100

# 测试连接
ssh root@192.168.1.100 "echo 'Connection OK'"
```

## 采集的数据

### 系统信息
| 文件 | 内容 | 说明 |
|------|------|------|
| system_info.txt | 系统基本信息 | 内核版本、CPU信息、内存总量 |
| cpu_info.txt | CPU详细信息 | CPU型号、核心数、频率 |
| mem_info.txt | 内存信息 | 内存总量、使用量、可用量 |
| disk_info.txt | 磁盘信息 | 分区使用情况 |
| loadavg.txt | 系统负载 | 1/5/15分钟平均负载 |

### 应用进程信息
| 文件 | 内容 | 说明 |
|------|------|------|
| app_process.txt | 进程列表 | 匹配到的应用进程 |
| app_status.txt | 进程状态 | /proc/[pid]/status |
| app_stat.txt | 进程统计 | /proc/[pid]/stat |
| app_smaps.txt | 内存映射 | /proc/[pid]/smaps_rollup |
| app_cpu.txt | CPU占用 | top输出 |
| app_memory.txt | 内存占用 | 内存详细使用 |
| app_io.txt | I/O统计 | /proc/[pid]/io |

### 性能采样数据
| 文件 | 内容 | 说明 |
|------|------|------|
| cpu_samples.csv | CPU采样 | CPU使用率时间序列 |
| mem_samples.csv | 内存采样 | 内存使用时间序列 |
| fps_samples.csv | 帧率采样 | FPS时间序列 |
| load_samples.csv | 负载采样 | 系统负载时间序列 |

### 火焰图和追踪数据
| 文件 | 内容 | 说明 |
|------|------|------|
| perf.data | perf原始数据 | perf record采集的数据 |
| perf_flamegraph.svg | 火焰图 | CPU热点可视化 |
| perf_report.txt | perf报告 | 热点函数列表 |
| drm_traces.txt | DRM追踪 | DRM事件追踪数据 |

### 锁分析数据
| 文件 | 内容 | 说明 |
|------|------|------|
| perf_lock.txt | 锁分析报告 | perf lock统计 |
| lock_contention.txt | 锁争用详情 | 锁争用排名 |

## 报告内容

生成的HTML报告包含以下章节：

### 1. 系统概览
- 系统基本信息（内核、CPU、内存）
- 资源使用摘要卡片
- 性能评分雷达图

### 2. 应用基础信息
- 进程列表和状态
- CPU/内存/IO使用
- 文件描述符数量

### 3. 性能趋势图表
- CPU使用率折线图
- 内存使用折线图
- 帧率折线图（FPS）
- 系统负载折线图

### 4. 火焰图与热点分析
- 可交互的SVG火焰图
- 热点函数排名表
- 调用栈折叠/展开功能

### 5. I/O性能分析
- 读取/写入速率统计
- I/O稳定性分析
- 性能建议

### 6. 锁分析
- 锁争用统计
- 热点锁排名
- 等待时间分析
- 优化建议

### 7. 进程Stat详情
- 详细的进程状态信息
- 上下文切换统计

### 8. 性能综合评估
- 总体评分（0-100）
- 瓶颈识别
- 优化建议汇总

## 权限要求

| 功能 | 所需权限 | 说明 |
|------|----------|------|
| 基础系统信息采集 | 普通用户 | top, free, df等 |
| 应用进程信息 | 普通用户 | /proc/[pid]/* |
| perf record | root用户 | CPU采样 |
| perf lock | root用户 | 锁分析 |
| DRM追踪 | root用户 | ftrace |

> **提示**：如果没有root权限，火焰图和锁分析功能将无法使用，但仍可采集基础性能数据。

## 常见问题

### Q: SSH连接失败怎么办？

```bash
# 1. 检查SSH服务
ssh root@目标IP "systemctl status sshd"

# 2. 检查网络连通性
ping 目标IP

# 3. 确认SSH端口
ssh -p 22 root@目标IP
```

### Q: perf命令不可用？

```bash
# 在目标设备上安装perf
# Debian/Ubuntu
apt install linux-tools-common linux-tools-generic

# Yocto/OpenEmbedded
bitbake linux-yocto -c populate_sysroot
```

### Q: 火焰图生成为空？

1. 确认perf工具可用：`ssh 目标 'which perf'`
2. 确认有root权限
3. 检查perf.data文件是否生成
4. 确认FlameGraph工具已下载

### Q: 如何分析多个进程？

修改config.yaml中的process_pattern：

```yaml
process_pattern: "app1|app2|app3"  # 使用正则匹配多个进程
```

## 高级用法

### 使用不同用户运行

```bash
# 修改配置文件使用非root用户
ssh_user: "devel"
ssh_key: "/home/user/.ssh/id_rsa"
```

> 注意：非root用户的perf功能受限

### 自定义采集时间

```bash
# 采集30秒数据
duration: 30  # 在config.yaml中设置

# 或通过命令行参数
./scripts/analyze_remote.sh -c config/config.yaml -t 30
```

### 生成对比报告

```bash
# 采集优化前的数据
./scripts/analyze_remote.sh -c config/config.yaml -o ./report_before

# 采集优化后的数据
./scripts/analyze_remote.sh -c config/config.yaml -o ./report_after

# 生成两个报告进行对比
python3 scripts/generate_report.py -d ./report_before -o report_before.html
python3 scripts/generate_report.py -d ./report_after -o report_after.html
```

## 参考资料

- [perf Documentation](https://www.man7.org/linux/man-pages/man1/perf.1.html)
- [FlameGraph](https://github.com/brendangregg/FlameGraph)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html)
- [DRM Documentation](https://www.kernel.org/doc/html/latest/gpu/index.html)
- [Wayland Documentation](https://wayland.freedesktop.org/docs.html)

## License

MIT License
