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
    
    for tool in ssh scp python3; do
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

    # 解析密钥路径为绝对路径
    if [ -n "$SSH_KEY" ]; then
        SSH_KEY=$(eval echo "$SSH_KEY")
        if [ -f "$SSH_KEY" ]; then
            log_info "  SSH密钥文件存在: ${SSH_KEY}"
        else
            log_warning "  SSH密钥文件不存在: ${SSH_KEY}，将使用密码认证"
            SSH_KEY=""
        fi
    fi

    # 导出变量供子函数使用
    export SSH_HOST SSH_PORT SSH_USER SSH_KEY SSH_PASS

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
    if [ -n "$SSH_KEY" ]; then
        log_info "  认证方式: SSH密钥"
    elif [ -n "$SSH_PASS" ]; then
        log_info "  认证方式: 密码"
    else
        log_warning "  认证方式: 无密码（可能需要手动输入）"
    fi
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

    # 使用密钥认证
    if [ -n "$ssh_key_file" ]; then
        ssh -p "$SSH_PORT" -i "$ssh_key_file" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o BatchMode=yes \
            -o PasswordAuthentication=no \
            "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null
        return $?
    fi

    # 最后尝试无密码连接
    ssh -p "$SSH_PORT" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        "${SSH_USER}@${SSH_HOST}" "$cmd" 2>/dev/null
}

#-------------------------------------------------------------------------------
# SCP文件拷贝函数 - 使用SSH远程执行cat传输
#-------------------------------------------------------------------------------
scp_copy() {
    local remote_file="$1"
    local local_file="$2"

    # 检查参数
    if [ -z "$remote_file" ] || [ -z "$local_file" ]; then
        log_error "scp_copy: 缺少参数"
        return 1
    fi

    # 确保local_file是文件路径，不是目录
    if [ -d "$local_file" ]; then
        log_error "scp_copy: 目标路径是目录而非文件: ${local_file}"
        return 1
    fi

    # 确保输出目录存在
    local local_dir="$(dirname "$local_file")"
    if [ -n "$local_dir" ] && [ "$local_dir" != "." ]; then
        mkdir -p "$local_dir"
    fi

    log_info "使用SSH方式拷贝文件: ${remote_file} -> ${local_file}"

    # 使用 sshpass（最可靠）
    if [ -n "$SSH_PASS" ] && command -v sshpass &> /dev/null; then
        log_info "使用sshpass认证拷贝文件..."
        sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            "${SSH_USER}@${SSH_HOST}" "cat ${remote_file}" > "$local_file" 2>/dev/null
        return $?
    fi

    # 使用 Python paramiko（如果可用）
    if [ -n "$SSH_PASS" ]; then
        local py_script
        py_script=$(mktemp /tmp/scp_copy_XXXXXX.py)

        cat > "$py_script" << 'PYEOF'
#!/usr/bin/env python3
import sys
import os
import paramiko

host = os.environ.get("SSH_HOST", "")
port = int(os.environ.get("SSH_PORT", "22"))
user = os.environ.get("SSH_USER", "")
password = os.environ.get("SSH_PASS", "")
remote_path = sys.argv[1] if len(sys.argv) > 1 else ""
local_path = sys.argv[2] if len(sys.argv) > 2 else ""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=port, username=user, password=password, timeout=30)
    stdin, stdout, stderr = client.exec_command(f'cat {remote_path}', timeout=120)
    data = stdout.read()
    client.close()
    with open(local_path, 'wb') as f:
        f.write(data)
