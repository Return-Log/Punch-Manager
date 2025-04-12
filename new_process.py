import json
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QMessageBox
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class NewProcessDialog(QDialog):
    # 信号：窗口关闭时通知主窗口刷新
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/new_process.ui', self)

        # 配置文件路径
        self.config_file = './data/config.json'
        self.process_file = './data/process.json'

        # 加载 config.json 中的名字
        self.load_config_names()

        # 连接信号
        self.connect_signals()

    def load_config_names(self):
        """加载 config.json 中的 name 到 listWidget_2"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                names = config.get('name', [])
        except FileNotFoundError:
            names = []

        self.listWidget_2.clear()
        for name in names:
            self.listWidget_2.addItem(name)

    def connect_signals(self):
        """连接控件信号"""
        # listWidget 点击移动到 listWidget_2
        self.listWidget.itemClicked.connect(self.move_to_listWidget_2)
        # listWidget_2 点击移动到 listWidget
        self.listWidget_2.itemClicked.connect(self.move_to_listWidget)
        # pushButton 将 listWidget_2 全部移到 listWidget
        self.pushButton.clicked.connect(self.move_all_to_listWidget)
        # pushButton_2 保存并关闭
        self.pushButton_2.clicked.connect(self.save_and_close)
        # lineEdit_3 中文逗号转英文逗号
        self.lineEdit_3.textEdited.connect(self.convert_commas)

    def move_to_listWidget(self, item):
        """将 listWidget_2 的名字移到 listWidget"""
        self.listWidget_2.takeItem(self.listWidget_2.row(item))
        self.listWidget.addItem(item.text())

    def move_to_listWidget_2(self, item):
        """将 listWidget 的名字移回 listWidget_2"""
        self.listWidget.takeItem(self.listWidget.row(item))
        self.listWidget_2.addItem(item.text())

    def move_all_to_listWidget(self):
        """将 listWidget_2 所有名字移到 listWidget"""
        while self.listWidget_2.count() > 0:
            item = self.listWidget_2.takeItem(0)
            self.listWidget.addItem(item.text())

    def convert_commas(self, text):
        """将 lineEdit_3 中的中文逗号转为英文逗号"""
        new_text = text.replace('，', ',')
        if new_text != text:
            self.lineEdit_3.setText(new_text)

    def save_and_close(self):
        """保存新项目并关闭窗口"""
        # 获取主名称
        process_name = self.lineEdit.text().strip()
        if not process_name:
            QMessageBox.warning(self, "错误", "主名称不能为空")
            return

        # 检查是否已存在
        try:
            with open(self.process_file, 'r', encoding='utf-8') as f:
                processes = json.load(f)
        except FileNotFoundError:
            processes = {}

        if process_name in processes:
            QMessageBox.warning(self, "错误", f"项目 {process_name} 已存在")
            return

        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取 unfinished 列表
        unfinished = [self.listWidget.item(i).text() for i in range(self.listWidget.count())]

        # 获取 at_name，分割并清理
        at_name_text = self.lineEdit_3.text().strip()
        at_name = [name.strip() for name in at_name_text.split(',') if name.strip()] if at_name_text else []

        # 创建新项目
        new_process = {
            "info": {
                "at_name": at_name,
                "create_time": current_time,
                "description": self.lineEdit_2.text().strip(),
                "mode": "on"
            },
            "unfinished": unfinished,
            "finished": [],
            "change": {
                "new_finished": [],
                "new_unfinished": []
            },
            "update_time": current_time
        }

        # 追加到 processes
        processes[process_name] = new_process

        # 保存到 process.json
        with open(self.process_file, 'w', encoding='utf-8') as f:
            json.dump(processes, f, ensure_ascii=False, indent=2)

        # 发出关闭信号
        self.closed.emit()
        self.accept()

    def closeEvent(self, event):
        """窗口关闭时发出信号"""
        self.closed.emit()
        super().closeEvent(event)