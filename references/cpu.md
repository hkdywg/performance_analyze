# CPU 分析

## 系统级检查

从整体 CPU 压力和调度器信号开始：

```bash
top -b -n 1
mpstat -P ALL 1 3
vmstat 1 5
pidstat -u -t 1 3
sar -u 1 3
```

关注点：

- `%us`：用户态 CPU 压力
- `%sy`：内核态 CPU 压力
- `%wa`：等待 I/O，通常不是纯 CPU 瓶颈
- `%hi` 和 `%si`：硬件/软件中断压力
- 运行队列、负载均值和上下文切换
- 单核热点 vs 整机饱和

## 进程深入分析

找出消耗 CPU 的进程或线程：

```bash
ps -eo pid,ppid,cmd,%cpu,%mem --sort=-%cpu | head
top -H -b -n 1
pidstat -u -t -p ALL 1 3
```

如果某个进程明显很热，先使用低侵入检查：

```bash
pidstat -u -t -p <pid> 1 5
cat /proc/<pid>/sched
```

仅作为升级步骤（需明确授权、有界时长）：

```bash
perf top -p <pid>
perf record -F 49 -g -p <pid> -- sleep 10
perf report
timeout 10s strace -tt -T -p <pid>
```

## 解读

- 高 `%us` 且用户线程热通常意味着应用态 CPU 瓶颈。
- 高 `%sy` 意味着内核工作开销大；检查系统调用、锁、网络、文件系统和中断。
- 高 `%si` 或 `%hi` 暗示中断压力，通常与网络或驱动相关。
- 高负载但 `%us` 和 `%sy` 适中意味着不要止步于 CPU；检查 I/O 等待、阻塞任务和锁竞争。
- 如果总 CPU 高但没有突出的长生命周期进程，查找短生命周期工作进程抖动、fork 风暴或线程突发。

## 内核态 vs 应用态

- 应用态：热点函数在进程本身；`perf` 显示用户函数占主导。
- 内核态：`perf` 或 `top` 显示内核函数、软中断、调度器、TCP 栈或系统调用路径占主导。
- 混合情况：应用程序可能通过过多的系统调用、网络或文件系统活动触发内核瓶颈。同时报告内核热点和导致它的进程。
