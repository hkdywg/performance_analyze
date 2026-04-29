#!/bin/bash

#==============================================================================
# 图形显示应用程序性能分析 - 远程数据采集脚本
# 用于通过SSH连接远程嵌入式设备，采集GPU、Wayland/Weston及应用程序性能数据
#==============================================================================

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/config.yaml"

# 默认值
OUTPUT_DIR="${PROJECT_DIR}/report"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REMOTE_DATA_FILE="${OUTPUT_DIR}/remote_data_${TIMESTAMP}.json"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#-------------------------------------------------------------------------------
# 帮助信息
#-------------------------------------------------------------------------------
show_help() {
    cat << EOF
用法: $(basename "$0") [选项]

通过SSH连接远程嵌入式设备，采集图形显示应用程序性能数据。

选项:
    -c, --config FILE      指定配置文件路径 (默认: ${CONFIG_FILE})
    -o, --output DIR      指定输出目录 (默认: ${OUTPUT_DIR})
    -h, --help            显示此帮助信息
    -v, --verbose         显示详细输出

示例:
    $(basename "$0") -c config/config.yaml
    $(basename "$0") -o ./my_report -v

EOF
}

#-------------------------------------------------------------------------------
# 日志函数
#-------------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#-------------------------------------------------------------------------------
# 解析命令行参数
#-------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

#-------------------------------------------------------------------------------
# 检查依赖
#-------------------------------------------------------------------------------
check_dependencies() {
    log_info "检查依赖工具..."
    
    local missing_tools=()
    
    for tool in ssh scp yaml python3; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "缺少必要的工具: ${missing_tools[*]}"
        log_info "安装建议: pip install pyyaml"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

#-------------------------------------------------------------------------------
# 读取配置文件
#-------------------------------------------------------------------------------
parse_yaml() {
    local file=$1
    local prefix=$2
    
    if [ ! -f "$file" ]; then
        log_error "配置文件不存在: $file"
        exit 1
    fi
    
    # 使用环境变量传递文件路径
    export YAML_CONFIG_FILE="$file"
    
    python3 -c "
import yaml
import os
import json

file_path = os.environ.get('YAML_CONFIG_FILE')
if not file_path:
    print(json.dumps({'error': 'No config file specified'}))
    exit(1)

try:
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
    print(json.dumps(config))
except Exception as e:
    print(json.dumps({'error': str(e)}))
    exit(1)
"
}

load_config() {
    log_info "读取配置文件: ${CONFIG_FILE}"
    
    # 转换为绝对路径
    local abs_config_file="$(cd "$(dirname "$CONFIG_FILE")" && pwd)/$(basename "$CONFIG_FILE")"
    export YAML_CONFIG_FILE="$abs_config_file"
    CONFIG_JSON=$(parse_yaml "$abs_config_file")
    
    SSH_HOST=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh',{}).get('host',''))")
    SSH_PORT=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh',{}).get('port','22'))")
    SSH_USER=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh',{}).get('user','root'))")
    SSH_KEY=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh',{}).get('key_path',''))")
    SSH_PASS=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh',{}).get('password',''))")
    
    APP_NAME=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('target',{}).get('app_name',''))")
    PROCESS_PATTERN=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('target',{}).get('process_pattern',''))")
    DISPLAY_SERVER=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('target',{}).get('display_server','wayland'))")
    COMPOSITOR=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('target',{}).get('compositor','weston'))")
    
    DURATION=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('analysis',{}).get('duration','10'))")
    INTERVAL=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('analysis',{}).get('interval','1'))")
    
    if [ -z "$SSH_HOST" ] || [ -z "$APP_NAME" ]; then
        log_error "配置文件缺少必要字段: ssh.host 或 target.app_name"
        exit 1
    fi
    
    log_success "配置加载完成"
    log_info "  SSH: ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
    log_info "  目标应用: ${APP_NAME}"
    log_info "  显示服务器: ${DISPLAY_SERVER}"
}

