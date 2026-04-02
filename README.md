# 🚀 ProcWatch

> A beautiful Windows desktop monitor that keeps watching when your PC suddenly stutters.

[![CI](https://github.com/lbbit/procwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/lbbit/procwatch/actions/workflows/ci.yml)
[![Release](https://github.com/lbbit/procwatch/actions/workflows/release.yml/badge.svg)](https://github.com/lbbit/procwatch/actions/workflows/release.yml)
![Platform](https://img.shields.io/badge/platform-Windows%2011%2F10-0078D6)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/github/license/lbbit/procwatch)

![Star History Chart](https://api.star-history.com/svg?repos=lbbit/procwatch&type=Date)

## ✨ Why this exists

电脑有时会 **突然变卡**，等你打开任务管理器的时候，一切又恢复正常了。

于是你只能得到一句：

> “刚才真的卡过，但现在看不出来了。”

**ProcWatch** 就是为这个痛点设计的：

- 🧠 持续记录系统 CPU / 内存历史
- 🔥 持续记录 CPU 占用最高的前 N 个进程
- 🐘 持续记录内存占用最高的前 N 个进程
- 📈 用美观图表回看问题发生时刻
- 🗃️ 使用 SQLite 保存历史数据
- ⚙️ 支持 JSON / INI 配置导入导出
- 🧺 支持最小化到托盘后台运行
- 🚀 支持开机自启动
- 📦 GitHub Actions 自动构建绿色版 EXE 发布包

## 🖼️ UI Design direction

ProcWatch 采用 **Python + PySide6 (Qt)** 方案，而不是“Python 后端 + Web 前端”混合架构。

原因很现实：

- 更适合 Windows 桌面常驻程序
- 托盘、自启动、窗口管理更省心
- PyInstaller 打包更直接
- GitHub Actions Windows 构建链更稳定
- 后续维护成本更低

界面目标：**现代、深色、卡片化、信息密度高但不杂乱**。

## 🏗️ Current architecture

```text
ProcWatch
├─ UI Layer (PySide6)
│  ├─ Dashboard
│  ├─ History Charts
│  ├─ Top Process Tables
│  └─ Settings Panel
├─ Service Layer
│  ├─ MonitorService
│  ├─ SettingsService
│  └─ AutostartService
├─ Collector Layer
│  ├─ SystemSampler
│  └─ ProcessSampler
└─ Storage Layer
   └─ SQLite + SQLAlchemy
```

更多设计细节见：

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)
- [`docs/FEATURE_MATRIX.md`](docs/FEATURE_MATRIX.md)
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)

## ✅ Planned / implemented features

| Feature | Status |
|---|---|
| 持续记录系统 CPU / 内存 | ✅ basic implementation |
| 记录 CPU Top N 进程 | ✅ basic implementation |
| 记录内存 Top N 进程 | ✅ basic implementation |
| SQLite 历史存储 | ✅ basic implementation |
| 历史趋势图 | ✅ basic implementation |
| 美观 Qt 桌面界面 | ✅ first version |
| JSON / INI 配置导入导出 | ✅ basic implementation |
| 托盘后台运行 | ✅ first version |
| Windows 开机自启动 | ✅ first version |
| 自动 Release 构建绿色版 | ✅ workflow ready |

## 📦 Quick start

### 1. Clone

```bash
git clone git@github.com:lbbit/procwatch.git
cd procwatch
```

### 2. Install

```bash
python -m pip install --upgrade pip
pip install -e .[dev]
```

### 3. Run

```bash
python -m procwatch.main
```

## 🧪 Test

```bash
pytest -q
ruff check .
```

## 🎨 App icon

打包使用仓库内置图标：

- `assets/app_icon.png`
- `assets/app_icon.ico`

当前图标已替换为用户提供的芯片图标。

## 🛠️ Build portable EXE

### Local build

```bash
pip install pyinstaller
python scripts/build_portable.py
```

Artifacts:

- `dist/ProcWatch-win-x64-portable.zip`
- `dist/SHA256SUMS.txt`

### GitHub Release build

推送 tag 即可自动构建：

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 📚 Usage guide

1. 打开 ProcWatch
2. 保持后台运行
3. 当电脑再次突然变卡
4. 重新打开窗口
5. 查看图表和 Top N 表格，定位可疑进程

## 🗺️ Roadmap

- [ ] 历史时段筛选
- [ ] 自动识别“卡顿事件”
- [ ] CSV 导出
- [ ] 更精致的图表与交互
- [ ] 数据压缩与长周期归档
- [ ] GPU / Disk 指标扩展

## 🤝 Contributing

欢迎提 issue / PR / feature request。

如果这个工具对你有帮助，欢迎点个 **Star** ⭐

## 📄 License

MIT
