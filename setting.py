import json
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class SettingDialog(QDialog):
    # 定义关闭信号
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/setting.ui', self)

        # 配置文件路径
        self.config_file = './data/config.json'

        # 加载配置
        self.load_config()

        # 连接控件信号
        self.connect_signals()

    def load_config(self):
        """从 config.json 加载配置并更新控件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {
                "dingtalk_bot": "",
                "webhook_url": "",
                "secret": "",
                "name": []
            }

        # 更新控件
        self.lineEdit.setText(self.config['webhook_url'])
        self.lineEdit_2.setText(self.config['secret'])
        self.plainTextEdit.setPlainText('\n'.join(self.config['name']))
        self.label_4.setText(self.config['dingtalk_bot'] or "关闭")

    def save_config(self):
        """保存配置到 config.json"""
        # 获取 plainTextEdit 的名字列表，过滤空行
        names = [line.strip() for line in self.plainTextEdit.toPlainText().split('\n') if line.strip()]

        # 更新配置
        self.config['webhook_url'] = self.lineEdit.text()
        self.config['secret'] = self.lineEdit_2.text()
        self.config['name'] = names
        # dingtalk_bot 由 buttonBox 控制，不在此更新

        # 保存到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def connect_signals(self):
        """连接控件信号以检测更改和按钮操作"""
        self.lineEdit.textChanged.connect(self.save_config)
        self.lineEdit_2.textChanged.connect(self.save_config)
        self.plainTextEdit.textChanged.connect(self.save_config)

        # buttonBox 按钮操作
        self.buttonBox.accepted.connect(self.on_open_clicked)
        self.buttonBox.rejected.connect(self.on_close_clicked)

    def on_open_clicked(self):
        """点击 open 按钮"""
        self.config['dingtalk_bot'] = "开启"
        self.label_4.setText("开启")
        self.save_config()

    def on_close_clicked(self):
        """点击 close 按钮"""
        self.config['dingtalk_bot'] = "关闭"
        self.label_4.setText("关闭")
        self.save_config()

    def closeEvent(self, event):
        """窗口关闭时发出信号"""
        self.closed.emit()
        super().closeEvent(event)