#-------------------------------------------------------------------------------
# SSH连接函数
#-------------------------------------------------------------------------------
ssh_cmd() {
    local cmd="$1"
    
    # 解析密钥路径为绝对路径
    local ssh_key_file=""
    if [ -n "$SSH_KEY" ]; then
        ssh_key_file=$(eval echo "$SSH_KEY")
        # 检查密钥文件是否存在
        if [ ! -f "$ssh_key_file" ]; then
            ssh_key_file=""
        fi
    fi
    
    # 优先使用密钥认证（如果密钥文件存在且有效）
    if [ -n "$ssh_key_file" ]; then
        if ssh -p "$SSH_PORT" -i "$ssh_key_file" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o BatchMode=yes \
            -o PasswordAuthentication=no \
            "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null; then
            return 0
        fi
        # 密钥认证失败，继续尝试其他方式

        log_info "  ----1"
        log_info "  key is $ssh_key_file"
    fi
    
    # 其次尝试使用 sshpass（如果配置了密码且 sshpass 可用）
    if [ -n "$SSH_PASS" ] && command -v sshpass &> /dev/null; then
        if sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null; then
            return 0
        fi
        log_info "  ----2"
    fi
    
    log_info "  $SSH_PASS $SSH_USER $SSH_PORT"
    # 使用 expect 处理交互式认证
    if command -v expect &> /dev/null && [ -n "$SSH_PASS" ]; then
        log_info "----------ss"
        if expect -c "
            set timeout 30
            spawn ssh -p $SSH_PORT -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${SSH_USER}@${SSH_HOST} $cmd
            expect {
                \"password:\" {
                    stty -echo
                    send \"$SSH_PASS\r\"
                    stty echo
                }
                \"(yes/no)?\" {
                    send \"yes\r\"
                    expect \"password:\"
                    stty -echo
                    send \"$SSH_PASS\r\"
                    stty echo
                }
                eof
            }
        " 2>/dev/null | grep -v "spawn\|expect\|send\|stty" > /dev/null; then
            return 0
        fi

        log_info "  ----3"
    fi
    
    # 最后尝试无密码交互式连接
    ssh -p "$SSH_PORT" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null

        log_info "  ----4"
}

