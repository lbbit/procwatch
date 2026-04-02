# ProcWatch Agent Guide

## 项目目标
构建一个 Windows 常驻轻量级进程性能监控工具，用于在电脑短时卡顿时仍可持续记录 CPU 总利用率、CPU Top N 进程、内存 Top N 进程，并以美观图表方式回看历史数据。

## 技术路线
- 后端与桌面应用：Python 3.11
- UI：PySide6（Qt Widgets + Qt Charts）
- 采样：psutil
- 存储：SQLite + SQLAlchemy
- 打包：PyInstaller
- CI/CD：GitHub Actions Release

## 关键原则
1. 优先保证监控低开销：采样逻辑与 UI 渲染解耦。
2. 所有关键设计、里程碑、需求变更同步更新 `docs/`。
3. 修改功能时同步更新：
   - `docs/ARCHITECTURE.md`
   - `docs/DEVELOPMENT_PLAN.md`
   - `docs/FEATURE_MATRIX.md`
   - `README.md`
4. Windows 特性（托盘、自启动）优先考虑真实行为，Linux 下允许降级。
5. Release 必须产出绿色版 zip 包，并附 SHA256。
