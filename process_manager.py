import json
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class ProcessManagerDialog(QDialog):
    # 信号：mode 更改后通知主窗口刷新
    updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/process_manager.ui', self)

        # process.json 路径
        self.process_file = './data/process.json'

        # 加载项目列表
        self.load_processes()

        # 连接信号
        self.connect_signals()

    def load_processes(self):
        """加载 process.json 中的项目到 listWidget"""
        try:
            with open(self.process_file, 'r', encoding='utf-8') as f:
                self.processes = json.load(f)
        except FileNotFoundError:
            self.processes = {}

        self.listWidget.clear()
        for process_name, data in self.processes.items():
            mode = data['info']['mode']
            item_text = f"{process_name} ({mode})"
            self.listWidget.addItem(item_text)

    def connect_signals(self):
        """连接 listWidget 点击信号"""
        self.listWidget.itemClicked.connect(self.toggle_mode)

    def toggle_mode(self, item):
        """切换项目 mode 状态并保存"""
        # 提取项目名称（去除 (on/off) 部分）
        process_name = item.text().split(' (')[0]

        # 切换 mode
        current_mode = self.processes[process_name]['info']['mode']
        new_mode = "off" if current_mode == "on" else "on"
        self.processes[process_name]['info']['mode'] = new_mode

        # 更新 listWidget 显示
        item.setText(f"{process_name} ({new_mode})")

        # 保存到 process.json
        with open(self.process_file, 'w', encoding='utf-8') as f:
            json.dump(self.processes, f, ensure_ascii=False, indent=2)

        # 发出更新信号
        self.updated.emit()

    def closeEvent(self, event):
        """窗口关闭时发出信号"""
        self.updated.emit()
        super().closeEvent(event)