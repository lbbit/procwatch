from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from procwatch.autostart import AutostartService
from procwatch.database import HistoryPoint
from procwatch.models import ProcessMetric, SystemSnapshot
from procwatch.services import AppContext, MonitorService

DARK_QSS = """
QWidget { background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI'; }
QTabWidget::pane, QFrame[card='true'], QGroupBox {
  background: #111827;
  border: 1px solid #243041;
  border-radius: 14px;
}
QTabBar::tab {
  background: #172033;
  color: #cbd5e1;
  border: 1px solid #243041;
  padding: 10px 18px;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  margin-right: 4px;
}
QTabBar::tab:selected { background: #2563eb; color: white; }
QGroupBox { margin-top: 12px; padding-top: 12px; font-weight: 600; }
QPushButton {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 600;
}
QPushButton:hover { background: #3b82f6; }
QTableWidget {
  background: #0b1220;
  alternate-background-color: #111827;
  gridline-color: #243041;
  border: 1px solid #243041;
  border-radius: 10px;
  selection-background-color: #1d4ed8;
}
QHeaderView::section {
  background: #172033;
  color: #cbd5e1;
  border: none;
  padding: 8px;
}
QLabel[muted='true'] { color:#94a3b8; }
"""


def resolve_asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        candidate = base_dir / "assets" / name
        if candidate.exists():
            return candidate
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / "assets" / name
            if candidate.exists():
                return candidate
    base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "assets" / name


def load_app_icon() -> QIcon:
    for name in ["app_icon.ico", "app_icon.png"]:
        icon_path = resolve_asset_path(name)
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                return icon
    return QIcon()


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setProperty("muted", True)
        self.title.setStyleSheet("font-size:13px;")
        self.value = QLabel("--")
        self.value.setStyleSheet(f"font-size:28px;font-weight:700;color:{accent};")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class SamplingWorker(QThread):
    snapshot_ready = Signal(object, object, object)
    error_raised = Signal(str)

    def __init__(self, monitor_service: MonitorService) -> None:
        super().__init__()
        self.monitor_service = monitor_service

    def run(self) -> None:
        try:
            snapshot = self.monitor_service.collect_once()
            history = self.monitor_service.history_points(limit=2000)
            self.snapshot_ready.emit(snapshot, history, None)
        except Exception as exc:  # noqa: BLE001
            self.error_raised.emit(str(exc))


