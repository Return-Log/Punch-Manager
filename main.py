import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QGridLayout,
                             QWidget, QScrollArea, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
from setting import SettingDialog
from new_process import NewProcessDialog
from process_manager import ProcessManagerDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('./ui/mainwindow.ui', self)

        # 加载数据
        self.data_file = './data/process.json'
        self.load_data()

        # 当前项目
        self.current_process = self.get_latest_process()

        # 本次运行的更改
        self.current_changes = {
            'new_finished': set(),
            'new_unfinished': set()
        }

        # 初始化布局
        self.setup_scroll_areas()

        # 设置项目菜单
        self.setup_process_menu()

        # 连接动作
        self.action1.triggered.connect(self.open_setting_dialog)
        self.action1_3.triggered.connect(self.open_new_process_dialog)
        self.action1_4.triggered.connect(self.open_process_manager_dialog)

        # 更新 label_3 显示当前项目
        self.label_3.setText(self.current_process)

    def open_setting_dialog(self):
        """打开设置窗口前检查保存"""
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process} 有未保存的更改，是否保存？',
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
                self, '未保存更改', f'项目 {self.current_process} 有未保存的更改，是否保存？',
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
                self, '未保存更改', f'项目 {self.current_process} 有未保存的更改，是否保存？',
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
        if self.current_process not in self.data or self.data[self.current_process]['info']['mode'] != 'on':
            self.current_process = self.get_latest_process()
        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}
        self.setup_process_menu()
        self.label_3.setText(self.current_process)
        self.setup_scroll_areas()

    def load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {
                "process_1": {
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
        return latest_process or list(self.data.keys())[0]

    def setup_process_menu(self):
        """清空 menu_2 后重新添加 action1_3, action1_4 和 mode: on 的项目"""
        self.menu_2.clear()
        # 重新添加静态动作
        self.menu_2.addAction(self.action1_3)
        self.menu_2.addAction(self.action1_4)
        # 添加动态项目动作
        for process in self.data:
            if self.data[process]['info']['mode'] == 'on':
                action = self.menu_2.addAction(process)
                action.triggered.connect(lambda checked, p=process: self.switch_process(p))

    def switch_process(self, process):
        if process == self.current_process:
            return

        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process} 有未保存的更改，是否保存？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_data()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.current_process = process
        self.label_3.setText(process)
        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}
        self.setup_scroll_areas()

    def save_data(self):
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

        self.current_changes = {'new_finished': set(), 'new_unfinished': set()}

    def closeEvent(self, event):
        if self.current_changes['new_finished'] or self.current_changes['new_unfinished']:
            reply = QMessageBox.question(
                self, '未保存更改', f'项目 {self.current_process} 有未保存的更改，是否保存？',
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

    def add_label(self, text, is_finished):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("border: 1px solid gray; padding: 5px; margin: 2px;")
        label.setMinimumSize(100, 30)
        label.mousePressEvent = lambda event: self.label_clicked(label)

        if is_finished:
            self.finished_labels.append(label)
        else:
            self.unfinished_labels.append(label)

    def label_clicked(self, label):
        text = label.text()
        if label in self.unfinished_labels:
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

        self.update_layouts()

    def update_layouts(self):
        for i in reversed(range(self.unfinished_layout.count())):
            self.unfinished_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.finished_layout.count())):
            self.finished_layout.itemAt(i).widget().setParent(None)

        cols = 3
        for i, label in enumerate(self.unfinished_labels):
            row = i // cols
            col = i % cols
            self.unfinished_layout.addWidget(label, row, col)

        for i, label in enumerate(self.finished_labels):
            row = i // cols
            col = i % cols
            self.finished_layout.addWidget(label, row, col)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())