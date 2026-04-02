# ProcWatch Architecture

## 1. Product positioning
ProcWatch is a lightweight Windows desktop monitor that continuously records system CPU load and heavy processes even when Task Manager is not opened in time.

## 2. Why PySide6
选择 PySide6 而不是 Python + WebView/Tauri 风格方案，主要原因：

1. **更稳的 Windows 打包链路**：PyInstaller + PySide6 在 GitHub Actions Windows runner 上成熟，避免 Web 前端构建链额外复杂度。
2. **原生托盘、自启动、窗口控制更顺手**。
3. **单进程绿色版分发更自然**，不需要额外 node/npm 依赖。
4. **界面依然可以做得美观**：通过现代配色、卡片布局、QSS、QtCharts 达成精致效果。

## 3. High-level modules

### 3.1 Collector layer
- `SystemSampler`: 采样系统总 CPU / 内存 / 时间戳
- `ProcessSampler`: 收集进程 CPU / RSS / 进程名 / PID
- `SnapshotReducer`: 只保留 Top N CPU 与 Top N Memory 记录，控制数据库体积

### 3.2 Storage layer
- SQLite database
- Tables:
  - `system_samples`
  - `process_samples`
  - `app_settings_snapshots`（可选，用于配置版本留痕）

### 3.3 Service layer
- `MonitorService`: 调度采样，控制周期与异常恢复
- `HistoryService`: 查询历史数据，提供图表友好的聚合接口
- `SettingsService`: 读写 JSON / INI / 默认配置
- `AutostartService`: 管理 Windows 开机自启动
- `TrayService`: 托盘菜单与窗口显隐

### 3.4 UI layer
- `DashboardWindow`
- `OverviewCard`: 当前状态卡片
- `HistoryChartPanel`: CPU / Memory 趋势图
- `TopProcessTable`: 热门进程排行
- `SettingsDialog`

## 4. Data flow
1. 定时器按照 `sampling_interval_seconds` 触发。
2. 采样器通过 `psutil` 获取总 CPU、总内存、进程快照。
3. Reducer 取 CPU Top N 与 Memory Top N。
4. 数据写入 SQLite。
5. UI 若已打开则刷新最新视图；若关闭则继续后台运行。
6. 用户查询历史时，通过 `HistoryService` 聚合数据库结果并绘制图表。

## 5. Performance strategy
- 默认采样间隔：2 秒
- 仅保存 Top N 进程，默认 N=8
- UI 图表使用降采样显示，避免一次绘制太多点
- 进程列表查询与排序在采样线程完成，UI 只接收结果
- 批量写库，减少 SQLite 事务频率
- 历史清理策略可配置（如保留 30/90/180 天）

## 6. SQLite schema draft

### system_samples
| column | type | note |
|---|---|---|
| id | INTEGER PK | |
| ts | DATETIME | UTC timestamp |
| cpu_percent | REAL | system cpu percent |
| memory_percent | REAL | system memory percent |
| total_memory_mb | INTEGER | |
| used_memory_mb | INTEGER | |

### process_samples
| column | type | note |
|---|---|---|
| id | INTEGER PK | |
| system_sample_id | INTEGER FK | link to system_samples |
| category | TEXT | `cpu` or `memory` |
| pid | INTEGER | |
| process_name | TEXT | |
| cpu_percent | REAL | |
| memory_mb | REAL | |

## 7. Release artifacts
- `ProcWatch-win-x64-portable.zip`
- `ProcWatch.exe`
- `SHA256SUMS.txt`

## 8. Future extensibility
- 卡顿事件自动标记
- CSV 导出
- 进程白名单/黑名单
- GPU 监控
- 崩溃自动恢复
