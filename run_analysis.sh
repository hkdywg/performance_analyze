#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  AR-HUD应用程序性能分析${NC}"
echo -e "${CYAN}========================================${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} 需要 Python 3"
    exit 1
fi

# 检查依赖
echo -e "${BLUE}[INFO]${NC} 检查依赖..."
if ! python3 -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}[WARN]${NC} 缺少 pyyaml，正在安装..."
    pip3 install pyyaml -q
fi

# 配置文件
CONFIG_FILE="${PROJECT_DIR}/config/config.yaml"
REPORT_HTML="${PROJECT_DIR}/report/report.html"

# 解析命令行参数
SKIP_COLLECT=0
SKIP_REPORT=0
SHOW_HELP=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-collect)
            SKIP_COLLECT=1
            shift
            ;;
        --skip-report)
            SKIP_REPORT=1
            shift
            ;;
        -h|--help)
            SHOW_HELP=1
            shift
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} 未知参数: $1"
            SHOW_HELP=1
            shift
            ;;
    esac
done

if [ $SHOW_HELP -eq 1 ]; then
    cat << EOF
用法: $(basename "$0") [选项]

选项:
    --skip-collect    跳过数据采集（使用已有数据）
    --skip-report     跳过报告生成
    -h, --help        显示此帮助信息

示例:
    $(basename "$0")              # 采集数据并生成报告
    $(basename "$0") --skip-collect  # 仅生成报告

EOF
    exit 0
fi

# 步骤1: 数据采集
if [ $SKIP_COLLECT -eq 0 ]; then
    echo -e "${BLUE}[STEP 1/2]${NC} 数据采集"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}[ERROR]${NC} 配置文件不存在: $CONFIG_FILE"
        echo "请先创建配置文件或检查路径"
        exit 1
    fi

    bash "${SCRIPT_DIR}/analyze_remote.sh" -c "$CONFIG_FILE"

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR]${NC} 数据采集失败"
        exit 1
    fi

    echo -e "${GREEN}[SUCCESS]${NC} 数据采集完成"
else
    echo -e "${YELLOW}[SKIP]${NC} 跳过数据采集"
fi

# 步骤2: 生成报告
if [ $SKIP_REPORT -eq 0 ]; then
    echo -e "${BLUE}[STEP 2/2]${NC} 生成报告"
    echo -e "${BLUE}========================================${NC}"

    python3 "${SCRIPT_DIR}/generate_report.py"

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR]${NC} 报告生成失败"
        exit 1
    fi

    echo -e "${GREEN}[SUCCESS]${NC} 报告生成完成"
else
    echo -e "${YELLOW}[SKIP]${NC} 跳过报告生成"
fi

# 完成
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}[完成]${NC} 性能分析完成！"
echo -e "${CYAN}========================================${NC}"
echo -e "报告文件: ${REPORT_HTML}"
echo -e "使用浏览器打开查看结果"
