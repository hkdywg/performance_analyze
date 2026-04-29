#!/bin/bash

#==============================================================================
# AR-HUD应用程序性能分析 - 远程数据采集脚本
# 用于通过SSH连接远程嵌入式设备，采集操作系统及应用程序性能数据
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
        if [ ! -f "$ssh_key_file" ]; then
            ssh_key_file=""
        fi
    fi

    # 优先使用密钥认证
    if [ -n "$ssh_key_file" ]; then
        if ssh -p "$SSH_PORT" -i "$ssh_key_file" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o BatchMode=yes \
            -o PasswordAuthentication=no \
            "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null; then
            return 0
        fi
    fi

    # 使用 sshpass（最可靠）
    if [ -n "$SSH_PASS" ] && command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null
        return $?
    fi

    # 使用 Python paramiko（如果可用）
    if [ -n "$SSH_PASS" ]; then
        # 创建临时Python脚本
        local py_script
        py_script=$(mktemp /tmp/ssh_cmd_XXXXXX.py)

        cat > "$py_script" << 'PYEOF'
#!/usr/bin/env python3
import sys
import os

host = os.environ.get("SSH_HOST", "")
port = int(os.environ.get("SSH_PORT", "22"))
user = os.environ.get("SSH_USER", "")
password = os.environ.get("SSH_PASS", "")
cmd = sys.argv[1] if len(sys.argv) > 1 else "true"

try:
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=port, username=user, password=password, timeout=30, allow_agent=False, look_for_keys=False)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    client.close()
    if error and not output:
        sys.stderr.write(error)
    sys.stdout.write(output)
except Exception as e:
    sys.exit(1)
