import sys
import json
import threading
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QGridLayout,
                             QWidget, QScrollArea, QMessageBox, QDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.uic import loadUi
from setting import SettingDialog
from new_process import NewProcessDialog
from process_manager import ProcessManagerDialog


class DingTalkThread(threading.Thread):
    def __init__(self, webhook_url, secret, process_name, at_name, new_finished, new_unfinished, finished, unfinished):
        super().__init__()
        self.webhook_url = webhook_url
        self.secret = secret
        self.process_name = process_name
        self.at_name = at_name
        self.new_finished = new_finished
        self.new_unfinished = new_unfinished
        self.finished = finished
        self.unfinished = unfinished

    def run(self):
        try:
            # Log webhook_url for debugging
            print(f"Webhook URL: {self.webhook_url}")
            print(f"Secret: {self.secret}")

            # 生成时间戳和签名
            timestamp = str(round(time.time() * 1000))
            secret_enc = self.secret.encode('utf-8')
            string_to_sign = f"{timestamp}\n{self.secret}"
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

            # 构造 Webhook URL（修复 ×tamp 为 timestamp）
            url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            print(f"Constructed URL: {url}")

            # 构建 Markdown 文本
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            at_name_text = "、".join([f"@{name}" for name in self.at_name]) or ""
            new_finished_text = "、".join(self.new_finished) or "- 无"
            new_unfinished_text = "、".join(self.new_unfinished) or "- 无"
            finished_text = "、".join(self.finished) or "- 无"
            unfinished_text = "、".join(self.unfinished) or "- 无"

            markdown_text = (
                f"## {self.process_name}{'' if not at_name_text else ' ' + at_name_text}\n"
                f"### 新增已完成人员\n{new_finished_text}\n"
                f"### 新增未完成人员\n{new_unfinished_text}\n"
                f"### 当前已完成人员\n{finished_text}\n"
                f"### 当前未完成人员\n{unfinished_text}\n"
                f"\n------\n"
                f"开源项目仓库 <https://github.com/Return-Log/Punch-Manager>\n"
                f"*{current_time}*\n"
            )

            # 构造有效负载
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "打卡信息",
                    "text": markdown_text
                },
                "at": {
                    "atMobiles": self.at_name,
                    "isAtAll": False
                }
            }

            # 配置重试会话
            session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"]
            )
            session.mount("https://", HTTPAdapter(max_retries=retries))

            # 发送 POST 请求
            headers = {"Content-Type": "application/json"}
            response = session.post(url, json=payload, headers=headers, timeout=10, verify=True)
            response_json = response.json()

            # 检查响应
            if response.status_code != 200 or response_json.get("errcode") != 0:
                print(f"DingTalk send failed: Status={response.status_code}, Response={response.text}")
            else:
                print("DingTalk message sent successfully")

        except requests.exceptions.SSLError as ssl_err:
            print(f"DingTalk SSL error: {str(ssl_err)}")
        except requests.exceptions.RequestException as req_err:
            print(f"DingTalk request error: {str(req_err)}")
        except Exception as e:
            print(f"DingTalk unexpected error: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('./ui/mainwindow.ui', self)

        # 加载数据
        self.data_file = './data/process.json'
        self.config_file = './data/config.json'
        self.load_data()

        # 当前项目
        self.current_process = self.get_latest_process()

        # 本次运行的更改
        self.current_changes = {
            'new_finished': set(),
            'new_unfinished': set()
        }

        # 初始化布局
        if self.current_process is None:
            self.label_3.setText("## 无项目")
            self.setup_scroll_areas_empty()
        else:
            self.label_3.setText(f"## {self.current_process}")
            self.setup_scroll_areas()

        # 设置项目菜单
        self.setup_process_menu()

        # 连接动作
        self.action1.triggered.connect(self.open_setting_dialog)
        self.action1_2.triggered.connect(self.open_about_dialog)
        self.action1_3.triggered.connect(self.open_new_process_dialog)
        self.action1_4.triggered.connect(self.open_process_manager_dialog)

    def open_setting_dialog(self):
        """打开设置窗口前检查保存"""
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process if self.current_process else "无项目"} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        dialog = SettingDialog(self)
        dialog.closed.connect(self.refresh_ui)
        dialog.exec()

    def open_new_process_dialog(self):
        """打开新建项目窗口前检查保存"""
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process if self.current_process else "无项目"} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        dialog = NewProcessDialog(self)
        dialog.closed.connect(self.refresh_ui)
        dialog.exec()

    def open_process_manager_dialog(self):
        """打开项目管理窗口前检查保存"""
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process if self.current_process else "无项目"} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        dialog = ProcessManagerDialog(self)
        dialog.updated.connect(self.refresh_ui)
        dialog.exec()

    def refresh_ui(self):
        """刷新主窗口界面"""
        self.load_data()
        old_process = self.current_process
        self.current_process = self.get_latest_process()
        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}
        if self.current_process is None:
            self.label_3.setText("## 无项目")
            self.setup_scroll_areas_empty()
        else:
            self.label_3.setText(f"## {self.current_process}")
            self.setup_scroll_areas()
        self.setup_process_menu()

    def load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            # 如果文件为空，初始化默认空项目
            if not self.data:
                self.data = {
                    "当前没有项目，请新建项目": {
                        "info": {
                            "at_name": [],
                            "create_time": "",
                            "description": "",
                            "mode": "on"
                        },
                        "unfinished": [],
                        "finished": [],
                        "change": {
                            "new_finished": [],
                            "new_unfinished": []
                        },
                        "update_time": ""
                    }
                }
        except FileNotFoundError:
            self.data = {
                "当前没有项目，请新建项目": {
                    "info": {
                        "at_name": [],
                        "create_time": "",
                        "description": "",
                        "mode": "on"
                    },
                    "unfinished": [],
                    "finished": [],
                    "change": {
                        "new_finished": [],
                        "new_unfinished": []
                    },
                    "update_time": ""
                }
            }
        self.initial_states = {}
        for process in self.data:
            self.initial_states[process] = {
                'unfinished': set(self.data[process]['unfinished']),
                'finished': set(self.data[process]['finished'])
            }

    def get_latest_process(self):
        latest_time = None
        latest_process = None
        for process, data in self.data.items():
            if data['info']['mode'] == 'on':
                update_time = data.get('update_time', '')
                if update_time:
                    try:
                        dt = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                        if latest_time is None or dt > latest_time:
                            latest_time = dt
                            latest_process = process
                    except ValueError:
                        continue
                elif latest_process is None:
                    latest_process = process
        return latest_process  # 返回 None 如果没有有效项目

    def setup_process_menu(self):
        """清空 menu_2 后重新添加 action1_3, action1_4 和 mode: on 的项目"""
        self.menu_2.clear()
        self.menu_2.addAction(self.action1_3)
        self.menu_2.addAction(self.action1_4)
        self.menu_2.addSeparator()
        for process in self.data:
            if self.data[process]['info']['mode'] == 'on':
                action = self.menu_2.addAction(process)
                action.triggered.connect(lambda checked, p=process: self.switch_process(p))

    def switch_process(self, process):
        if process == self.current_process:
            return

        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process if self.current_process else "无项目"} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.current_process = process
        self.label_3.setText(f"## {process}")
        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}
        self.setup_scroll_areas()

    def save_data(self):
        if self.current_process is None:
            return  # 没有项目时不保存
        self.data[self.current_process]['unfinished'] = [label.text() for label in self.unfinished_labels]
        self.data[self.current_process]['finished'] = [label.text() for label in self.finished_labels]
        self.data[self.current_process]['update_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data[self.current_process]['change']['new_finished'] = list(self.current_changes['new_finished'])
        self.data[self.current_process]['change']['new_unfinished'] = list(self.current_changes['new_unfinished'])

        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        self.initial_states[self.current_process] = {
            'unfinished': set(self.data[self.current_process]['unfinished']),
            'finished': set(self.data[self.current_process]['finished'])
        }

        # 检查钉钉机器人是否开启并发送消息
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if config.get('dingtalk_bot') == '开启':
                webhook_url = config.get('webhook_url', '')
                secret = config.get('secret', '')
                if webhook_url and secret:
                    at_name = self.data[self.current_process]['info'].get('at_name', []) if self.current_process else []
                    thread = DingTalkThread(
                        webhook_url=webhook_url,
                        secret=secret,
                        process_name=self.current_process or "无项目",
                        at_name=at_name,
                        new_finished=self.current_changes['new_finished'],
                        new_unfinished=self.current_changes['new_unfinished'],
                        finished=self.data[self.current_process]['finished'] if self.current_process else [],
                        unfinished=self.data[self.current_process]['unfinished'] if self.current_process else []
                    )
                    thread.start()
        except Exception as e:
            print(f"Failed to start DingTalk thread: {str(e)}")

        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}

    def closeEvent(self, event):
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process if self.current_process else "无项目"} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def setup_scroll_areas(self):
        self.unfinished_widget = QWidget()
        self.finished_widget = QWidget()
        self.unfinished_layout = QGridLayout()
        self.finished_layout = QGridLayout()
        self.unfinished_widget.setLayout(self.unfinished_layout)
        self.finished_widget.setLayout(self.finished_layout)

        self.scrollArea.setWidget(self.unfinished_widget)
        self.scrollArea_2.setWidget(self.finished_widget)

        self.unfinished_labels = []
        self.finished_labels = []

        for item in self.data[self.current_process]['unfinished']:
            self.add_label(item, False)

        for item in self.data[self.current_process]['finished']:
            self.add_label(item, True)

        self.update_layouts()

    def setup_scroll_areas_empty(self):
        """设置空的滚动区域当没有项目时"""
        self.unfinished_widget = QWidget()
        self.finished_widget = QWidget()
        self.unfinished_layout = QGridLayout()
        self.finished_layout = QGridLayout()
        self.unfinished_widget.setLayout(self.unfinished_layout)
        self.finished_widget.setLayout(self.finished_layout)

        self.scrollArea.setWidget(self.unfinished_widget)
        self.scrollArea_2.setWidget(self.finished_widget)

        self.unfinished_labels = []
        self.finished_labels = []

        self.update_layouts()

    def add_label(self, text, is_finished):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 设置更大的字体
        font = QFont()
        font.setPointSize(14)
        label.setFont(font)

        # 设置最小大小
        label.setMinimumSize(100, 30)

        # 应用初始样式
        self._apply_label_style(label, text, is_finished)

        label.mousePressEvent = lambda event: self.label_clicked(label)

        if is_finished:
            self.finished_labels.append(label)
        else:
            self.unfinished_labels.append(label)

    def _apply_label_style(self, label, text, is_finished):
        """根据完成状态和current_changes应用样式的帮助程序."""
        if is_finished and text in self.current_changes['new_finished']:
            label.setStyleSheet(
                "background-color: rgba(0, 255, 0, 0.2); "
                "border: 1px solid rgb(0, 255, 0); "
                "padding: 5px; "
                "margin: 2px;"
            )
        elif not is_finished and text in self.current_changes['new_unfinished']:
            label.setStyleSheet(
                "background-color: rgba(255, 255, 0, 0.2); "
                "border: 1px solid rgb(255, 255, 0); "
                "padding: 5px; "
                "margin: 2px;"
            )
        else:
            label.setStyleSheet(
                "border: 1px solid rgb(128, 128, 128); "
                "padding: 5px; "
                "margin: 2px;"
            )

    def label_clicked(self, label):
        text = label.text()
        is_finished = label in self.finished_labels
        if not is_finished:
            self.unfinished_labels.remove(label)
            self.finished_labels.append(label)
            if text not in self.initial_states[self.current_process]['finished']:
                self.current_changes['new_finished'].add(text)
            self.current_changes['new_unfinished'].discard(text)
        else:
            self.finished_labels.remove(label)
            self.unfinished_labels.append(label)
            if text not in self.initial_states[self.current_process]['unfinished']:
                self.current_changes['new_unfinished'].add(text)
            self.current_changes['new_finished'].discard(text)

        # 立即更新标签样式
        self._apply_label_style(label, text, not is_finished)

        self.update_layouts()

    def update_layouts(self):
        for i in reversed(range(self.unfinished_layout.count())):
            self.unfinished_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.finished_layout.count())):
            self.finished_layout.itemAt(i).widget().setParent(None)

        cols = 5
        for i, label in enumerate(self.unfinished_labels):
            row = i // cols
            col = i % cols
            self.unfinished_layout.addWidget(label, row, col)

        for i, label in enumerate(self.finished_labels):
            row = i // cols
            col = i % cols
            self.finished_layout.addWidget(label, row, col)

    def open_about_dialog(self):
        """打开关于窗口"""
        dialog = AboutDialog(self)
        dialog.exec()

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/about.ui', self)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())