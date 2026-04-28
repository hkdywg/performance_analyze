# 内存分析

## 系统级检查

从容量、回收、交换和页面错误行为开始：

```bash
free -h
vmstat 1 5
sar -r 1 3
sar -B 1 3
```

关注点：

- `available` 内存，而不仅仅是 `free`
- swap 使用量和 swap in/out
- 主页面错误
- 回收压力
- OOM 杀死或分配失败

有用的辅助检查：

```bash
dmesg | tail -n 50
grep -i 'oom\|killed process' /var/log/messages /var/log/syslog 2>/dev/null
```

## 进程深入分析

识别占用内存或触发错误的进程：

```bash
ps -eo pid,ppid,cmd,%mem,rss,vsz --sort=-rss | head
smem -rk
pidstat -r -p ALL 1 3
```

如果怀疑是单个进程，检查其映射和增长模式：

```bash
pmap -x <pid> | tail -n 20
cat /proc/<pid>/status
cat /proc/<pid>/smaps_rollup
```

## 解读

- 低 `available` 加上活跃的 swap in/out 意味着真实内存压力。
- 大的页面缓存但健康的 `available` 不一定是问题。
- 高主错误或回收停滞即使在 OOM 之前也能导致延迟峰值。
- 重复的 OOM 事件表明内存不足或一个或多个失控进程。
- RSS 稳定增长或明显未释放分配的进程表明应用层泄漏或保留。

## 内核态 vs 应用态

- 应用态：一个或多个进程主导 RSS、泄漏内存或触发过多分配/错误。
- 内核态：slab 增长、回收行为、页面缓存压力或其他内核管理的内存行为占主导。
- 混合情况：内存饥饿的应用程序可能迫使内核回收和 swap 风暴。同时报告时间损失所在层，并指出触发它的进程。
