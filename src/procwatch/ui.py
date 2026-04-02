from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from procwatch.autostart import AutostartService
from procwatch.services import AppContext, MonitorService

DARK_QSS = """
QWidget { background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI'; }
QFrame[card='true'], QGroupBox {
  background: #111827;
  border: 1px solid #243041;
  border-radius: 14px;
}
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
}
QHeaderView::section {
  background: #172033;
  color: #cbd5e1;
  border: none;
  padding: 8px;
}
"""


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("color:#94a3b8;font-size:13px;")
        self.value = QLabel("--")
        self.value.setStyleSheet(f"font-size:28px;font-weight:700;color:{accent};")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.monitor_service = MonitorService(context)
        self.autostart_service = AutostartService()
        self.setWindowTitle("ProcWatch")
        self.resize(1360, 860)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()
        self._build_tray()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_once)
        self.apply_settings_to_timer()
        self.refresh_once()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        title = QLabel("ProcWatch · 瞬时卡顿捕手")
        title.setStyleSheet("font-size:30px;font-weight:800;")
        subtitle = QLabel("持续记录系统 CPU/内存与 Top 进程，让短时卡顿也有证据可查。")
        subtitle.setStyleSheet("color:#94a3b8;font-size:14px;")
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

        center = QHBoxLayout()
        center.setSpacing(18)
        layout.addLayout(center, 1)

        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()
        center.addLayout(left_panel, 3)
        center.addLayout(right_panel, 2)

        self.chart = QChart()
        self.chart.setBackgroundBrush(QColor("#111827"))
        self.chart.legend().setVisible(True)
        self.cpu_series = QLineSeries()
        self.cpu_series.setName("CPU %")
        self.mem_series = QLineSeries()
        self.mem_series.setName("Memory %")
        self.chart.addSeries(self.cpu_series)
        self.chart.addSeries(self.mem_series)
        self.axis_x = QValueAxis()
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setTitleText("最近样本")
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Percent")
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.cpu_series.attachAxis(self.axis_x)
        self.cpu_series.attachAxis(self.axis_y)
        self.mem_series.attachAxis(self.axis_x)
        self.mem_series.attachAxis(self.axis_y)
        chart_view = QChartView(self.chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        chart_group = QGroupBox("历史趋势")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.addWidget(chart_view)
        left_panel.addWidget(chart_group, 2)

        self.cpu_table = self._make_table()
        cpu_group = QGroupBox("CPU Top 进程")
        cpu_layout = QVBoxLayout(cpu_group)
        cpu_layout.addWidget(self.cpu_table)
        left_panel.addWidget(cpu_group, 1)

        self.mem_table = self._make_table()
        mem_group = QGroupBox("Memory Top 进程")
        mem_layout = QVBoxLayout(mem_group)
        mem_layout.addWidget(self.mem_table)
        right_panel.addWidget(mem_group, 1)

        settings_group = QGroupBox("设置")
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
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        export_json_btn = QPushButton("导出 JSON")
        export_json_btn.clicked.connect(self.export_json)
        import_json_btn = QPushButton("导入 JSON")
        import_json_btn.clicked.connect(self.import_json)
        export_ini_btn = QPushButton("导出 INI")
        export_ini_btn.clicked.connect(self.export_ini)
        import_ini_btn = QPushButton("导入 INI")
        import_ini_btn.clicked.connect(self.import_ini)
        for btn in [save_btn, export_json_btn, import_json_btn, export_ini_btn, import_ini_btn]:
            button_row.addWidget(btn)
        settings_layout.addLayout(button_row)
        right_panel.addWidget(settings_group, 1)

    def _make_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["PID", "Process", "CPU %", "Memory MB"])
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        menu = self.menuBar().addMenu("托盘")
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu = menu
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray.show()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def apply_settings_to_timer(self) -> None:
        interval_ms = int(self.context.config.monitor.sampling_interval_seconds * 1000)
        self.timer.start(interval_ms)

    def refresh_once(self) -> None:
        snapshot = self.monitor_service.collect_once()
        self.cpu_card.set_value(f"{snapshot.cpu_percent:.1f}%")
        self.mem_card.set_value(f"{snapshot.memory_percent:.1f}%")
        samples = self.monitor_service.recent_samples(limit=120)
        self.samples_card.set_value(str(len(samples)))
        ordered = list(reversed(samples))
        self.cpu_series.clear()
        self.mem_series.clear()
        for idx, sample in enumerate(ordered):
            self.cpu_series.append(idx, sample.cpu_percent)
            self.mem_series.append(idx, sample.memory_percent)
        self.axis_x.setRange(0, max(1, len(ordered) - 1))
        self._fill_table(self.cpu_table, snapshot.top_cpu_processes)
        self._fill_table(self.mem_table, snapshot.top_memory_processes)

    def _fill_table(self, table: QTableWidget, rows: list) -> None:
        table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            values = [
                str(item.pid),
                item.process_name,
                f"{item.cpu_percent:.1f}",
                f"{item.memory_mb:.1f}",
            ]
            for col, value in enumerate(values):
                table.setItem(row_index, col, QTableWidgetItem(value))

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
    base_dir = Path(__file__).resolve().parents[2]
    from procwatch.services import create_app_context

    context = create_app_context(base_dir)
    window = MainWindow(context)
    if not context.config.monitor.start_minimized:
        window.show()
    sys.exit(app.exec())