except Exception as e:
    print(f"SSH error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

        chmod +x "$py_script"
        export SSH_HOST SSH_PORT SSH_USER SSH_PASS
        log_info "使用Python paramiko拷贝文件..."
        "$py_script" "$remote_file" "$local_file"
        local result=$?
        rm -f "$py_script"
        return $result
    fi

    # 使用 expect 作为最后方案
    if [ -n "$SSH_PASS" ] && command -v expect &> /dev/null; then
        log_info "使用expect拷贝文件..."
        expect -c "
            set timeout 120
            spawn ssh -p ${SSH_PORT} -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} cat ${remote_file}
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
        " > "$local_file" 2>/dev/null
        return $?
    fi

    # 解析密钥路径为绝对路径
    local ssh_key_file=""
    if [ -n "$SSH_KEY" ]; then
        ssh_key_file=$(eval echo "$SSH_KEY")
        if [ -f "$ssh_key_file" ]; then
            log_info "使用SSH密钥认证拷贝文件..."
            ssh -p "$SSH_PORT" -i "$ssh_key_file" \
                -o StrictHostKeyChecking=no \
                -o ConnectTimeout=10 \
                "${SSH_USER}@${SSH_HOST}" "cat ${remote_file}" > "$local_file" 2>/dev/null
            return $?
        fi
    fi

    # 最后尝试无密码连接
    log_warning "尝试无密码连接..."
    ssh -p "$SSH_PORT" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        "${SSH_USER}@${SSH_HOST}" "cat ${remote_file}" > "$local_file" 2>/dev/null
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
        ssh_cmd "cat /proc/${APP_PID}/stat" > "${OUTPUT_DIR}/app_stat.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_stat.txt"
        ssh_cmd "cat /proc/${APP_PID}/smaps_rollup" > "${OUTPUT_DIR}/app_smaps.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_smaps.txt"

        # 进程CPU使用 - 使用top获取实时CPU和内存
        ssh_cmd "top -b -n 1 | grep -E '^[[:space:]]*${APP_PID}'" > "${OUTPUT_DIR}/app_cpu.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_cpu.txt"

        # 进程内存使用 - 使用top获取内存详情
        ssh_cmd "top -b -n 1 | grep -E '^[[:space:]]*${APP_PID}' && cat /proc/${APP_PID}/status | grep -E 'VmRSS|VmSize|VmData|VmStk|VmPeak'" > "${OUTPUT_DIR}/app_memory.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_memory.txt"

        # 进程IO使用 - 使用ps或/proc/io替代pidstat
        ssh_cmd "cat /proc/${APP_PID}/io 2>/dev/null || echo 'N/A'" > "${OUTPUT_DIR}/app_io.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_io.txt"
        
        # 线程信息 - 使用/proc/${APP_PID}/task/代替ps -eLf
        ssh_cmd '
            pid="'"${APP_PID}"'"
            echo "TID  PPID   UID    STAT   COMMAND"
            # 获取主线程信息
            if [ -f "/proc/${pid}/stat" ]; then
                stat=$(cat /proc/${pid}/stat 2>/dev/null)
                # 解析stat文件: pid (comm) state ppid
                tid=$(echo "$stat" | awk "{print \$1}")
                comm=$(echo "$stat" | sed "s/.*(\([^)]*\)).*/\1/" | awk "{print \$1}")
                state=$(echo "$stat" | awk "{print \$3}")
                ppid=$(echo "$stat" | awk "{print \$4}")
                # 映射状态码
                case "$state" in
                    R) stat_str="R" ;;
                    S) stat_str="S" ;;
                    D) stat_str="D" ;;
                    Z) stat_str="Z" ;;
                    T) stat_str="T" ;;
                    t) stat_str="t" ;;
                    X) stat_str="X" ;;
                    x) stat_str="x" ;;
                    K) stat_str="K" ;;
                    W) stat_str="W" ;;
                    P) stat_str="P" ;;
                    *) stat_str="?" ;;
                esac
                printf "%-6d %-5d %-6d %-7s %s\n" "$tid" "$ppid" "0" "$stat_str" "$comm"
            fi
            # 获取所有线程信息
            if [ -d "/proc/${pid}/task" ]; then
                for tgid in $(ls -1 /proc/${pid}/task/ 2>/dev/null); do
                    # 跳过主线程（已在上面处理）
                    if [ "$tgid" != "$pid" ]; then
                        if [ -f "/proc/${pid}/task/${tgid}/stat" ]; then
                            tstat=$(cat /proc/${pid}/task/${tgid}/stat 2>/dev/null)
                            ttid=$(echo "$tstat" | awk "{print \$1}")
                            tcomm=$(echo "$tstat" | sed "s/.*(\([^)]*\)).*/\1/" | awk "{print \$1}")
                            tstate=$(echo "$tstat" | awk "{print \$3}")
                            tppid=$(echo "$tstat" | awk "{print \$4}")
                            # 映射状态码
                            case "$tstate" in
                                R) tstat_str="R" ;;
                                S) tstat_str="S" ;;
                                D) tstat_str="D" ;;
                                Z) tstat_str="Z" ;;
                                T) tstat_str="T" ;;
                                t) tstat_str="t" ;;
                                X) tstat_str="X" ;;
                                x) tstat_str="x" ;;
                                K) tstat_str="K" ;;
                                W) tstat_str="W" ;;
                                P) tstat_str="P" ;;
                                *) tstat_str="?" ;;
                            esac
                            printf "%-6d %-5d %-6d %-7s %s\n" "$ttid" "$tppid" "0" "$tstat_str" "$tcomm"
                        fi
                    fi
                done
            fi
            # 统计线程数
            thread_count=$(ls -1 /proc/${pid}/task/ 2>/dev/null | wc -l)
            echo ""
            echo "Total threads: $thread_count"
        ' > "${OUTPUT_DIR}/app_threads.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/app_threads.txt"
        
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
# 优化：每次采样只执行一条 SSH 命令，提高效率和可靠性
# 支持计算采样期间的 IO 差值而非累计值
#-------------------------------------------------------------------------------
collect_performance_samples() {
    log_info "开始周期性采样 CPU 和内存数据..."
    log_info "采样参数: 持续时间=${DURATION}s, 间隔=${INTERVAL}s"
    
    # 从 app_pid.txt 读取 PID
    local app_pid_file="${OUTPUT_DIR}/app_pid.txt"
    local APP_PID=""
    
    if [ -f "$app_pid_file" ]; then
        APP_PID=$(cat "$app_pid_file" | tr -cd '[:digit:]' | tr -d '\r\n')
    fi
    
    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ] || [ "$APP_PID" = "" ]; then
        log_warning "未找到目标进程PID，跳过采样"
        echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/perf_samples.csv"
        echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/io_samples.csv"
        echo "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "${OUTPUT_DIR}/perf_samples.csv"
        return
    fi
    
    log_info "目标进程PID: ${APP_PID}"
    
    # 验证进程是否存在
    local proc_exists=$(ssh_cmd "test -d /proc/${APP_PID} && echo 'OK'" 2>&1 | tr -d '\r\n ')
    if [ "$proc_exists" != "OK" ]; then
        log_warning "进程 ${APP_PID} 不存在"
        echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/perf_samples.csv"
        echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/io_samples.csv"
        echo "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "${OUTPUT_DIR}/perf_samples.csv"
        return
    fi
    
    # 计算采样次数
    local sample_count=$((DURATION / INTERVAL))
    [ "$sample_count" -lt 1 ] && sample_count=1
    
    # 创建CSV文件 - 包含IO差值列
    echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/perf_samples.csv"
    echo "时间(s),CPU%,RSS(MB),VSZ(MB),读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值" > "${OUTPUT_DIR}/io_samples.csv"

    local elapsed=0
    local iteration=0
    
    # IO字节差值追踪
    local prev_read_bytes=0
    local prev_write_bytes=0
    local prev_time=0
    
    # IO系统调用差值追踪
    local prev_syscr=0
    local prev_syscw=0
    local prev_syscr_time=0
    
    # 初始采样：获取基线数据
    local baseline_io=$(ssh_cmd "cat /proc/${APP_PID}/io 2>/dev/null" 2>&1)
    if [ -n "$baseline_io" ]; then
        prev_read_bytes=$(echo "$baseline_io" | grep "^read_bytes:" | awk '{print $2}' | head -1)
        prev_write_bytes=$(echo "$baseline_io" | grep "^write_bytes:" | awk '{print $2}' | head -1)
        prev_syscr=$(echo "$baseline_io" | grep "^syscr:" | awk '{print $2}' | head -1)
        prev_syscw=$(echo "$baseline_io" | grep "^syscw:" | awk '{print $2}' | head -1)
        prev_time=0
        prev_syscr_time=0
    fi
    
    # 确保初始值为数字
    prev_read_bytes=${prev_read_bytes:-0}
    prev_write_bytes=${prev_write_bytes:-0}
    prev_syscr=${prev_syscr:-0}
    prev_syscw=${prev_syscw:-0}

    while [ "$elapsed" -lt "$DURATION" ]; do
        iteration=$((iteration + 1))
        local current_time=$((iteration * INTERVAL))

        # 使用 top 获取 CPU% 和内存信息 (与 collect_app_info 一致)
        local top_line=$(ssh_cmd "top -b -n 1 | grep -E '^[[:space:]]*${APP_PID}'" 2>&1)
        local mem_info=$(ssh_cmd "cat /proc/${APP_PID}/status | grep -E 'VmRSS:|VmSize:'" 2>&1)
        # 获取完整的/proc/{pid}/io信息
        local io_info=$(ssh_cmd "cat /proc/${APP_PID}/io 2>/dev/null" 2>&1)

        # 解析 top 输出: PID USER PR NI %CPU %MEM TIME+  COMMAND
        local cpu_val=$(echo "$top_line" | awk '{print $8}' | tr -d ' \r\n')
        local rss_kb=$(echo "$mem_info" | grep "VmRSS:" | awk '{print $2}')
        local vsz_kb=$(echo "$mem_info" | grep "VmSize:" | awk '{print $2}')

        # 解析IO数据 - 使用 ^ 匹配行首避免匹配 cancelled_write_bytes
        local read_bytes=$(echo "$io_info" | grep "^read_bytes:" | awk '{print $2}' | head -1)
        local write_bytes=$(echo "$io_info" | grep "^write_bytes:" | awk '{print $2}' | head -1)
        local rchar=$(echo "$io_info" | grep "^rchar:" | awk '{print $2}' | head -1)
        local wchar=$(echo "$io_info" | grep "^wchar:" | awk '{print $2}' | head -1)
        local syscr=$(echo "$io_info" | grep "^syscr:" | awk '{print $2}' | head -1)
        local syscw=$(echo "$io_info" | grep "^syscw:" | awk '{print $2}' | head -1)

        # 确保值为数字
        read_bytes=${read_bytes:-0}
        write_bytes=${write_bytes:-0}
        syscr=${syscr:-0}
        syscw=${syscw:-0}

        # 计算IO字节速率 (KB/s)
        local read_rate="0"
        local write_rate="0"
        local time_diff=$((current_time - prev_time))
        
        if [ -n "$read_bytes" ] && [ -n "$write_bytes" ] && [ -n "$time_diff" ] && [ "$time_diff" -gt 0 ]; then
            # 确保是有效数字
            if [[ "$read_bytes" =~ ^[0-9]+$ ]] && [[ "$write_bytes" =~ ^[0-9]+$ ]] && [[ "$prev_read_bytes" =~ ^[0-9]+$ ]] && [[ "$prev_write_bytes" =~ ^[0-9]+$ ]]; then
                local read_diff=$((read_bytes - prev_read_bytes))
                local write_diff=$((write_bytes - prev_write_bytes))
                
                # 处理可能的负值（进程重启或数据异常）
                [ "$read_diff" -lt 0 ] && read_diff=0
                [ "$write_diff" -lt 0 ] && write_diff=0
                
                # 计算速率
                read_rate=$(echo "scale=2; $read_diff / 1024 / $time_diff" | bc 2>/dev/null || echo "0")
                write_rate=$(echo "scale=2; $write_diff / 1024 / $time_diff" | bc 2>/dev/null || echo "0")
                
                prev_read_bytes=$read_bytes
                prev_write_bytes=$write_bytes
                prev_time=$current_time
            fi
        fi
        
        # 计算IO系统调用差值 (次)
        local syscr_diff=0
        local syscw_diff=0
        local syscr_time_diff=$((current_time - prev_syscr_time))
        
        if [ -n "$syscr" ] && [ -n "$syscw" ] && [ -n "$syscr_time_diff" ] && [ "$syscr_time_diff" -gt 0 ]; then
            # 确保是有效数字
            if [[ "$syscr" =~ ^[0-9]+$ ]] && [[ "$syscw" =~ ^[0-9]+$ ]] && [[ "$prev_syscr" =~ ^[0-9]+$ ]] && [[ "$prev_syscw" =~ ^[0-9]+$ ]]; then
                syscr_diff=$((syscr - prev_syscr))
                syscw_diff=$((syscw - prev_syscw))
                
                # 处理可能的负值
                [ "$syscr_diff" -lt 0 ] && syscr_diff=0
                [ "$syscw_diff" -lt 0 ] && syscw_diff=0
                
                prev_syscr=$syscr
                prev_syscw=$syscw
                prev_syscr_time=$current_time
            fi
        fi

        # 格式化累计IO值（转换为MB）
        local read_mb=$(echo "scale=2; ${read_bytes:-0} / 1024 / 1024" | bc 2>/dev/null || echo "0")
        local write_mb=$(echo "scale=2; ${write_bytes:-0} / 1024 / 1024" | bc 2>/dev/null || echo "0")

        # 验证数据有效性
        if [ -n "$rss_kb" ] && [ -n "$vsz_kb" ]; then
            local rss_mb=$(echo "scale=1; ${rss_kb:-0} / 1024" | bc 2>/dev/null || echo "${rss_kb}" | awk '{printf "%.1f", $1/1024}')
            local vsz_mb=$(echo "scale=1; ${vsz_kb:-0} / 1024" | bc 2>/dev/null || echo "${vsz_kb}" | awk '{printf "%.1f", $1/1024}')
            local cpu_pct="${cpu_val:-0}"

            # 写入 perf_samples.csv (简化版)
            echo "${current_time},${cpu_pct},${rss_mb},${vsz_mb},${read_rate},${write_rate}" >> "${OUTPUT_DIR}/perf_samples.csv"
            
            # 写入 io_samples.csv (包含IO系统调用差值)
            # 格式: 时间,CPU%,RSS,VSZ,读IO(KB/s),写IO(KB/s),读字节累计,写字节累计,读调用差值,写调用差值
            echo "${current_time},${cpu_pct},${rss_mb},${vsz_mb},${read_rate},${write_rate},${read_mb},${write_mb},${syscr_diff},${syscw_diff}" >> "${OUTPUT_DIR}/io_samples.csv"
            
            log_info "采样 ${iteration}/${sample_count}: CPU=${cpu_pct}%, RSS=${rss_mb}MB, IO读=${read_rate}KB/s, IO写=${write_rate}KB/s"
        else
            echo "${current_time},N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "${OUTPUT_DIR}/perf_samples.csv"
            echo "${current_time},N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "${OUTPUT_DIR}/io_samples.csv"
            log_warning "第${iteration}次采样数据无效"
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

    # 系统负载 - 使用 /proc 文件替代 vmstat
    ssh_cmd 'uptime' > "${OUTPUT_DIR}/uptime.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/uptime.txt"

    # 从 /proc/stat 和 /proc/meminfo 生成类似 vmstat 的输出
    # 正确解析各列：r b swpd free buff cache si so bi bo in cs us sy id wa st
    ssh_cmd '
        # 获取 CPU 时间和上下文切换信息
        cpu_line=$(cat /proc/stat | head -1)
        ct_line=$(cat /proc/stat | grep ctxt | head -1)
        
        # 解析 CPU 时间各字段 (user nice system idle iowait irq softirq steal guest guest_nice)
        cpu_user=$(echo "$cpu_line" | awk "{print \$2}")
        cpu_nice=$(echo "$cpu_line" | awk "{print \$3}")
        cpu_system=$(echo "$cpu_line" | awk "{print \$4}")
        cpu_idle=$(echo "$cpu_line" | awk "{print \$5}")
        cpu_iowait=$(echo "$cpu_line" | awk "{print \$6}")
        cpu_irq=$(echo "$cpu_line" | awk "{print \$7}")
        cpu_softirq=$(echo "$cpu_line" | awk "{print \$8}")
        
        # 计算总 CPU 时间和 I/O 等待百分比
        cpu_total=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
        [ $cpu_total -eq 0 ] && cpu_total=1
        
        # I/O 等待是 iowait 占总 CPU 时间的百分比
        io_wait=$(echo "scale=1; $cpu_iowait * 100 / $cpu_total" | bc 2>/dev/null || echo "0")
        
        # 计算用户/系统 CPU 百分比
        cpu_usr_pct=$(echo "scale=1; ($cpu_user + $cpu_nice) * 100 / $cpu_total" | bc 2>/dev/null || echo "0")
        cpu_sys_pct=$(echo "scale=1; $cpu_system * 100 / $cpu_total" | bc 2>/dev/null || echo "0")
        cpu_idle_pct=$(echo "scale=1; $cpu_idle * 100 / $cpu_total" | bc 2>/dev/null || echo "0")

        # 获取内存信息
        mem_total=$(grep MemTotal: /proc/meminfo | awk "{print \$2}")
        mem_free=$(grep MemFree: /proc/meminfo | awk "{print \$2}")
        mem_available=$(grep MemAvailable: /proc/meminfo | awk "{print \$2}")
        buffers=$(grep Buffers: /proc/meminfo | awk "{print \$2}")
        cached=$(grep Cached: /proc/meminfo | grep -v SwapCached | awk "{print \$2}")
        if [ -z "$cached" ]; then
            cached=0
        fi
        swap_cached=$(grep SwapCached: /proc/meminfo | awk "{print \$2}")
        [ -z "$swap_cached" ] && swap_cached=0
        swap_total=$(grep SwapTotal: /proc/meminfo | awk "{print \$2}")
        [ -z "$swap_total" ] && swap_total=0
        swap_free=$(grep SwapFree: /proc/meminfo | awk "{print \$2}")
        [ -z "$swap_free" ] && swap_free=0

        # 计算已用 swap
        swap_used=$((swap_total - swap_free))
        
        # 计算已用内存 (近似值)
        used_mem=$((mem_total - mem_free - buffers - cached))
        [ $used_mem -lt 0 ] && used_mem=0
        
        # 进程信息 - 运行中和阻塞的进程
        procs_r=$(cat /proc/stat | grep "^procs_running" | awk "{print \$2}")
        procs_b=$(cat /proc/stat | grep "^procs_blocked" | awk "{print \$2}")
        [ -z "$procs_r" ] && procs_r=0
        [ -z "$procs_b" ] && procs_b=0
        
        # 上下文切换和中断
        ctxt=$(grep ctxt /proc/stat | awk "{print \$2}")
        intr=$(grep intr /proc/stat | awk "{print \$2}")
        [ -z "$ctxt" ] && ctxt=0
        [ -z "$intr" ] && intr=0

        # 输出格式类似 vmstat: procs r b swpd free buff cache si so bi bo in cs us sy id wa st
        # 注意：wa列必须输出有效的0-100百分比值
        printf "procs r  b    swpd   free   buff  cache   si   so    bi    bo   in    cs  us  sy  id  wa  st\n"
        printf "%5d %-3d %-6d %6d %5d %6d    0    0    0     0 %5d %5d %3d %3d %3d %3d   0\n" \
            "$procs_r" "$procs_b" "$swap_used" "$mem_free" "$buffers" "$cached" "$intr" "$ctxt" \
            "${cpu_usr_pct%.*}" "${cpu_sys_pct%.*}" "${cpu_idle_pct%.*}" "${io_wait%.*}"
    ' > "${OUTPUT_DIR}/vmstat.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/vmstat.txt"

    # top输出
    ssh_cmd 'top -b -n 1' > "${OUTPUT_DIR}/top.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/top.txt"

    # mpstat - 使用 /proc/stat 替代
    ssh_cmd '
        echo "Linux kernel driver."
        echo ""
        echo "Average:      CPU   %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle"
        cpu_line=$(cat /proc/stat | head -1)
        total=$(echo "$cpu_line" | awk "{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}")
        idle=$(echo "$cpu_line" | awk "{print \$5}")
        iowait=$(echo "$cpu_line" | awk "{print \$6}")
        system=$(echo "$cpu_line" | awk "{print \$4}")
        user=$(echo "$cpu_line" | awk "{print \$2}")
        irq=$(echo "$cpu_line" | awk "{print \$7}")
        soft=$(echo "$cpu_line" | awk "{print \$8}")

        [ $total -eq 0 ] && total=1
        usr_pct=$(echo "scale=1; $user * 100 / $total" | bc 2>/dev/null || echo "0")
        sys_pct=$(echo "scale=1; $system * 100 / $total" | bc 2>/dev/null || echo "0")
        iowait_pct=$(echo "scale=1; $iowait * 100 / $total" | bc 2>/dev/null || echo "0")
        irq_pct=$(echo "scale=1; $irq * 100 / $total" | bc 2>/dev/null || echo "0")
        soft_pct=$(echo "scale=1; $soft * 100 / $total" | bc 2>/dev/null || echo "0")
        idle_pct=$(echo "scale=1; $idle * 100 / $total" | bc 2>/dev/null || echo "0")

        echo "Average:    all  $usr_pct    0.00  $sys_pct   $iowait_pct   $irq_pct  $soft_pct    0.00    0.00    0.00 $idle_pct"
    ' > "${OUTPUT_DIR}/mpstat.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/mpstat.txt"

    log_success "系统负载信息采集完成"
}