PYEOF

        chmod +x "$py_script"
        export SSH_HOST SSH_PORT SSH_USER SSH_PASS
        "$py_script" "$cmd"
        local result=$?
        rm -f "$py_script"
        return $result
    fi

    # 使用 expect 作为最后方案
    if [ -n "$SSH_PASS" ] && command -v expect &> /dev/null; then
        expect -c "
            set timeout 30
            spawn ssh -p ${SSH_PORT} -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} ${cmd}
            expect {
                \"password:\" {
                    send \"${SSH_PASS}\r\"
                    expect eof
                }
                \"yes/no\" {
                    send \"yes\r\"
                    expect \"password:\"
                    send \"${SSH_PASS}\r\"
                    expect eof
                }
                timeout {
                    exit 1
                }
                eof {
                    exit 1
                }
            }
        " 2>/dev/null
        return $?
    fi

    # 最后尝试无密码连接
    ssh -p "$SSH_PORT" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null
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
    
    # 查找目标进程 - 多种方式获取PID
    ssh_cmd "ps aux | grep -E '${PROCESS_PATTERN}' | grep -v grep" > "${OUTPUT_DIR}/app_process.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_process.txt"

    # 获取进程PID - 使用更可靠的方式
    APP_PID=$(ssh_cmd "pgrep -f '${PROCESS_PATTERN}' 2>/dev/null | head -1 || pgrep '${APP_NAME}' 2>/dev/null | head -1 || ps aux | grep -E '${PROCESS_PATTERN}' | grep -v grep | awk '{print \$2}' | head -1" 2>/dev/null | tr -d '\r\n' || echo "")

    # 清理PID中的非数字字符，只保留纯数字
    APP_PID=$(echo "$APP_PID" | tr -cd '[:digit:]')

    if [ -n "$APP_PID" ] && [ "$APP_PID" != "N/A" ] && [ "$APP_PID" != "" ]; then
        log_info "找到进程PID: ${APP_PID}"
        
        # 进程详细信息
        ssh_cmd "cat /proc/${APP_PID}/status" > "${OUTPUT_DIR}/app_status.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_status.txt"
        ssh_cmd "cat /proc/${APP_PID}/smaps_rollup" > "${OUTPUT_DIR}/app_smaps.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_smaps.txt"

        # 进程CPU使用 - 使用top获取实时CPU和内存
        ssh_cmd "top -b -n 1 | grep -E '^[[:space:]]*${APP_PID}'" > "${OUTPUT_DIR}/app_cpu.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_cpu.txt"

        # 进程内存使用 - 使用top获取内存详情
        ssh_cmd "top -b -n 1 | grep -E '^[[:space:]]*${APP_PID}' && cat /proc/${APP_PID}/status | grep -E 'VmRSS|VmSize|VmData|VmStk|VmPeak'" > "${OUTPUT_DIR}/app_memory.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_memory.txt"

        # 进程IO使用 - 使用ps或/proc/io替代pidstat
        ssh_cmd "cat /proc/${APP_PID}/io 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/app_io.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_io.txt"
        
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
# 周期性采样 CPU 和内存数据（用于折线图）
#-------------------------------------------------------------------------------
collect_performance_samples() {
    log_info "开始周期性采样 CPU 和内存数据..."
    log_info "采样参数: 持续时间=${DURATION}s, 间隔=${INTERVAL}s"
    
    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ] || [ "$APP_PID" = "" ]; then
        log_warning "未找到目标进程PID，跳过采样"
        echo "时间(s),CPU%,RSS(MB),VSZ(MB)" > "${OUTPUT_DIR}/perf_samples.csv"
        echo "N/A,N/A,N/A,N/A" >> "${OUTPUT_DIR}/perf_samples.csv"
        return
    fi
    
    # 计算采样次数
    local sample_count=$((DURATION / INTERVAL))
    [ "$sample_count" -lt 1 ] && sample_count=1
    
    # 创建CSV文件
    echo "时间(s),CPU%,RSS(MB),VSZ(MB)" > "${OUTPUT_DIR}/perf_samples.csv"
    
    local elapsed=0
    local iteration=0
    
    while [ "$elapsed" -lt "$DURATION" ]; do
        iteration=$((iteration + 1))
        local current_time=$((iteration * INTERVAL))
        
        # 获取进程 CPU 和内存 - 使用ps获取更可靠的格式
        # 格式: PID COMMAND %CPU %MEM RSS VSZ
        local app_data=$(ssh_cmd "ps -p ${APP_PID} -o pid,comm,%cpu,%mem,rss,vsz --no-headers 2>/dev/null" | tr -s ' ')
        if [ -n "$app_data" ]; then
            # 解析 ps 输出: PID COMMAND %CPU %MEM RSS VSZ
            local app_cpu=$(echo "$app_data" | awk '{print $3}')
            local app_rss=$(echo "$app_data" | awk '{print $5}')  # RSS in KB
            local app_vsz=$(echo "$app_data" | awk '{print $6}')  # VSZ in KB
            
            # 转换 RSS 和 VSZ 为 MB
            local rss_mb=$(echo "$app_rss" | awk '{printf "%.1f", $1/1024}')
            local vsz_mb=$(echo "$app_vsz" | awk '{printf "%.1f", $1/1024}')
            
            echo "${current_time},${app_cpu},${rss_mb},${vsz_mb}" >> "${OUTPUT_DIR}/perf_samples.csv"
            log_info "采样 ${iteration}/${sample_count}: 时间=${current_time}s, CPU=${app_cpu}%, RSS=${rss_mb}MB"
        else
            echo "${current_time},N/A,N/A,N/A" >> "${OUTPUT_DIR}/perf_samples.csv"
        fi
        
        elapsed=$((elapsed + INTERVAL))
        if [ "$elapsed" -lt "$DURATION" ]; then
            sleep "$INTERVAL"
        fi
    done
    
    log_success "周期性采样完成，共 ${iteration} 次采样"
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
# 采集火焰图数据 (perf)
#-------------------------------------------------------------------------------
collect_flamegraph_data() {
    log_info "采集火焰图数据..."

    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ] || [ "$APP_PID" = "" ]; then
        log_warning "未找到目标进程PID，跳过火焰图采集"
        echo "N/A" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"
        echo "N/A" > "${OUTPUT_DIR}/flamegraph.svg"
        echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
        return
    fi

    # 检查perf是否可用
    local perf_available=$(ssh_cmd "which perf 2>/dev/null || echo 'not_found'" | tr -d '\r\n')
    if [ "$perf_available" = "not_found" ]; then
        log_warning "perf工具不可用，尝试使用其他方法"
        # 尝试使用 /proc/profile 或其他替代方案
        collect_stack_traces_alternative
        return
    fi

    log_info "使用perf record采集PID=${APP_PID}的调用栈..."

    # 清理旧数据
    ssh_cmd "rm -f /tmp/perf.data"

    # 使用perf record采集数据（系统级采集，指定输出文件）
    # 使用nohup确保命令在远程后台运行
    ssh_cmd "rm -f /tmp/perf.data && nohup sh -c 'perf record -F 99 -a -g -o /tmp/perf.data -- sleep ${DURATION}' > /tmp/perf.log 2>&1 &"
    log_info "perf record正在后台运行..."

    # 等待采集完成
    sleep $((DURATION + 5))

    # 获取perf.data文件
    local perf_data_exists=$(ssh_cmd "ls -la /tmp/perf.data 2>/dev/null | wc -l" | tr -d '\r\n')
    if [ "$perf_data_exists" != "0" ] && [ -n "$perf_data_exists" ]; then
        # 检查文件大小
        local perf_size=$(ssh_cmd "stat -c%s /tmp/perf.data 2>/dev/null" | tr -d '\r\n')
        log_info "perf.data 大小: ${perf_size} bytes"

        # 生成perf报告
        ssh_cmd "perf report --stdio --no-children -g none -i /tmp/perf.data 2>/dev/null" > "${OUTPUT_DIR}/perf_report.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"

        # 生成调用栈文本（用于火焰图）
        ssh_cmd "perf script -i /tmp/perf.data 2>/dev/null | stackcollapse-perf.pl 2>/dev/null || perf script -i /tmp/perf.data 2>/dev/null" > "${OUTPUT_DIR}/stack_counts.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"

        log_success "火焰图数据采集完成"
    else
        log_warning "perf record未能生成数据文件"
        echo "采集失败" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"
        echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
    fi
}