class HistoryChartView(QChartView):
    point_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sample_ids: list[int] = []

    def set_sample_ids(self, sample_ids: list[int]) -> None:
        self._sample_ids = sample_ids

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._sample_ids:
            return super().mousePressEvent(event)
        value = self.chart().mapToValue(event.position())
        index = int(round(value.x()))
        index = max(0, min(index, len(self._sample_ids) - 1))
        self.point_selected.emit(self._sample_ids[index])
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.monitor_service = MonitorService(context)
        self.autostart_service = AutostartService()
        self.app_icon = load_app_icon()
        self.current_snapshot: SystemSnapshot | None = None
        self.current_history: list[HistoryPoint] = []
        self.worker: SamplingWorker | None = None
        self._ui_busy = False
        self.selected_sample_id: int | None = None
        self.last_active_tab_index = 0

        self.setWindowTitle("ProcWatch")
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)
        self.resize(1460, 920)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()
        self._build_tray()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.apply_settings_to_timer()
        self.request_refresh()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        title = QLabel("ProcWatch · 瞬时卡顿捕手")
        title.setStyleSheet("font-size:30px;font-weight:800;")
        subtitle = QLabel(
            "持续记录系统 CPU/内存与 Top 进程，实时轻量监控，支持按时间点回看卡顿现场。"
        )
        subtitle.setProperty("muted", True)
        subtitle.setStyleSheet("font-size:14px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        cards = QGridLayout()
        self.cpu_card = MetricCard("系统 CPU", "#60a5fa")
        self.mem_card = MetricCard("系统内存", "#34d399")
        self.samples_card = MetricCard("历史样本", "#f59e0b")
        cards.addWidget(self.cpu_card, 0, 0)
        cards.addWidget(self.mem_card, 0, 1)
        cards.addWidget(self.samples_card, 0, 2)
        layout.addLayout(cards)

        top_actions = QHBoxLayout()
        self.refresh_button = QPushButton("立即刷新数据")
        self.refresh_button.clicked.connect(self.request_refresh)
        self.refresh_status_label = QLabel("状态：等待首次采样")
        self.refresh_status_label.setProperty("muted", True)
        top_actions.addWidget(self.refresh_button)
        top_actions.addWidget(self.refresh_status_label)
        top_actions.addStretch(1)
        layout.addLayout(top_actions)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.realtime_tab = QWidget()
        self.history_tab = QWidget()
        self.settings_tab = QWidget()
        self.tabs.addTab(self.realtime_tab, "实时状态")
        self.tabs.addTab(self.history_tab, "历史查询")
        self.tabs.addTab(self.settings_tab, "设置")

        self._build_realtime_tab()
        self._build_history_tab()
        self._build_settings_tab()

    def _build_realtime_tab(self) -> None:
        layout = QVBoxLayout(self.realtime_tab)
        layout.setSpacing(18)

        realtime_top = QHBoxLayout()
        layout.addLayout(realtime_top, 1)

        chart_group = QGroupBox("最近趋势")
        chart_layout = QVBoxLayout(chart_group)
        self.realtime_chart = QChart()
        self.realtime_chart.setBackgroundBrush(QColor("#111827"))
        self.realtime_chart.legend().setVisible(True)
        self.rt_cpu_series = QLineSeries()
        self.rt_cpu_series.setName("CPU %")
        self.rt_mem_series = QLineSeries()
        self.rt_mem_series.setName("Memory %")
        self.realtime_chart.addSeries(self.rt_cpu_series)
        self.realtime_chart.addSeries(self.rt_mem_series)
        self.rt_axis_x = QValueAxis()
        self.rt_axis_x.setLabelFormat("%d")
        self.rt_axis_x.setTitleText("最近样本")
        self.rt_axis_y = QValueAxis()
        self.rt_axis_y.setRange(0, 100)
        self.rt_axis_y.setTitleText("Percent")
        self.realtime_chart.addAxis(self.rt_axis_x, Qt.AlignBottom)
        self.realtime_chart.addAxis(self.rt_axis_y, Qt.AlignLeft)
        self.rt_cpu_series.attachAxis(self.rt_axis_x)
        self.rt_cpu_series.attachAxis(self.rt_axis_y)
        self.rt_mem_series.attachAxis(self.rt_axis_x)
        self.rt_mem_series.attachAxis(self.rt_axis_y)
        chart_view = QChartView(self.realtime_chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_layout.addWidget(chart_view)
        realtime_top.addWidget(chart_group, 3)

        status_group = QGroupBox("当前说明")
        status_layout = QVBoxLayout(status_group)
        self.realtime_hint = QLabel(
            "实时状态页聚焦当前与最近样本；历史查询页可点击任意时间点查看当时的进程快照。"
        )
        self.realtime_hint.setWordWrap(True)
        self.realtime_hint.setProperty("muted", True)
        self.current_time_label = QLabel("当前样本时间：--")
        self.current_time_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_cpu_label = QLabel("当前 CPU Top：--")
        self.current_cpu_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_mem_label = QLabel("当前 Memory Top：--")
        self.current_mem_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        for widget in [
            self.realtime_hint,
            self.current_time_label,
            self.current_cpu_label,
            self.current_mem_label,
        ]:
            status_layout.addWidget(widget)
        status_layout.addStretch(1)
        realtime_top.addWidget(status_group, 2)

        tables_row = QHBoxLayout()
        layout.addLayout(tables_row, 2)
        self.cpu_table = self._make_table()
        self.mem_table = self._make_table()
        cpu_group = QGroupBox("CPU Top 进程")
        cpu_layout = QVBoxLayout(cpu_group)
        cpu_layout.addWidget(self.cpu_table)
        mem_group = QGroupBox("Memory Top 进程")
        mem_layout = QVBoxLayout(mem_group)
        mem_layout.addWidget(self.mem_table)
        tables_row.addWidget(cpu_group, 1)
        tables_row.addWidget(mem_group, 1)

    def _build_history_tab(self) -> None:
        layout = QVBoxLayout(self.history_tab)
        layout.setSpacing(18)

        history_header = QHBoxLayout()
        self.history_refresh_button = QPushButton("刷新历史数据")
        self.history_refresh_button.clicked.connect(self.request_refresh)
        self.history_mode_label = QLabel("提示：点击图表定位时间点；不会再自动跳回最新点。")
        self.history_mode_label.setProperty("muted", True)
        history_header.addWidget(self.history_refresh_button)
        history_header.addWidget(self.history_mode_label)
        history_header.addStretch(1)
        layout.addLayout(history_header)

        history_chart_group = QGroupBox("历史总览（点击图表定位时间点）")
        history_chart_layout = QVBoxLayout(history_chart_group)
        self.history_chart = QChart()
        self.history_chart.setBackgroundBrush(QColor("#111827"))
        self.history_chart.legend().setVisible(True)
        self.history_cpu_series = QLineSeries()
        self.history_cpu_series.setName("CPU %")
        self.history_mem_series = QLineSeries()
        self.history_mem_series.setName("Memory %")
        self.history_selected_point = QScatterSeries()
        self.history_selected_point.setName("Selected")
        self.history_selected_point.setMarkerSize(12.0)
        self.history_chart.addSeries(self.history_cpu_series)
        self.history_chart.addSeries(self.history_mem_series)
        self.history_chart.addSeries(self.history_selected_point)
        self.history_axis_x = QValueAxis()
        self.history_axis_x.setLabelFormat("%d")
        self.history_axis_x.setTitleText("历史样本索引")
        self.history_axis_y = QValueAxis()
        self.history_axis_y.setRange(0, 100)
        self.history_axis_y.setTitleText("Percent")
        self.history_chart.addAxis(self.history_axis_x, Qt.AlignBottom)
        self.history_chart.addAxis(self.history_axis_y, Qt.AlignLeft)
        for series in [
            self.history_cpu_series,
            self.history_mem_series,
            self.history_selected_point,
        ]:
            series.attachAxis(self.history_axis_x)
            series.attachAxis(self.history_axis_y)
        self.history_chart_view = HistoryChartView()
        self.history_chart_view.setChart(self.history_chart)
        self.history_chart_view.setRenderHint(QPainter.Antialiasing)
        self.history_chart_view.point_selected.connect(self.load_sample_details)
        history_chart_layout.addWidget(self.history_chart_view)
        layout.addWidget(history_chart_group, 2)

        detail_row = QHBoxLayout()
        layout.addLayout(detail_row, 2)

        detail_group = QGroupBox("选中时间点详情")
        detail_layout = QVBoxLayout(detail_group)
        self.selected_time_label = QLabel("时间点：--")
        self.selected_time_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.selected_summary_label = QLabel("说明：点击上方历史图任意位置查看当时快照")
        self.selected_summary_label.setWordWrap(True)
        self.selected_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        detail_layout.addWidget(self.selected_time_label)
        detail_layout.addWidget(self.selected_summary_label)
        detail_layout.addStretch(1)
        detail_row.addWidget(detail_group, 1)

        self.history_cpu_table = self._make_table()
        self.history_mem_table = self._make_table()
        history_cpu_group = QGroupBox("该时间点 CPU Top")
        history_cpu_layout = QVBoxLayout(history_cpu_group)
        history_cpu_layout.addWidget(self.history_cpu_table)
        history_mem_group = QGroupBox("该时间点 Memory Top")
        history_mem_layout = QVBoxLayout(history_mem_group)
        history_mem_layout.addWidget(self.history_mem_table)
        detail_row.addWidget(history_cpu_group, 2)
        detail_row.addWidget(history_mem_group, 2)

    def _build_settings_tab(self) -> None:
        layout = QVBoxLayout(self.settings_tab)
        layout.setSpacing(18)

        settings_group = QGroupBox("采样与行为设置")
        settings_layout = QVBoxLayout(settings_group)
        form = QFormLayout()
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(1.0, 60.0)
        self.interval_spin.setValue(self.context.config.monitor.sampling_interval_seconds)
        self.interval_spin.setSuffix(" s")
        self.top_cpu_spin = QSpinBox()
        self.top_cpu_spin.setRange(1, 50)
        self.top_cpu_spin.setValue(self.context.config.monitor.top_n_cpu)
        self.top_mem_spin = QSpinBox()
        self.top_mem_spin.setRange(1, 50)
        self.top_mem_spin.setValue(self.context.config.monitor.top_n_memory)
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 3650)
        self.retention_spin.setValue(self.context.config.monitor.retention_days)
        self.close_to_tray_checkbox = QCheckBox("关闭窗口时最小化到托盘")
        self.close_to_tray_checkbox.setChecked(self.context.config.monitor.close_to_tray)
        self.autostart_checkbox = QCheckBox("Windows 开机自启动")
        self.autostart_checkbox.setChecked(self.autostart_service.is_enabled())
        form.addRow("采样间隔", self.interval_spin)
        form.addRow("CPU Top N", self.top_cpu_spin)
        form.addRow("Memory Top N", self.top_mem_spin)
        form.addRow("历史保留天数", self.retention_spin)
        settings_layout.addLayout(form)
        settings_layout.addWidget(self.close_to_tray_checkbox)
        settings_layout.addWidget(self.autostart_checkbox)

        button_row = QHBoxLayout()
        for text, handler in [
            ("保存设置", self.save_settings),
            ("导出 JSON", self.export_json),
            ("导入 JSON", self.import_json),
            ("导出 INI", self.export_ini),
            ("导入 INI", self.import_ini),
        ]:
            button = QPushButton(text)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        settings_layout.addLayout(button_row)
        layout.addWidget(settings_group)

        notes_group = QGroupBox("优化说明")
        notes_layout = QVBoxLayout(notes_group)
        for text in [
            "• 系统 CPU 现在使用短采样窗口（0.15s）计算，避免长期出现 0%。",
            "• 已将采样移到后台线程，避免界面每 2 秒卡顿。",
            "• 历史页支持手动刷新，不会在查看旧点时自动跳回最新点。",
            "• 切换到历史页时会自动刷新一次最新数据。",
        ]:
            label = QLabel(text)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            notes_layout.addWidget(label)
        notes_layout.addStretch(1)
        layout.addWidget(notes_group, 1)

    def _make_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["PID", "Process", "CPU %", "Memory MB"])
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideMiddle)
        table.setSortingEnabled(False)
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        copy_action = QAction("复制选中行", table)
        copy_action.triggered.connect(lambda t=table: self.copy_selected_row(t))
        table.addAction(copy_action)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        return table

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        tray_icon = self.app_icon
        if tray_icon.isNull():
            tray_icon = self.style().standardIcon(QStyle.SP_DesktopIcon)
        self.tray.setIcon(tray_icon)

        tray_menu = QMenu(self)
        open_action = tray_menu.addAction("打开界面")
        open_action.triggered.connect(self.show_from_tray)
        settings_action = tray_menu.addAction("打开设置")
        settings_action.triggered.connect(self.show_settings_tab)
        tray_menu.addSeparator()
        refresh_action = tray_menu.addAction("立即采样")
        refresh_action.triggered.connect(self.request_refresh)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("退出程序")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger}:
            self.show_from_tray()

    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_settings_tab(self) -> None:
        self.tabs.setCurrentWidget(self.settings_tab)
        self.show_from_tray()

    def on_timer_tick(self) -> None:
        if self.tabs.currentWidget() == self.realtime_tab:
            self.request_refresh()

    def on_tab_changed(self, index: int) -> None:
        previous_tab = self.tabs.widget(self.last_active_tab_index)
        current_tab = self.tabs.widget(index)
        self.last_active_tab_index = index
        if current_tab == self.history_tab and previous_tab != self.history_tab:
            self.request_refresh()

    def request_refresh(self) -> None:
        if self._ui_busy:
            return
        self._ui_busy = True
        self.refresh_button.setEnabled(False)
        self.history_refresh_button.setEnabled(False)
        self.refresh_status_label.setText("状态：后台刷新中...")
        self.worker = SamplingWorker(self.monitor_service)
        self.worker.snapshot_ready.connect(self.on_snapshot_ready)
        self.worker.error_raised.connect(self.on_worker_error)
        self.worker.finished.connect(self._clear_worker_state)
        self.worker.start()

    def _clear_worker_state(self) -> None:
        self._ui_busy = False
        self.worker = None
        self.refresh_button.setEnabled(True)
        self.history_refresh_button.setEnabled(True)

    def on_worker_error(self, message: str) -> None:
        self.refresh_status_label.setText(f"状态：刷新失败 - {message}")
        self.selected_summary_label.setText(f"后台采样失败：{message}")

    def apply_settings_to_timer(self) -> None:
        interval_ms = int(self.context.config.monitor.sampling_interval_seconds * 1000)
        self.timer.start(interval_ms)

    def on_snapshot_ready(
        self,
        snapshot: SystemSnapshot,
        history: list[HistoryPoint],
        _placeholder: Any,
    ) -> None:
        self.current_snapshot = snapshot
        self.current_history = history
        self.cpu_card.set_value(f"{snapshot.cpu_percent:.1f}%")
        self.mem_card.set_value(f"{snapshot.memory_percent:.1f}%")
        self.samples_card.set_value(str(len(history)))
        self.refresh_status_label.setText(
            f"状态：最近刷新 {snapshot.timestamp.astimezone().strftime('%H:%M:%S')}"
        )
        self.current_time_label.setText(
            f"当前样本时间：{snapshot.timestamp.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.current_cpu_label.setText(
            "当前 CPU Top：" + self._format_process_summary(snapshot.top_cpu_processes)
        )
        self.current_mem_label.setText(
            "当前 Memory Top：" + self._format_process_summary(snapshot.top_memory_processes)
        )
        self._fill_table(self.cpu_table, snapshot.top_cpu_processes)
        self._fill_table(self.mem_table, snapshot.top_memory_processes)
        self._update_realtime_chart(history[-120:])
        self._update_history_chart(history)
        if self.selected_sample_id is None and history:
            self.load_sample_details(history[-1].sample_id)
        elif self.selected_sample_id is not None:
            if any(point.sample_id == self.selected_sample_id for point in history):
                self.load_sample_details(self.selected_sample_id)
            elif history:
                self.load_sample_details(history[-1].sample_id)

    def _update_realtime_chart(self, history: list[HistoryPoint]) -> None:
        self.rt_cpu_series.clear()
        self.rt_mem_series.clear()
        for idx, point in enumerate(history):
            self.rt_cpu_series.append(idx, point.cpu_percent)
            self.rt_mem_series.append(idx, point.memory_percent)
        self.rt_axis_x.setRange(0, max(1, len(history) - 1))

    def _update_history_chart(self, history: list[HistoryPoint]) -> None:
        self.history_cpu_series.clear()
        self.history_mem_series.clear()
        self.history_selected_point.clear()
        sample_ids: list[int] = []
        for idx, point in enumerate(history):
            self.history_cpu_series.append(idx, point.cpu_percent)
            self.history_mem_series.append(idx, point.memory_percent)
            sample_ids.append(point.sample_id)
        self.history_chart_view.set_sample_ids(sample_ids)
        self.history_axis_x.setRange(0, max(1, len(history) - 1))

    def load_sample_details(self, sample_id: int) -> None:
        self.selected_sample_id = sample_id
        history_index = next(
            (idx for idx, point in enumerate(self.current_history) if point.sample_id == sample_id),
            None,
        )
        if history_index is not None:
            point = self.current_history[history_index]
            self.history_selected_point.clear()
            self.history_selected_point.append(history_index, point.cpu_percent)
            self.selected_time_label.setText(
                f"时间点：{point.timestamp.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.selected_summary_label.setText(
                f"系统 CPU {point.cpu_percent:.1f}% · 系统内存 {point.memory_percent:.1f}%"
            )
        cpu_rows = self.monitor_service.sample_processes(sample_id, "cpu")
        mem_rows = self.monitor_service.sample_processes(sample_id, "memory")
        self._fill_table(self.history_cpu_table, cpu_rows)
        self._fill_table(self.history_mem_table, mem_rows)

    def _fill_table(self, table: QTableWidget, rows: list[ProcessMetric]) -> None:
        table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            values = [
                str(item.pid),
                item.process_name,
                f"{item.cpu_percent:.1f}",
                f"{item.memory_mb:.1f}",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                if col in {0, 1}:
                    cell.setToolTip(value)
                table.setItem(row_index, col, cell)
        table.resizeRowsToContents()

    def copy_selected_row(self, table: QTableWidget) -> None:
        row = table.currentRow()
        if row < 0:
            return
        values = []
        for col in range(table.columnCount()):
            item = table.item(row, col)
            values.append(item.text() if item else "")
        QGuiApplication.clipboard().setText("\t".join(values))

    def _format_process_summary(self, rows: list[ProcessMetric]) -> str:
        if not rows:
            return "--"
        return "；".join(
            (
                f"{item.process_name} (PID {item.pid}, "
                f"CPU {item.cpu_percent:.1f}%, MEM {item.memory_mb:.1f} MB)"
            )
            for item in rows[:3]
        )

    def save_settings(self) -> None:
        monitor = self.context.config.monitor
        monitor.sampling_interval_seconds = self.interval_spin.value()
        monitor.top_n_cpu = self.top_cpu_spin.value()
        monitor.top_n_memory = self.top_mem_spin.value()
        monitor.retention_days = self.retention_spin.value()
        monitor.close_to_tray = self.close_to_tray_checkbox.isChecked()
        monitor.auto_start = self.autostart_checkbox.isChecked()
        self.context.settings_service.save(self.context.config)
        self.autostart_service.set_enabled(monitor.auto_start, Path(sys.executable))
        self.apply_settings_to_timer()
        QMessageBox.information(self, "ProcWatch", "设置已保存。")

    def export_json(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 JSON",
            "procwatch-config.json",
            "JSON (*.json)",
        )
        if file_path:
            self.context.settings_service.export_json(self.context.config, Path(file_path))

    def import_json(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入 JSON",
            "",
            "JSON (*.json)",
        )
        if file_path:
            self.context.config = self.context.settings_service.import_json(Path(file_path))
            self.context.settings_service.save(self.context.config)
            QMessageBox.information(
                self,
                "ProcWatch",
                "JSON 配置已导入，请重启程序以完全应用。",
            )

    def export_ini(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 INI",
            "procwatch-config.ini",
            "INI (*.ini)",
        )
        if file_path:
            self.context.settings_service.export_ini(self.context.config, Path(file_path))

    def import_ini(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入 INI",
            "",
            "INI (*.ini)",
        )
        if file_path:
            self.context.config = self.context.settings_service.import_ini(Path(file_path))
            self.context.settings_service.save(self.context.config)
            QMessageBox.information(
                self,
                "ProcWatch",
                "INI 配置已导入，请重启程序以完全应用。",
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.context.config.monitor.close_to_tray and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "ProcWatch",
                "程序仍在后台持续监控。",
                QSystemTrayIcon.Information,
                2000,
            )
            event.ignore()
            return
        super().closeEvent(event)


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ProcWatch")
    app.setDesktopFileName("ProcWatch")
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    from procwatch.services import create_app_context

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("lbbit.procwatch")
        except Exception:
            pass

    base_dir = Path(__file__).resolve().parents[2]
    context = create_app_context(base_dir)
    window = MainWindow(context)
    if not context.config.monitor.start_minimized:
        window.show()
    sys.exit(app.exec())