#-------------------------------------------------------------------------------
# 测试SSH连接
#-------------------------------------------------------------------------------
test_connection() {
    log_info "测试SSH连接..."
    
    # 首先检查网络连通性
    if ! ping -c 1 -W 2 "$SSH_HOST" &> /dev/null; then
        log_error "无法到达主机 ${SSH_HOST}，请检查网络连接"
        exit 1
    fi
    
    if ssh_cmd "echo 'Connection OK'" &> /dev/null; then
        log_success "SSH连接成功"
    else
        log_error "SSH连接失败，请检查以下配置："
        log_info "  1. SSH密钥认证: 确保公钥已添加到远程主机的 ~/.ssh/authorized_keys"
        log_info "  2. 或在配置文件中设置 password 字段"
        log_info "  3. 或安装 sshpass: sudo apt install sshpass"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# 创建输出目录
#-------------------------------------------------------------------------------
setup_output() {
    mkdir -p "$OUTPUT_DIR"
    log_info "输出目录: ${OUTPUT_DIR}"
}

#-------------------------------------------------------------------------------
# 采集系统信息
#-------------------------------------------------------------------------------
collect_system_info() {
    log_info "采集系统信息..."
    
    ssh_cmd 'cat /etc/os-release' > "${OUTPUT_DIR}/os_release.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/os_release.txt"
    ssh_cmd 'uname -a' > "${OUTPUT_DIR}/uname.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/uname.txt"
    ssh_cmd 'cat /proc/cpuinfo' > "${OUTPUT_DIR}/cpuinfo.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/cpuinfo.txt"
    ssh_cmd 'nproc' > "${OUTPUT_DIR}/nproc.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/nproc.txt"
    
    log_success "系统信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集内存信息
#-------------------------------------------------------------------------------
collect_memory_info() {
    log_info "采集内存信息..."
    
    ssh_cmd 'free -h' > "${OUTPUT_DIR}/memory.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/memory.txt"
    ssh_cmd 'cat /proc/meminfo' > "${OUTPUT_DIR}/meminfo.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/meminfo.txt"
    
    log_success "内存信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集GPU信息（通用方式）
#-------------------------------------------------------------------------------
collect_gpu_info() {
    log_info "采集GPU信息..."
    
    # DRM设备列表
    ssh_cmd 'ls -la /sys/class/drm/' > "${OUTPUT_DIR}/drm_devices.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_devices.txt"
    
    # GPU基本信息（Vendor/Device ID - 通用方式）
    for card in /sys/class/drm/card*/device; do
        ssh_cmd "cat ${card}/vendor 2>/dev/null; cat ${card}/device 2>/dev/null" > "${OUTPUT_DIR}/gpu_basic.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/gpu_basic.txt"
    done
    
    # GPU内存信息
    ssh_cmd 'cat /sys/class/drm/card*/device/mem_info_vram 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/gpu_vram.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/gpu_vram.txt"
    ssh_cmd 'cat /sys/class/drm/card*/device/mem_info_gtt 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/gpu_gtt.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/gpu_gtt.txt"
    
    # GPU利用率（如果支持）
    ssh_cmd 'cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/gpu_utilization.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/gpu_utilization.txt"
    
    # DRM状态（用于诊断）
    ssh_cmd 'cat /sys/kernel/debug/dri/0/state 2>/dev/null || cat /sys/kernel/debug/dri/0/mm 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/drm_state.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_state.txt"
    
    # DRM设备状态
    ssh_cmd 'cat /sys/class/drm/card*/status 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/drm_status.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_status.txt"
    
    log_success "GPU信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集Wayland/Weston信息
#-------------------------------------------------------------------------------
collect_wayland_info() {
    log_info "采集Wayland/Weston信息..."
    
    # Weston信息
    ssh_cmd 'weston-info 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/weston_info.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/weston_info.txt"
    
    # Weston日志
    ssh_cmd 'journalctl -u weston --since "30 minutes ago" 2>/dev/null | tail -100 || echo "N/A"' > "${OUTPUT_DIR}/weston_log.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/weston_log.txt"
    
    # Wayland socket
    ssh_cmd 'ls -la /run/user/*/wayland-* 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/wayland_sockets.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/wayland_sockets.txt"
    
    # Weston进程状态
    ssh_cmd 'ps aux | grep -E "weston|wayland" | grep -v grep' > "${OUTPUT_DIR}/compositor_process.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/compositor_process.txt"
    
    log_success "Wayland/Weston信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集DRM直接信息（无Wayland时）
#-------------------------------------------------------------------------------
collect_drm_info() {
    log_info "采集DRM直接信息..."
    
    # DRM设备节点
    ssh_cmd 'ls -la /dev/dri/' > "${OUTPUT_DIR}/drm_nodes.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_nodes.txt"
    
    # Framebuffer信息
    ssh_cmd 'cat /sys/class/graphics/fb*/virtual_size 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/framebuffer.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/framebuffer.txt"
    
    # fbset信息
    ssh_cmd 'fbset -i 2>/dev/null || echo "N/A"' > "${OUTPUT_DIR}/fbset.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/fbset.txt"
    
    log_success "DRM信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集目标应用进程信息
#-------------------------------------------------------------------------------
collect_app_info() {
    log_info "采集应用程序信息..."
    
    # 查找目标进程
    ssh_cmd "ps aux | grep -E '${PROCESS_PATTERN}' | grep -v grep" > "${OUTPUT_DIR}/app_process.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_process.txt"
    
    # 获取进程PID
    APP_PID=$(ssh_cmd "pidof ${APP_NAME} 2>/dev/null || ps aux | grep -E '${PROCESS_PATTERN}' | grep -v grep | awk '{print \$2}' | head -1" 2>/dev/null || echo "")
    
    if [ -n "$APP_PID" ]; then
        log_info "找到进程PID: ${APP_PID}"
        
        # 进程详细信息
        ssh_cmd "cat /proc/${APP_PID}/status" > "${OUTPUT_DIR}/app_status.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_status.txt"
        ssh_cmd "cat /proc/${APP_PID}/smaps_rollup" > "${OUTPUT_DIR}/app_smaps.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_smaps.txt"
        
        # 进程CPU使用
        ssh_cmd "pidstat -u -p ${APP_PID} ${INTERVAL} ${DURATION}" > "${OUTPUT_DIR}/app_cpu.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_cpu.txt"
        
        # 进程内存使用
        ssh_cmd "pidstat -r -p ${APP_PID} ${INTERVAL} ${DURATION}" > "${OUTPUT_DIR}/app_memory.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_memory.txt"
        
        # 进程IO使用
        ssh_cmd "pidstat -d -p ${APP_PID} ${INTERVAL} ${DURATION}" > "${OUTPUT_DIR}/app_io.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_io.txt"
        
        # 线程信息
        ssh_cmd "ps -eLf -p ${APP_PID}" > "${OUTPUT_DIR}/app_threads.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_threads.txt"
        
        # 文件描述符
        ssh_cmd "ls -la /proc/${APP_PID}/fd 2>/dev/null | wc -l || echo "N/A"" > "${OUTPUT_DIR}/app_fds.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_fds.txt"
        
        # 保存PID供后续使用
        echo "$APP_PID" > "${OUTPUT_DIR}/app_pid.txt"
    else
        log_warning "未找到目标进程: ${APP_NAME}"
        echo "N/A" > "${OUTPUT_DIR}/app_pid.txt"
    fi
    
    log_success "应用程序信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集系统负载和进程信息
#-------------------------------------------------------------------------------
collect_system_load() {
    log_info "采集系统负载信息..."
    
    # 系统负载
    ssh_cmd 'uptime' > "${OUTPUT_DIR}/uptime.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/uptime.txt"
    ssh_cmd 'vmstat 1 5' > "${OUTPUT_DIR}/vmstat.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/vmstat.txt"
    
    # top输出
    ssh_cmd 'top -b -n 1' > "${OUTPUT_DIR}/top.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/top.txt"
    
    # mpstat
    ssh_cmd 'mpstat -P ALL 1 3' > "${OUTPUT_DIR}/mpstat.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/mpstat.txt"
    
    log_success "系统负载信息采集完成"
}

#-------------------------------------------------------------------------------
# 生成JSON汇总文件
#-------------------------------------------------------------------------------
generate_json_summary() {
    log_info "生成JSON汇总文件..."
    
    cat > "${REMOTE_DATA_FILE}" << 'JSONEOF'
{
  "timestamp": "TIMESTAMP_PLACEHOLDER",
  "ssh_host": "SSH_HOST_PLACEHOLDER",
  "app_name": "APP_NAME_PLACEHOLDER",
  "display_server": "DISPLAY_SERVER_PLACEHOLDER",
  "compositor": "COMPOSITOR_PLACEHOLDER",
  "files": {}
}
JSONEOF
    
    # 替换占位符
    sed -i "s/TIMESTAMP_PLACEHOLDER/${TIMESTAMP}/g" "${REMOTE_DATA_FILE}"
    sed -i "s/SSH_HOST_PLACEHOLDER/${SSH_HOST}/g" "${REMOTE_DATA_FILE}"
    sed -i "s/APP_NAME_PLACEHOLDER/${APP_NAME}/g" "${REMOTE_DATA_FILE}"
    sed -i "s/DISPLAY_SERVER_PLACEHOLDER/${DISPLAY_SERVER}/g" "${REMOTE_DATA_FILE}"
    sed -i "s/COMPOSITOR_PLACEHOLDER/${COMPOSITOR}/g" "${REMOTE_DATA_FILE}"
    
    # 添加所有采集的文件内容
    export REMOTE_DATA_FILE="${REMOTE_DATA_FILE}"
    python3 -c "
import json
import os
import sys

output_file = os.environ.get('REMOTE_DATA_FILE')
if not output_file:
    print('Error: No output file specified')
    sys.exit(1)

# 确保输出目录路径正确
output_dir = os.path.dirname(output_file)
if not output_dir:
    output_dir = '.'

with open(output_file, 'r') as f:
    data = json.load(f)

# 添加所有txt文件内容（排除JSON文件本身）
for filename in os.listdir(output_dir):
    if filename.endswith('.txt'):
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                data['files'][filename] = content[:50000]  # 限制大小
        except Exception as e:
            data['files'][filename] = f'Error reading file: {e}'

with open(output_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('JSON summary generated')
"
    
    log_success "JSON汇总文件已生成: ${REMOTE_DATA_FILE}"
}

#-------------------------------------------------------------------------------
# 主函数
#-------------------------------------------------------------------------------
main() {
    echo "========================================"
    echo "  图形显示应用程序性能分析 - 远程采集"
    echo "========================================"
    echo ""
    
    #check_dependencies
    load_config
    setup_output
    test_connection
    
    echo ""
    log_info "开始采集性能数据..."
    echo ""

    ssh_cmd 'uname -a'
    exit
    
    collect_system_info
    collect_memory_info
    collect_gpu_info
    
    if [ "$DISPLAY_SERVER" = "wayland" ]; then
        collect_wayland_info
    else
        collect_drm_info
    fi
    
    collect_app_info
    collect_system_load
    generate_json_summary
    
    echo ""
    echo "========================================"
    log_success "数据采集完成!"
    echo "========================================"
    echo ""
    log_info "采集的数据保存在: ${OUTPUT_DIR}"
    log_info "下一步: 运行 generate_report.py 生成HTML报告"
    echo ""
}

# 执行主函数
main