#-------------------------------------------------------------------------------
# 备选方案：采集调用栈（不使用perf）
#-------------------------------------------------------------------------------
collect_stack_traces_alternative() {
    log_info "使用备选方案采集调用栈..."

    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ]; then
        echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
        return
    fi

    # 使用 /proc/PID/stack 获取内核栈
    ssh_cmd "cat /proc/${APP_PID}/stack 2>/dev/null" > "${OUTPUT_DIR}/kernel_stack.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/kernel_stack.txt"

    # 获取线程栈信息
    local tids=$(ssh_cmd "ls /proc/${APP_PID}/task/ 2>/dev/null" | tr -d '\r\n' || echo "")
    if [ -n "$tids" ]; then
        ssh_cmd "for tid in ${tids}; do echo \"=== TID: \$tid ===\"; cat /proc/${APP_PID}/task/\$tid/stack 2>/dev/null; done" > "${OUTPUT_DIR}/thread_stacks.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/thread_stacks.txt"
    fi

    # 尝试使用 eBPF / funccount（如可用）
    local bcc_available=$(ssh_cmd "which funccount 2>/dev/null || echo 'not_found'" | tr -d '\r\n')
    if [ "$bcc_available" != "not_found" ]; then
        log_info "使用 BCC/funccount 采集函数调用频率..."
        ssh_cmd "funccount -d 5 'gl*' 'egl*' 'drm*' 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/function_counts.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/function_counts.txt"
    else
        echo "N/A" > "${OUTPUT_DIR}/function_counts.txt"
    fi

    # 使用 strace 采样（短时间）
    log_info "使用strace采样系统调用..."
    ssh_cmd "timeout 5 strace -p ${APP_PID} -c -f 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/syscall_counts.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/syscall_counts.txt"

    log_success "备选方案数据采集完成"
}

