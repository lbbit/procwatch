# Development Plan

## Milestones

### M1 - Foundation
- [x] 仓库初始化
- [x] 技术方案选型
- [x] 基础目录结构
- [x] 配置模型与持久化
- [x] SQLite schema 与 repository 层

### M2 - Monitoring engine
- [x] psutil 采样器
- [x] Top N 进程筛选
- [x] 低开销定时采样线程（已改为后台 worker 线程）
- [x] 历史保留与清理策略

### M3 - Desktop UI
- [x] 主界面布局
- [x] 实时概览卡片
- [x] 历史趋势图
- [x] Top N 表格
- [x] 设置面板
- [x] 托盘菜单

### M4 - Windows integration
- [x] 开机自启动
- [x] 最小化到托盘
- [x] 关闭窗口继续后台运行
- [x] JSON/INI 导入导出

### M5 - Quality & release
- [x] 单元测试
- [x] Windows 打包脚本
- [x] GitHub Actions CI
- [x] GitHub Actions Release 自动上传附件
- [x] README、截图占位、使用指南
