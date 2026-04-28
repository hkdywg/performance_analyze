# Linux 性能分析

本项目提供两套Linux性能分析skill：通用的系统性能分析和专用的图形显示应用程序性能分析。

## 项目结构

```
performance/
├── SKILL.md                    # Linux系统性能分析skill
├── SKILL_GRAPHICS.md          # 图形显示应用程序性能分析skill
├── README_GRAPHICS.md         # 图形分析详细使用文档
├── scripts/
│   ├── analyze_remote.sh       # SSH远程数据采集脚本（图形分析用）
│   └── generate_report.py      # HTML报告生成器（图形分析用）
├── config/
│   ├── config.yaml             # 配置文件
│   └── config.yaml.example     # 配置文件示例
└── references/
    ├── cpu.md                  # CPU分析参考
    ├── memory.md               # 内存分析参考
    ├── io.md                   # I/O分析参考
    ├── network.md              # 网络分析参考
    ├── gpu.md                  # GPU分析参考
    ├── wayland.md              # Wayland/Weston分析参考
    ├── embedded.md             # 嵌入式系统特殊考量
    └── report-template.md      # 报告模板
```

## Skill 1: Linux 系统性能分析

诊断Linux系统在CPU、内存、I/O和网络方面的性能问题。

**使用方式**：当用户要求分析Linux主机性能时使用此skill。

详细说明请参见 [SKILL.md](SKILL.md)。

## Skill 2: 图形显示应用程序性能分析

针对嵌入式Linux系统的图形显示应用程序进行性能分析，支持通过SSH远程分析并生成HTML报告。

**功能特点**：
- 通用GPU信息获取（不区分NVIDIA/AMD/Intel）
- 针对嵌入式系统（仅支持Wayland或DRM，无X11）
- SSH远程数据采集
- 自动生成HTML分析报告

**使用方式**：
1. 配置 `config/config.yaml`
2. 运行 `./scripts/analyze_remote.sh`
3. 运行 `python3 scripts/generate_report.py`
4. 查看生成的 `report/report.html`

详细说明请参见 [SKILL_GRAPHICS.md](SKILL_GRAPHICS.md) 或 [README_GRAPHICS.md](README_GRAPHICS.md)。

## 快速开始

### Linux系统性能分析

直接使用SKILL.md中描述的工作流程和命令进行诊断。

### 图形显示应用性能分析

```bash
# 1. 安装依赖
pip3 install pyyaml

# 2. 配置目标设备
vim config/config.yaml

# 3. 运行数据采集
./scripts/analyze_remote.sh -c config/config.yaml

# 4. 生成HTML报告
python3 scripts/generate_report.py -d ./report
```

## 参考文档

| 文档 | 用途 |
|------|------|
| [cpu.md](references/cpu.md) | CPU性能分析命令和解读 |
| [memory.md](references/memory.md) | 内存性能分析命令和解读 |
| [io.md](references/io.md) | I/O性能分析命令和解读 |
| [network.md](references/network.md) | 网络性能分析命令和解读 |
| [gpu.md](references/gpu.md) | GPU性能分析参考 |
| [wayland.md](references/wayland.md) | Wayland/Weston分析参考 |
| [embedded.md](references/embedded.md) | 嵌入式系统特殊考量 |
| [report-template.md](references/report-template.md) | 报告模板格式 |
