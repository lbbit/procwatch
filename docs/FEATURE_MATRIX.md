# Feature Matrix

| Feature | Status | Notes |
|---|---|---|
| 持续记录系统 CPU 利用率 | Implemented | 默认 2 秒采样 |
| 记录 CPU Top N 进程 | Implemented | 默认 N=8 |
| 记录 Memory Top N 进程 | Implemented | 默认 N=8 |
| SQLite 历史存储 | Implemented | 轻量本地存储 |
| 历史图表 | Implemented | Qt Charts |
| 历史总览点击查看对应时间点进程 | Implemented | 图表点击回查快照 |
| 历史页保留已选点位 | Implemented | 刷新后不强制跳回最新点 |
| 实时状态/历史查询/设置 Tab 分区 | Implemented | 降低页面复杂度 |
| 美观桌面界面 | Implemented | 深色现代风格 |
| JSON 配置导出/导入 | Implemented | Pydantic |
| INI 配置导出/导入 | Implemented | configparser |
| 关闭后托盘运行 | Implemented | QSystemTrayIcon |
| 托盘右键菜单 | Implemented | 打开/设置/立即采样/退出 |
| 开机自启动 | Implemented | Windows Run registry |
| 绿色版 exe 打包 | Implemented | PyInstaller |
| GitHub Release 自动上传 | Implemented | tag/release workflow |
| 历史保留与清理策略 | Implemented | 按 retention_days 自动清理 |
| 更智能卡顿事件检测 | Planned | 后续增强 |