#-------------------------------------------------------------------------------
# 采集 OpenGL/EGL/DRM 调用信息
#-------------------------------------------------------------------------------
collect_graphics_traces() {
    log_info "采集图形API调用信息..."

    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ]; then
        log_warning "未找到目标进程PID，跳过图形API采集"
        echo "N/A" > "${OUTPUT_DIR}/opengl_info.txt"
        echo "N/A" > "${OUTPUT_DIR}/egl_info.txt"
        echo "N/A" > "${OUTPUT_DIR}/drm_info.txt"
        echo "N/A" > "${OUTPUT_DIR}/graphics_env.txt"
        return
    fi

    # 获取图形环境变量
    ssh_cmd "cat /proc/${APP_PID}/environ 2>/dev/null | tr '\0' '\n' | grep -E 'DISPLAY|WAYLAND|EGL|GLX|MESA'" > "${OUTPUT_DIR}/graphics_env.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/graphics_env.txt"

    # 获取OpenGL信息（如应用有显示连接）
    ssh_cmd "export DISPLAY=:0; glxinfo -B 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/opengl_info.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/opengl_info.txt"

    # 获取EGL信息
    ssh_cmd "export EGL_LOG_LEVEL=info; cat /sys/kernel/debug/dri/0/state 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/drm_state_debug.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_state_debug.txt"

    # DRM统计信息
    ssh_cmd "cat /sys/kernel/debug/dri/0/clients 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/drm_clients.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_clients.txt"

    # GPU内存分配信息
    ssh_cmd "cat /sys/kernel/debug/dri/0/mm 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/gpu_memory_allocs.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/gpu_memory_allocs.txt"

    # Vulkan信息（如可用）
    local vulkan_available=$(ssh_cmd "which vulkaninfo 2>/dev/null || echo 'not_found'" | tr -d '\r\n')
    if [ "$vulkan_available" != "not_found" ]; then
        ssh_cmd "vulkaninfo --summary 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/vulkan_info.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/vulkan_info.txt"
    else
        echo "N/A" > "${OUTPUT_DIR}/vulkan_info.txt"
    fi

    # 使用 ftrace 追踪 DRM 调用（如有权限）
    collect_drm_traces

    log_success "图形API信息采集完成"
}

#-------------------------------------------------------------------------------
# 采集 DRM 调用追踪
#-------------------------------------------------------------------------------
collect_drm_traces() {
    log_info "采集DRM调用追踪..."

    # 检查ftrace是否可用
    local trace_available=$(ssh_cmd "[ -d /sys/kernel/debug/tracing ] && echo 'available' || echo 'not_available'" | tr -d '\r\n')
    if [ "$trace_available" != "available" ]; then
        log_warning "ftrace不可用，跳过DRM追踪"
        echo "N/A" > "${OUTPUT_DIR}/drm_traces.txt"
        return
    fi

    # 检查是否有写权限
    local can_write=$(ssh_cmd "echo 1 > /sys/kernel/debug/tracing/tracing_on 2>/dev/null && echo 'yes' || echo 'no'" | tr -d '\r\n')
    if [ "$can_write" != "yes" ]; then
        log_warning "无ftrace写入权限，跳过DRM追踪"
        echo "权限不足" > "${OUTPUT_DIR}/drm_traces.txt"
        return
    fi

    # 设置ftrace追踪DRM事件
    ssh_cmd "cd /sys/kernel/debug/tracing && \
        echo nop > current_tracer && \
        echo 0 > tracing_on && \
        echo > trace && \
        echo 1 > events/drm/drm_vblank_event/enable 2>/dev/null || true && \
        echo 1 > events/drm/drm_flip_complete/enable 2>/dev/null || true && \
        echo 1 > events/i915/enable 2>/dev/null || true && \
        echo 1 > tracing_on && \
        sleep ${DURATION} && \
        echo 0 > tracing_on && \
        cat trace" > "${OUTPUT_DIR}/drm_traces.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/drm_traces.txt"

    # 恢复ftrace设置
    ssh_cmd "cd /sys/kernel/debug/tracing && \
        echo nop > current_tracer && \
        echo > events/enable && \
        echo 0 > tracing_on 2>/dev/null || true" 2>/dev/null

    log_success "DRM追踪采集完成"
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

# 添加所有txt和csv文件内容
for filename in os.listdir(output_dir):
    if filename.endswith('.txt') or filename.endswith('.csv'):
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                data['files'][filename] = content[:100000]  # 增大限制
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

    # 周期性采样 CPU 和内存（用于折线图）
    collect_performance_samples

    # 火焰图数据采集
    collect_flamegraph_data

    # 图形API追踪
    collect_graphics_traces

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
