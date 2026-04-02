# User Guide

## What ProcWatch solves
当电脑突然卡顿时，很多高占用进程会在你打开任务管理器前就恢复正常，导致很难定位根因。ProcWatch 通过后台持续采样，把“来不及看见的问题”记录下来。

## Core workflow
1. 打开程序
2. 点击开始监控（后续可支持开机自动启动）
3. 将窗口关闭到托盘
4. 等电脑再次出现卡顿
5. 打开历史图表与 Top N 记录，查看具体时段的高占用进程

## Recommended default settings
- 采样间隔：2 秒
- Top N：8
- 历史保留：30 天
- 开机自启动：开启
- 开机后最小化到托盘：开启