#-------------------------------------------------------------------------------
# 采集火焰图数据 (使用perf + FlameGraph)
# 流程：远程采集perf.data -> 拷贝到本地 -> 本地生成火焰图
#-------------------------------------------------------------------------------
collect_flamegraph_data() {
    log_info "采集火焰图数据..."


    # 检查本地FlameGraph工具
    local local_flamegraph="${PROJECT_DIR}/FlameGraph"
    if [ ! -f "${local_flamegraph}/flamegraph.pl" ]; then
        log_warning "本地FlameGraph工具不存在: ${local_flamegraph}"
        echo "本地FlameGraph工具不存在" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    if [ ! -f "${local_flamegraph}/stackcollapse-perf.pl" ]; then
        log_warning "本地stackcollapse-perf.pl不存在"
        echo "本地stackcollapse-perf.pl不存在" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ] || [ "$APP_PID" = "" ]; then
        log_warning "未找到目标进程PID，跳过火焰图采集"
        echo "N/A" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    # 检查远程perf是否可用
    local perf_available=$(ssh_cmd "which perf 2>/dev/null || echo 'not_found'" | tr -d '\r\n')
    if [ "$perf_available" = "not_found" ]; then
        log_warning "远程perf工具不可用，跳过火焰图采集"
        echo "远程perf不可用" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    log_info "使用perf record采集PID=${APP_PID}的调用栈..."

    # 清理远程旧数据
    ssh_cmd "rm -f /tmp/perf.data /tmp/perf.svg /tmp/perf.log"

    # 使用perf record采集数据（系统级采集，带调用栈）
    # 使用nohup确保命令在远程后台运行
    ssh_cmd "rm -f /tmp/perf.data && nohup sh -c 'perf record -F 99 -p ${APP_PID} -a -g -o /tmp/perf.data -- sleep ${DURATION}' > /tmp/perf.log 2>&1 &"
    log_info "perf record正在后台运行..."

    # 等待采集完成
    sleep $((DURATION + 2))

    # 检查perf.data文件是否存在
    local perf_data_exists=$(ssh_cmd "test -f /tmp/perf.data && echo 'yes' || echo 'no'" | tr -d '\r\n')
    if [ "$perf_data_exists" != "yes" ]; then
        log_warning "perf record未能生成数据文件"
        echo "采集失败" > "${OUTPUT_DIR}/perf_report.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    # 获取perf.data大小
    local perf_size=$(ssh_cmd "ls -la /tmp/perf.data 2>/dev/null | awk '{print \$5}'" | tr -d '\r\n')
    log_info "perf.data 大小: ${perf_size} bytes"

    # 拷贝perf.data到本地
    log_info "拷贝perf.data到本地..."
    local perf_data_local="${OUTPUT_DIR}/perf.data"
    scp_copy "/tmp/perf.data" "$perf_data_local"
    local local_size=$(wc -c < "$perf_data_local" 2>/dev/null || echo "0")

    if [ -z "$local_size" ] || [ "$local_size" -lt 1000 ]; then
        log_warning "perf.data拷贝失败或文件过小"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    log_info "本地perf.data大小: ${local_size} bytes"

    # 清理远程perf.data
    #ssh_cmd "rm -f /tmp/perf.data"

    ssh_cmd "cat /proc/kallsyms > /tmp/kallsyms"
    local perf_kernel_sym="${OUTPUT_DIR}/kallsyms"
    scp_copy "/tmp/kallsyms" "$perf_kernel_sym"

    # 检查本地perf工具
    if command -v perf &> /dev/null; then
        local perf_cmd="perf"
    elif [ -f "/usr/bin/perf" ]; then
        local perf_cmd="/usr/bin/perf"
    else
        log_warning "本地perf工具不可用，无法生成火焰图"
        echo "perf工具不可用" > "${OUTPUT_DIR}/perf_record.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        return
    fi

    # 生成perf报告的辅助函数
    generate_perf_report() {
        local perf_data_path="$1"
        local output_file="$2"
        local use_callgraph="${3:-1}"
        
        if [ "$use_callgraph" = "1" ]; then
            # 使用调用链模式
            sudo $perf_cmd report -i "$perf_data_path" -g --stdio -n 20 2>&1 | head -150 > "$output_file"
        else
            # 不使用调用链
            sudo $perf_cmd report -i "$perf_data_path" --stdio -g none 2>&1 | head -80 > "$output_file"
        fi
    }

    # 生成热点函数调用栈详情的函数
    # 从 perf report 中提取热点函数及其调用栈，生成结构化文本文件
    generate_hot_functions_stacks() {
        local perf_data_path="$1"
        local output_file="$2"
        
        log_info "生成热点函数调用栈详情..."
        
        # 创建输出文件
        : > "$output_file"
        
        # 检查是否有调用链数据
        local has_callgraph
        has_callgraph=$(sudo $perf_cmd report -i "$perf_data_path" -g --stdio 2>&1 | grep -c "callchain" || echo "0")
        
        if [ "$has_callgraph" = "0" ]; then
            log_warning "perf.data没有调用链数据，跳过热点函数调用栈生成"
            echo "# === 热点函数调用栈 ===" >> "$output_file"
            echo "# 状态: 无调用链数据" >> "$output_file"
            echo "# 说明: perf.data采集时未使用 -g 参数，没有调用栈信息" >> "$output_file"
            echo "# " >> "$output_file"
            echo "# 解决方案: 重新采集perf数据，使用 -g 参数" >> "$output_file"
            echo "#   perf record -F 99 -p <PID> -a -g -o /tmp/perf.data -- sleep 10" >> "$output_file"
            return
        fi
        
        # 获取热点函数列表和调用栈
        local perf_output
        perf_output=$(sudo $perf_cmd report -i "$perf_data_path" -g --stdio 2>&1) || true
        
        if [ -z "$perf_output" ]; then
            log_warning "无法获取perf报告数据"
            echo "# === 热点函数调用栈 ===" >> "$output_file"
            echo "# 状态: 无法获取数据" >> "$output_file"
            return
        fi
        
        echo "# === 热点函数调用栈 ===" >> "$output_file"
        echo "# 状态: 成功" >> "$output_file"
        echo "#" >> "$output_file"
        
        # 解析perf报告，提取热点函数及其调用栈
        local current_func=""
        local current_pct=""
        local in_stack=0
        
        echo "$perf_output" | while IFS= read -r line; do
            # 跳过空行和注释
            [ -z "$line" ] && continue
            [[ "$line" =~ ^# ]] && continue
            
            # 检测新的热点函数行
            if [[ "$line" =~ ^[[:space:]]*([0-9]+\.?[0-9]*)%[[:space:]]+[0-9]+\.?[0-9]*%[[:space:]]+([^[:space:]]+)[[:space:]]+([^\[:space:]]+) ]]; then
                # 保存前一个函数
                [ -n "$current_func" ] && echo "" >> "$output_file"
                
                current_pct="${BASH_REMATCH[1]}"
                local module="${BASH_REMATCH[3]}"
                
                # 提取地址
                local addr_val=""
                if [[ "$line" =~ \[.\][[:space:]]+(0x[0-9a-f]+) ]]; then
                    addr_val="${BASH_REMATCH[1]}"
                    current_func="$addr_val"
                elif [[ "$line" =~ \[k\][[:space:]]+(0x[0-9a-f]+) ]]; then
                    addr_val="${BASH_REMATCH[1]}"
                    current_func="[k]$addr_val"
                else
                    current_func="$module"
                fi
                
                # 输出函数信息
                echo "FUNC: $current_func PCT: $current_pct%" >> "$output_file"
                in_stack=1
            # 检测调用栈中的函数调用
            elif [ "$in_stack" = "1" ] && [[ "$line" =~ ^[[:space:]]+\|+ ]]; then
                # 提取调用栈中的地址
                if [[ "$line" =~ 0x([0-9a-f]+) ]]; then
                    local addr="${BASH_REMATCH[1]}"
                    # 计算缩进深度
                    local indent=${#line}
                    indent=${indent%%[^|]*}  # 移除非管道字符前的部分
                    local depth=${#indent}
                    depth=$((depth / 2))
                    
                    # 判断是内核还是用户地址
                    if [[ "$addr" =~ ^ffff ]]; then
                        echo "  STACK[$depth]: kernel:0x${addr: -8}" >> "$output_file"
                    else
                        echo "  STACK[$depth]: app:0x${addr: -8}" >> "$output_file"
                    fi
                fi
            # 检测新的热点函数（缩进减少）
            elif [ "$in_stack" = "1" ] && [[ "$line" =~ ^[[:space:]]*[^|] ]]; then
                if [[ "$line" =~ ^[0-9] ]]; then
                    in_stack=0
                fi
            fi
        done
        
        log_success "热点函数调用栈详情已生成"
    }

    # 检查perf.data是否有调用链数据
    log_info "检查perf.data调用链数据..."
    local perf_check_output
    perf_check_output=$(sudo $perf_cmd report -i "$perf_data_local" -g --stdio 2>&1 | head -10) || true
    
    if echo "$perf_check_output" | grep -qi "no callchain\|no branch\|no data"; then
        log_warning "perf.data没有调用链数据，将使用非调用栈模式生成报告"
        HAS_CALLCHAIN=0
    elif echo "$perf_check_output" | grep -qi "password\|permission denied\|requires"; then
        log_warning "sudo权限不足，跳过perf报告生成"
        HAS_CALLCHAIN=2  # 特殊标记：sudo不可用
    else
        HAS_CALLCHAIN=1
    fi

    # 生成perf report（热点函数列表）
    log_info "生成perf报告..."
    
    ssh_cmd "perf report --stdio -g none -i /tmp/perf.data 2>/dev/null" > "${OUTPUT_DIR}/perf_report.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/perf_report.txt"
    
    # 检查生成的报告
    local report_size=$(wc -c < "${OUTPUT_DIR}/perf_report.txt" 2>/dev/null || echo "0")
    if [ -z "$report_size" ] || [ "$report_size" -lt 100 ]; then
        log_warning "perf报告生成失败，生成占位符..."
        echo "# === perf报告生成失败 ===" > "${OUTPUT_DIR}/perf_report.txt"
        echo "# " >> "${OUTPUT_DIR}/perf_report.txt"
        echo "# perf.data 信息：" >> "${OUTPUT_DIR}/perf_report.txt"
        sudo $perf_cmd report -i "$perf_data_local" --header-only 2>&1 | head -20 >> "${OUTPUT_DIR}/perf_report.txt" || true
    fi
    
    # 生成调用栈数据（用于热点函数调用栈详情）
    log_info "生成调用栈数据..."
    if [ "$HAS_CALLCHAIN" = "1" ]; then
        # 只有有调用链数据时才生成
        if $perf_cmd script -i "$perf_data_local" 2>/dev/null > "${OUTPUT_DIR}/stack_counts.txt"; then
            local stack_size=$(wc -c < "${OUTPUT_DIR}/stack_counts.txt" 2>/dev/null || echo "0")
            if [ -n "$stack_size" ] && [ "$stack_size" -gt 100 ]; then
                log_success "调用栈数据已生成，大小: ${stack_size} bytes"
            else
                log_warning "调用栈数据文件过小"
                echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
            fi
        else
            # 尝试使用 sudo
            if sudo $perf_cmd script -i "$perf_data_local" 2>/dev/null > "${OUTPUT_DIR}/stack_counts.txt"; then
                local stack_size=$(wc -c < "${OUTPUT_DIR}/stack_counts.txt" 2>/dev/null || echo "0")
                if [ -n "$stack_size" ] && [ "$stack_size" -gt 100 ]; then
                    log_success "调用栈数据已生成(sudo模式)，大小: ${stack_size} bytes"
                else
                    log_warning "调用栈数据文件过小"
                    echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
                fi
            else
                log_warning "调用栈数据生成失败"
                echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
            fi
        fi
        
        # 生成带调用栈的 perf report（用于热点函数调用链详情）
        log_info "生成带调用栈的perf报告..."
        if $perf_cmd report -i "$perf_data_local" --stdio -g 2>/dev/null > "${OUTPUT_DIR}/perf_report_with_stack.txt"; then
            local report_stack_size=$(wc -c < "${OUTPUT_DIR}/perf_report_with_stack.txt" 2>/dev/null || echo "0")
            if [ -n "$report_stack_size" ] && [ "$report_stack_size" -gt 100 ]; then
                log_success "带调用栈的perf报告已生成，大小: ${report_stack_size} bytes"
            else
                log_warning "带调用栈的perf报告文件过小"
                echo "N/A" > "${OUTPUT_DIR}/perf_report_with_stack.txt"
            fi
        else
            # 尝试使用 sudo
            if sudo $perf_cmd report -i "$perf_data_local" --stdio -g 2>/dev/null > "${OUTPUT_DIR}/perf_report_with_stack.txt"; then
                local report_stack_size=$(wc -c < "${OUTPUT_DIR}/perf_report_with_stack.txt" 2>/dev/null || echo "0")
                if [ -n "$report_stack_size" ] && [ "$report_stack_size" -gt 100 ]; then
                    log_success "带调用栈的perf报告已生成(sudo模式)，大小: ${report_stack_size} bytes"
                else
                    log_warning "带调用栈的perf报告文件过小"
                    echo "N/A" > "${OUTPUT_DIR}/perf_report_with_stack.txt"
                fi
            else
                log_warning "带调用栈的perf报告生成失败"
                echo "N/A" > "${OUTPUT_DIR}/perf_report_with_stack.txt"
            fi
        fi
    else
        # 无调用链数据时，创建空的占位符
        echo "N/A" > "${OUTPUT_DIR}/stack_counts.txt"
        echo "N/A" > "${OUTPUT_DIR}/perf_report_with_stack.txt"
        log_info "跳过调用栈数据生成（perf.data无调用链）"
    fi

    # 生成热点函数调用栈详情（新的结构化格式）
    generate_hot_functions_stacks "$perf_data_local" "${OUTPUT_DIR}/hot_functions_stacks.txt"

    # 生成火焰图 SVG
    log_info "生成火焰图..."

    # 生成火焰图
    if $perf_cmd script -i "$perf_data_local" --kallsyms="$perf_kernel_sym" 2>/dev/null | "${local_flamegraph}/stackcollapse-perf.pl" 2>/dev/null | "${local_flamegraph}/flamegraph.pl" --bgcolor='#1e1e2e' > "${OUTPUT_DIR}/perf_flamegraph.svg" 2>&1; then
        local svg_size=$(wc -c < "${OUTPUT_DIR}/perf_flamegraph.svg" 2>/dev/null || echo "0")
        if [ -n "$svg_size" ] && [ "$svg_size" -gt 1000 ]; then
            log_success "火焰图已生成，大小: ${svg_size} bytes"
        else
            log_warning "火焰图文件过小，可能生成失败"
            echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        fi
    else
        log_warning "火焰图生成失败，尝试使用sudo..."
        # 尝试使用sudo
        if sudo $perf_cmd script -i "$perf_data_local" 2>/dev/null | "${local_flamegraph}/stackcollapse-perf.pl" 2>/dev/null | "${local_flamegraph}/flamegraph.pl" --bgcolor='#1e1e2e' > "${OUTPUT_DIR}/perf_flamegraph.svg" 2>&1; then
            local svg_size=$(wc -c < "${OUTPUT_DIR}/perf_flamegraph.svg" 2>/dev/null || echo "0")
            if [ -n "$svg_size" ] && [ "$svg_size" -gt 1000 ]; then
                log_success "火焰图已生成(sudo模式)，大小: ${svg_size} bytes"
            else
                log_warning "火焰图文件过小"
                echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
            fi
        else
            log_warning "火焰图生成失败"
            echo "N/A" > "${OUTPUT_DIR}/perf_flamegraph.svg"
        fi
    fi

    log_success "火焰图数据采集完成"
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
# 采集锁分析数据 (使用 perf lock)
#-------------------------------------------------------------------------------
collect_lock_analysis() {
    log_info "采集锁分析数据..."

    if [ -z "$APP_PID" ] || [ "$APP_PID" = "N/A" ] || [ "$APP_PID" = "" ]; then
        log_warning "未找到目标进程PID，跳过锁分析"
        echo "N/A" > "${OUTPUT_DIR}/perf_lock.txt"
        echo "N/A" > "${OUTPUT_DIR}/lock_contention.txt"
        return
    fi

    # 检查远程perf是否可用
    local perf_available=$(ssh_cmd "which perf 2>/dev/null || echo 'not_found'" | tr -d '\r\n')
    if [ "$perf_available" = "not_found" ]; then
        log_warning "远程perf工具不可用，跳过锁分析"
        echo "perf工具不可用" > "${OUTPUT_DIR}/perf_lock.txt"
        echo "perf工具不可用" > "${OUTPUT_DIR}/lock_contention.txt"
        return
    fi

    # 检查perf lock命令是否支持
    local perf_lock_support=$(ssh_cmd "perf lock --help 2>/dev/null | head -5 || echo 'not_supported'" | tr -d '\r\n')
    if [[ "$perf_lock_support" == *"not_supported"* ]] || [[ "$perf_lock_support" == *"unknown option"* ]]; then
        log_warning "perf lock子命令不可用，跳过锁分析"
        echo "perf lock子命令不可用" > "${OUTPUT_DIR}/perf_lock.txt"
        echo "perf lock子命令不可用" > "${OUTPUT_DIR}/lock_contention.txt"
        return
    fi

    log_info "使用perf lock record采集PID=${APP_PID}的锁争用信息..."

    # 清理远程旧数据
    ssh_cmd "rm -f /tmp/perf.data /tmp/perf.lock"

    # 使用perf lock record采集数据
    # -a: 整个系统
    # -g: 记录调用栈
    ssh_cmd "rm -f /tmp/perf.data && nohup sh -c 'perf lock record -a -g -o /tmp/perf.data -- sleep ${DURATION}' > /tmp/perf_lock.log 2>&1 &"
    log_info "perf lock record正在后台运行..."

    # 等待采集完成
    sleep $((DURATION + 2))

    # 检查是否采集成功
    local perf_lock_exists=$(ssh_cmd "test -f /tmp/perf.data && echo 'yes' || echo 'no'" | tr -d '\r\n')
    if [ "$perf_lock_exists" != "yes" ]; then
        log_warning "perf lock record未能生成数据文件"
        echo "采集失败" > "${OUTPUT_DIR}/perf_lock.txt"
        echo "采集失败" > "${OUTPUT_DIR}/lock_contention.txt"
        return
    fi

    # 生成锁分析报告
    log_info "生成锁分析报告..."
    
    # perf lock report - 显示锁争用统计
    ssh_cmd "perf lock report -i /tmp/perf.data 2>/dev/null" > "${OUTPUT_DIR}/perf_lock.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/perf_lock.txt"
    
    # perf lock contention - 显示锁争用情况
    ssh_cmd "perf lock contention -i /tmp/perf.data 2>/dev/null | head -100" > "${OUTPUT_DIR}/lock_contention.txt" 2>/dev/null || echo "N/A" > "${OUTPUT_DIR}/lock_contention.txt"

    # 获取锁统计摘要
    local lock_summary=$(ssh_cmd "perf lock stat -i /tmp/perf.data 2>/dev/null | head -50" 2>/dev/null || echo "N/A")
    if [ -n "$lock_summary" ] && [ "$lock_summary" != "N/A" ]; then
        echo "$lock_summary" >> "${OUTPUT_DIR}/perf_lock.txt"
        echo "" >> "${OUTPUT_DIR}/perf_lock.txt"
        echo "=== Lock Contention Summary ===" >> "${OUTPUT_DIR}/perf_lock.txt"
        cat "${OUTPUT_DIR}/lock_contention.txt" >> "${OUTPUT_DIR}/perf_lock.txt"
    fi

    log_success "锁分析数据采集完成"
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

# 添加所有txt、csv和svg文件内容
for filename in os.listdir(output_dir):
    if filename.endswith('.txt') or filename.endswith('.csv') or filename.endswith('.svg'):
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                if filename.endswith('.svg'):
                    data['files'][filename] = content  # SVG文件不做截断
                else:
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

    check_dependencies
    load_config
    setup_output
    test_connection

    log_info "开始采集性能数据..."

    collect_system_info
    collect_memory_info

    if [ "$DISPLAY_SERVER" = "wayland" ]; then
        collect_wayland_info
    else
        collect_drm_info
    fi

    collect_app_info
    collect_flamegraph_data
    collect_lock_analysis
    collect_system_load

    # 周期性采样 CPU 和内存（用于折线图）
    collect_performance_samples

    # 图形API追踪
    collect_graphics_traces

    generate_json_summary

    log_info "采集的数据保存在: ${OUTPUT_DIR}"
}

# 执行主函数
main
