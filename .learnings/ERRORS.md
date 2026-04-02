## [ERR-20260402-001] pyside6-linux-ci-resolution

**Logged**: 2026-04-02T08:08:00Z
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
Linux CI 安装 PySide6 主包失败，需要改为拆分使用 PySide6-Essentials / Addons 或在 CI 跳过 GUI 依赖。

### Error
```
pip install -e .[dev]
... ERROR: Ignored the following versions that require a different python version ...
```

### Context
- 项目：procwatch
- 场景：Ubuntu runner / 当前 Linux 开发环境安装桌面 GUI 依赖
- 影响：pytest 与 lint 无法在当前依赖定义下跑起来

### Suggested Fix
将 GUI 依赖改为平台区分：Windows 使用 PySide6 与 Charts；Linux CI 仅安装测试所需核心依赖，或将 PySide6 版本放宽到可用版本并验证 Charts 安装链。

### Metadata
- Reproducible: yes
- Related Files: pyproject.toml, .github/workflows/ci.yml

---
## [ERR-20260402-002] qstyle-standard-icon-compat

**Logged**: 2026-04-02T08:17:00Z
**Priority**: high
**Status**: fixed
**Area**: ui

### Summary
`QStyle.StandardPixmap` 里并非所有平台/Qt 版本都存在 `SP_ComputerIcon`，直接访问会导致 Windows 打包后启动崩溃。

### Fix
改为优先加载项目内置应用图标；若失败，再回退到更稳定的标准图标如 `SP_DesktopIcon`。

---
