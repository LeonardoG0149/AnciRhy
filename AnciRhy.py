import colorsys
import os
import sys
import re
import threading
import time
from collections import defaultdict
from random import choice
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QLabel, QPushButton,
                             QGridLayout, QHBoxLayout, QMessageBox,
                             QLineEdit, QFrame, QSizePolicy, QScrollArea, QTableWidgetItem, QTableWidget, QHeaderView,
                             QProgressDialog, QInputDialog, QToolTip, QTextEdit, QCheckBox, QRadioButton)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QSharedMemory, QSystemSemaphore, QSize, QEvent, QTimer, QCoreApplication
import sqlite3

from PyQt5.uic.properties import QtCore

shanggushengipa_select = ""
zhonggushengchar_select = ""
shangguyunchar_select = ""
zhongguyunchar_select = ""


# 创建数据库连接函数————————————————————————————————————————————————————————
def create_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ancienttest.db')
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row  # 让结果集支持列名访问
    return connection


# 圖標設置
def set_window_icon(self, icon_filename='icon.ico'):
    """设置窗口图标，根据程序是否打包判断图标路径"""
    # 检查程序是否在打包环境中运行
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本的目录

    # 使用相对路径查找图标文件
    icon_path = os.path.join(base_dir, icon_filename)

    # 设置窗口图标
    self.setWindowIcon(QIcon(icon_path))


# 單個實例檢測
class SingleInstanceApplication:
    def __init__(self, key):
        self.key = key
        self.shared_memory = QSharedMemory(self.key)
        self.semaphore = QSystemSemaphore(self.key + "_sem", 1)

    def is_running(self):
        """检查是否已有实例在运行"""
        self.semaphore.acquire()
        if not self.shared_memory.attach():
            self.shared_memory.create(1)
            self.semaphore.release()
            return False
        else:
            self.semaphore.release()
            return True

    def activate_existing_instance(self):
        """显示正在运行的主窗口"""
        # 弹出警告提示用户程序已在运行
        QMessageBox.warning(None, "警告", "程序已在运行！")
        self.shared_memory.lock()
        self.shared_memory.data()[0] = b'1'  # 向共享内存中写入一个标志，表示要激活窗口
        self.shared_memory.unlock()


# 主页面___________________________________________________________________
class MainWindow(QMainWindow):
    def show_and_raise(self):
        """显示窗口并将其置于前台"""
        self.show()
        self.raise_()  # 将窗口置于其他窗口之上
        self.activateWindow()  # 激活窗口，确保其在前台

    def __init__(self):
        super().__init__()
        # 初始化数据库连接
        self.conn = create_db_connection()
        self.cursor = self.conn.cursor()  # 创建游标对象
        self.search_window = None  # 初始化为空
        self.is_waiting_for_column_choice = False  # 标志位，用来跟踪是否等待用户选择列
        self.pending_character = None  # 用于存储待查询的字符
        self.confirmed_character = None  # 新增：用于存储用户确认的字符

        # 设置窗口标题和大小
        self.setWindowTitle("賢哉古音 - 首頁")
        self.setGeometry(100, 100, 1700, 1000)
        self.setMinimumSize(1600, 900)

        # 设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 创建主部件和垂直布局
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()  # 使用 QVBoxLayout
        main_widget.setLayout(layout)

        # 设置布局的外边距与间距
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)  # 组件之间的间距

        # 标题标签：
        query_label = QLabel("賢 哉 古 音")
        query_label.setFont(QFont("康熙字典體", 64))
        query_label.setStyleSheet(
            """
            QLabel {
                color: #8B2500;
                border: 2px solid #A0522D;  
                border-radius: 15px;
                padding: 16px;
                background: qlineargradient(
                    spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #FFEBD2 , stop: 1 #F2EFEC );  /* 米黄色到象牙色的渐变 */
            }
            """)
        query_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(query_label)  # 添加标题到垂直布局

        # 创建按钮
        buttons_texts = ["查字", "查上古音·声母", "查中古音·声母", "查上古音·韵部", "查中古音·韵部"]
        button_fonts = QFont("Aa古典刻本宋", 17)
        button_colors = ["#CA6503", "#3C0D00", "#3C0D00", "#8E4A37", "#8E4A37"]
        button_commands = [self.open_search_chara_window,
                           self.open_shanggusheng_window,
                           self.open_zhonggusheng_window,
                           self.open_shangguyun_window,
                           self.open_zhongguyun_window]

        # 创建按钮容器布局（QHBoxLayout）放置按钮，使用柔和的色调
        button_layout = QHBoxLayout()  # 使用水平布局放置按钮
        for text, color, command in zip(buttons_texts, button_colors, button_commands):
            button = QPushButton(text)
            button.setFont(button_fonts)
            button.setStyleSheet(f"""
                QPushButton {{
                    color: {color}; padding: 20px 5px;
                }}
                QPushButton:hover {{
                    font-weight: bold;
                }}
            """)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(command)
            button_layout.addWidget(button)  # 将按钮添加到水平布局

        layout.addLayout(button_layout)  # 将按钮水平布局添加到主垂直布局

        bottom_layout = QHBoxLayout()

        # 更新日志按钮样式优化
        log_button = QPushButton("v 1.3.5  更新日志")
        log_button.setStyleSheet("""
           QPushButton {
               color: #B22222;  /* 不饱和的红色 */
               background-color: transparent;
               border: none;
               text-decoration: underline;
               padding: 5px;
           }
           QPushButton:hover {
               color: #0072F0;           
           }
       """)
        log_button.setFont(QFont("Aa古典刻本宋", 12))
        log_button.setCursor(Qt.PointingHandCursor)
        log_button.clicked.connect(self.open_update_log_window)
        bottom_layout.addWidget(log_button, alignment=Qt.AlignLeft | Qt.AlignBottom)  # 将更新日志按钮添加到垂直布局

        # 创建帮助 bot 的按钮，带机器人图标__________________________________
        self.bot_button = QPushButton(self)
        self.bot_button.setIcon(QIcon(self.resource_path('bot.png')))  # 设置小机器人图标
        self.bot_button.setIconSize(QSize(94, 94))  # 设置图标的大小
        self.bot_button.setFixedSize(110, 110)  # 设置按钮大小
        self.bot_button.setCursor(Qt.PointingHandCursor)

        # 设置按钮样式，去除边框
        self.bot_button.setStyleSheet("""
            QPushButton {
                border: none;  /* 去掉按钮边框 */
                background-color: transparent;  /* 背景透明 */
            }
            QPushButton:hover {
                background-color: transparent;  /* 悬停时背景也保持透明 */
            }
        """)

        # 添加眨眼效果
        self.bot_icon_default = QIcon(self.resource_path('bot.png'))  # 默认睁眼图标
        self.bot_icon_blink = QIcon(self.resource_path('bot3.png'))  # 闭眼图标
        self.bot_icon_hover = QIcon(self.resource_path('bot2.png'))  # 懸停樣式

        # 计时器用于眨眼效果
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_bot_icon)
        self.blink_timer.start(2400)  # 每2.4秒触发一次

        # 计时器用于眨眼结束
        self.blink_end_timer = QTimer(self)
        self.blink_end_timer.setSingleShot(True)
        self.blink_end_timer.timeout.connect(self.reset_bot_icon)

        # 悬停效果：鼠标进入和离开事件处理
        self.bot_button.installEventFilter(self)
        self.bot_button.clicked.connect(self.open_bot_dialog)  # 点击按钮打开 bot 对话框

        # 设置按钮的悬停提示
        self.bot_button.setToolTip("有问题？请告诉我")  # 悬停时显示的浮窗提示
        QToolTip.setFont(QFont('Aa古典刻本宋', 16))  # 设置提示的字体和大小

        # 将机器人按钮放在右下角
        bottom_layout.addWidget(self.bot_button, alignment=Qt.AlignBottom | Qt.AlignRight)
        layout.addLayout(bottom_layout)

    def open_search_chara_window(self):
        print("打开查字窗口")
        if self.search_window is None:
            self.search_window = SearchCharaWindow()

            # 设置输入框内容为已确认的字符
        if self.confirmed_character:
            self.search_window.search_chara_entry.setText(self.confirmed_character)
            self.search_window.search_chara_entry.returnPressed.emit()  # 模拟按下回车键
        self.search_window.show()

    def open_shanggusheng_window(self):
        print("打開上古聲母窗口")
        self.shanggusheng_window = ShanggushengWindow()
        self.shanggusheng_window.show()

    def open_zhonggusheng_window(self):
        print("打開中古聲母")
        self.zhonggusheng_window = ZhonggushengWindow()
        self.zhonggusheng_window.show()

    def open_shangguyun_window(self):
        print("打開上古韻母")
        self.shangguyun_window = ShangguyunWindow()
        self.shangguyun_window.show()

    def open_zhongguyun_window(self):
        print("打開中古韻母")
        self.zhongguyun_window = ZhongguyunWindow()
        self.zhongguyun_window.show()

    # 打开更新日志窗口的函数
    def open_update_log_window(self):
        self.update_log_window = UpdateLogWindow()
        self.update_log_window.show()

    def blink_bot_icon(self):
        """切换为闭眼图标"""
        if not self.bot_button.underMouse():  # 只有在鼠标不悬停时才眨眼
            self.bot_button.setIcon(self.bot_icon_blink)
            self.blink_end_timer.start(300)  # 300毫秒后切换回默认睁眼图标

    def reset_bot_icon(self):
        """恢复为睁眼图标"""
        self.bot_button.setIcon(self.bot_icon_default)

    def eventFilter(self, obj, event):
        """监测鼠标悬停事件并动态更改图标和大小"""
        if hasattr(self, 'bot_button') and obj == self.bot_button:
            if event.type() == QEvent.Enter:  # 鼠标进入
                self.blink_timer.stop()  # 停止眨眼
                self.is_hovering = True  # 标记鼠标悬停状态
                obj.setIcon(self.bot_icon_hover)
                obj.setIconSize(QSize(110, 110))  # 更改图标大小
            elif event.type() == QEvent.Leave:  # 鼠标离开
                self.is_hovering = False  # 取消悬停状态
                obj.setIcon(self.bot_icon_default)
                obj.setIconSize(QSize(94, 94))  # 恢复原始大小
                self.blink_timer.start(2400)  # 鼠标离开后重新启动眨眼计时器
        return super().eventFilter(obj, event)

    def resource_path(self, relative_path):
        """获取资源文件的绝对路径"""
        # PyInstaller 创建临时文件夹，并在临时文件夹中存放资源文件
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def open_bot_dialog(self):  # ————————————————————————————
        """创建一个 Telegram 样式的聊天窗口"""
        self.bot_chat_window = QMainWindow(self)
        # 重写关闭事件，重置变量
        self.bot_chat_window.closeEvent = self.reset_variables_on_close
        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'bot.png')
        # 单独为子窗口设置图标，而不是调用全局的 set_window_icon
        self.bot_chat_window.setWindowIcon(QIcon(icon_path))

        self.bot_chat_window.setWindowTitle("賢哉Bot")
        self.bot_chat_window.setGeometry(400, 200, 600, 900)
        self.bot_chat_window.setFixedSize(600, 900)

        # 创建主部件和布局
        central_widget = QWidget(self.bot_chat_window)
        layout = QVBoxLayout(central_widget)

        # 聊天记录显示区域（使用 ScrollArea）
        scroll_area = QScrollArea(self.bot_chat_window)
        scroll_area.setWidgetResizable(True)
        self.chat_display_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_display_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)  # 设置消息之间的间距
        self.chat_layout.setContentsMargins(10, 10, 10, 10)  # 设置布局的边距
        scroll_area.setWidget(self.chat_display_widget)

        # 将聊天记录区域加入布局
        layout.addWidget(scroll_area)

        # 输入框和发送按钮的布局
        input_layout = QHBoxLayout()

        # 用户输入框
        self.input_field = QLineEdit(self.bot_chat_window)
        self.input_field.setFont(QFont("等线", 14))
        self.input_field.setPlaceholderText("簡述您的疑問...")
        self.input_field.setStyleSheet("padding: 10px; "
                                       "border-radius: 15px; "
                                       "border: 1px solid #0088CC;")

        # 将 Enter 键绑定到发送消息功能
        self.input_field.returnPressed.connect(self.send_message)

        # 发送按钮
        send_button = QPushButton("發送", self.bot_chat_window)
        send_button.setFont(QFont("Aa古典刻本宋", 14))

        send_button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #0088CC;
                            color: white; 
                            padding: 10px;
                            border-radius: 15px; 
                            margin-left: 10px;
                        }}
                        QPushButton:hover {{
                    font-weight: bold;
                    background-color: #0077BB;
                }}
        """)
        send_button.setCursor(Qt.PointingHandCursor)
        send_button.clicked.connect(self.send_message)

        # 将输入框和按钮添加到输入布局
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_button)

        # 将输入布局加入主布局
        layout.addLayout(input_layout)

        # 确保输入框获取焦点
        self.input_field.setFocus()  # 让输入框获取焦点，光标开始闪烁

        # 让 bot 先发送一条消息
        self.add_message("賢哉Bot", "我是賢哉Bot，請隨時向我提問。輸入help以獲取幫助", is_user=False)

        # 设置主部件和布局
        self.bot_chat_window.setCentralWidget(central_widget)
        self.bot_chat_window.show()

    def reset_variables_on_close(self, event):
        """当聊天窗口关闭时重置变量"""
        self.is_waiting_for_column_choice = False
        self.pending_character = None
        event.accept()  # 确保窗口正常关闭
        print("bot窗口將關閉……")

    def send_message(self):
        """发送用户输入的消息，并模拟 bot 回复"""
        user_input = self.input_field.text().strip()

        if user_input:
            # 显示用户的消息
            self.add_message("您", user_input, is_user=True)
            self.input_field.clear()

            # 使用 QTimer 在 200ms 后调用 bot 的回复
            QTimer.singleShot(200, lambda: self.bot_reply(user_input))

    def bot_reply(self, user_input):
        """模拟 bot 的回应"""
        response = self.handle_bot_response(user_input)
        if response:  # 如果 response 不为 None，才添加消息
            self.add_message("賢哉Bot", response, is_user=False)

        QCoreApplication.processEvents()  # 强制处理UI事件，以确保新消息框架已被添加

        # 模拟滚轮操作，将滚动条滚动到最底部
        scroll_area = self.bot_chat_window.findChild(QScrollArea)
        scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum())

        # 发送消息后重新设置焦点到输入框
        self.input_field.setFocus()  # 确保焦点保持在输入框

    def add_message(self, sender, message, is_user=False):
        """添加一条气泡消息到聊天窗口"""
        # 创建消息容器
        message_frame = QFrame(self.bot_chat_window)
        message_layout = QHBoxLayout(message_frame)

        # 用户和 bot 的消息排版不同
        if is_user:
            # 用户头像
            user_label = QLabel(self.bot_chat_window)
            user_label.setFixedSize(40, 40)
            user_label.setStyleSheet("""
                QLabel {
                    background-color: #0088CC;
                    color: white;
                    border-radius: 22px;  /* 圆形半徑 */
                    min-width: 44px;  /* 圆圈的宽度 */
                    min-height: 44px;  /* 圆圈的高度 */
                    font-size: 30px;
                    text-align: center;
                    font-family: "Aa古典刻本宋";
                }
            """)
            user_label.setAlignment(Qt.AlignCenter)
            user_label.setText("您")

            # 用户消息气泡
            message_bubble = QLabel(message, self.bot_chat_window)
            message_bubble.setFont(QFont("等线", 14))
            message_bubble.setStyleSheet("""
                QLabel {
                    background-color: #DCF8C6;
                    padding: 10px;
                    border-radius: 10px;
                    max-width: 550px;
                    border: 1px solid #C0C0C0;
                    word-wrap: break-word; 
                }
            """)
            message_bubble.setWordWrap(True)
            message_bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
            message_bubble.adjustSize()  # 调整大小以适应文本内容
            # 添加到布局（右侧）
            message_layout.addStretch()
            message_layout.addWidget(message_bubble)
            message_layout.addWidget(user_label)

        else:
            # Bot 头像
            bot_avatar = QLabel(self.bot_chat_window)
            bot_avatar.setPixmap(
                QPixmap(self.resource_path("bot.png")).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # Bot 消息气泡
            message_bubble = QLabel(message, self.bot_chat_window)
            message_bubble.setFont(QFont("等线", 14))
            message_bubble.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    padding: 10px;
                    border-radius: 10px;
                    max-width: 650px;
                    word-wrap: break-word;  /* 自动换行 */
                    border: 1px solid #C0C0C0;
                }
            """)
            message_bubble.setWordWrap(True)

            # 设置尺寸策略，确保 QLabel 可以根据内容自动扩展
            message_bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
            message_bubble.adjustSize()  # 调整大小以适应文本内容
            # 添加到布局（左侧）
            message_layout.addWidget(bot_avatar)
            message_layout.addWidget(message_bubble)
            message_layout.addStretch()

        # 将消息添加到聊天记录区域
        self.chat_layout.addWidget(message_frame)

        # 强制更新布局和父容器的大小
        message_frame.adjustSize()
        self.chat_display_widget.adjustSize()
        # 强制刷新 UI
        QCoreApplication.processEvents()

        # 判断是否是 bot 消息，只有 bot 的消息才会自动滚动到底部
        if not is_user:
            # 强制处理UI事件，以确保新消息框架已被添加
            QCoreApplication.processEvents()

            # 自动滚动到底部
            scroll_area = self.bot_chat_window.findChild(QScrollArea)
            scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum())

    def handle_bot_response(self, user_input):
        """根据用户输入模拟 bot 的回应"""

        if user_input.lower() == "取消":
            # 如果用户输入“取消”，重置状态并停止当前查询
            self.is_waiting_for_column_choice = False
            self.pending_character = None
            return "已取消当前查询。"

        if self.is_waiting_for_column_choice:
            # 如果正在等待用户选择列
            return self.handle_column_choice(user_input)
        elif re.fullmatch(r'^.$', user_input):  # 如果输入是单个字符
            return self.process_character_query(user_input)
        elif "谢谢" in user_input or "謝謝" in user_input:
            return "不必客气 ;-)"
        elif "help" in user_input:
            return "可以直接輸入韻部、聲母、單個字。例如“東”，輸入后根據bot提示選擇查字、聲母或韻部"
        else:
            return "我不太明白。如有需要，可以使用主頁的功能按鈕查找各類音韻信息。"

    def process_character_query(self, character):
        """处理字符查询逻辑"""

        #检查字符是否出现在上古韻、中古聲、中古韻列中
        columns_to_check = ["上古韻", "中古聲", "中古韻"]
        results = {}

        for column in columns_to_check:
            self.cursor.execute(f"SELECT COUNT(*) FROM ancienttesttable1 WHERE {column}=?", (character,))
            count = self.cursor.fetchone()[0]
            if count > 0:
                results[column] = count

        if results:
            response = f"'{character}'可能是 單字字頭 或：\n"
            for column, count in results.items():
                response += f"-{column}（{count} 個歸屬字）\n"
            response += "選擇要查的内容\n(輸入列名,如'中古聲',或'字頭')"
            self.is_waiting_for_column_choice = True  # 设置标志位，等待用户选择列
            self.pending_character = character  # 保存字符
            return response
        else:
            # 直接查询字头信息
            return self.query_character_info(character)

    def handle_column_choice(self, user_input):
        """处理用户选择的列"""
        if user_input in ["上古韻", "中古聲", "中古韻"]:
            # 查询指定列的值
            values = self.query_column_values(user_input, self.pending_character)
            response = f"所有 '{user_input}' 為 '{self.pending_character}' 的字頭：\n"
            for row in values:
                response += f"{row[0]}\n"
            self.is_waiting_for_column_choice = False  # 重置标志位
            return response
        elif user_input == "字頭":
            # 查询字头信息
            self.is_waiting_for_column_choice = False  # 重置标志位
            return self.query_character_info(self.pending_character)
        else:
            return "輸入無效\n請輸列名(如'中古聲'或'字頭')\n輸入“取消”以停止當前查詢"

    def query_column_values(self, column, value):
        """查询指定列的值"""
        self.cursor.execute(f"SELECT 字頭 FROM ancienttesttable1 WHERE {column}=?", (value,))
        return self.cursor.fetchall()

    def query_character_info(self, character):
        """查询字头信息"""
        self.cursor.execute("SELECT * FROM ancienttesttable1 WHERE 字頭=?", (character,))
        results = self.cursor.fetchall()  # 获取所有结果
        result_count = len(results)  # 结果数量

        if result_count == 0:
            return f"未找到'{character}'字的信息。"
        elif result_count == 1:
            result_strings = []  # 用来存储每一条数据对应的结果字符串
            for result in results:
                # 假设表中有9列数据
                col1, col2, col3, col4, col5, col6, col7, col8, col9 = result

                # 构建单条结果的字符串
                result_string = (
                    f"“{col2}”是上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。"
                )
                result_strings.append(result_string)
            # 将所有结果字符串拼接在一起，用换行分隔
            return "\n".join(result_strings)
        else:
            # 如果有多条结果（多音字），依次显示每个读音的详细信息
            for i, result in enumerate(results, start=1):
                # 假设表中有9列数据
                col1, col2, col3, col4, col5, col6, col7, col8, col9 = result
                result_string_1 = (
                    f"“{col2}”是上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。"
                )
                result_string_i = (
                    f"上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。"
                )
                if i == 1:
                    response = f"第 {i} 个读音：\n{result_string_1}"
                else:
                    response = f"第 {i} 个读音：\n{result_string_i}"
                self.add_message("賢哉Bot", response, is_user=False)
            return None  # 返回 None，避免重复添加消息


# 查中古韻母窗口——————————————————————————————————————————————————————————————————————————————
class ZhongguyunWindow(QWidget):
    zhongguyun_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查中古音·韻部")
        self.setGeometry(200, 100, 1900, 1300)
        self.setMinimumSize(1400, 1100)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.initUI()

        # 连接信号到表格更新的槽函数
        self.zhongguyun_loaded_signal.connect(self.update_table)

    def initUI(self):
        # 创建主布局
        self.main_layout = QHBoxLayout(self)

        global zhongguyunchar_select

        # 1. L半部分 - 放置按钮
        button_frame = QFrame(self)
        button_frame.setFixedWidth(630)
        button_layout = QGridLayout(button_frame)

        # 设置按钮之间的间距
        button_layout.setHorizontalSpacing(20)  # 设置按钮左右之间的间距
        button_layout.setVerticalSpacing(20)  # 设置按钮上下之间的间距

        self.selected_button = None
        # 字符列表
        zhongguyunchars = ["東", "屋", "冬", "沃", "鍾", "燭", "江", "覺", "支", "脂",
                           "之", "微", "魚", "虞", "模", "齊", "祭", "泰",
                           "佳", "皆", "夬", "灰", "咍", "廢", "真", "質", "臻", "櫛",
                           "文", "物", "殷", "迄", "元", "月", "魂", "沒", "痕", "寒", "曷", "删", "黠", "山", "鎋",
                           "先", "屑", "仙", "薛", "蕭", "宵", "肴", "豪", "歌", "麻",
                           "陽", "藥", "唐", "鐸", "庚", "陌", "耕", "麥", "清", "昔", "青", "錫", "蒸", "職", "登",
                           "德",
                           "尤", "侯", "幽", "侵", "緝", "覃", "合", "談", "盍", "鹽", "葉", "添", "帖",
                           "咸", "洽", "銜", "狎", "嚴", "業", "凡", "乏", "以韻圖顯示結果"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for zhongguyunchar in zhongguyunchars:
            button = QPushButton(zhongguyunchar, self)

            if zhongguyunchar == "以韻圖顯示結果":
                # 设置“以韻圖顯示結果”按钮的字体为16号
                button.setFont(QFont("康熙字典體", 16))
                # 设置按钮尺寸
                button.setFixedSize(305, 70)  # 使其更大以适应较长的文字
                # 绑定打开新窗口的点击事件
                button.clicked.connect(self.showTable_window)
                # 设置按钮文字颜色
                button.setStyleSheet("color: #CD5555;")  # 改变文字颜色
                button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标

            else:
                # 设置其他按钮的字体为18号
                button.setFont(QFont("康熙字典體", 18))
                # 设置按钮为方形
                button.setFixedSize(70, 70)  # 宽度和高度相同，方形按钮
                # 绑定正常的点击事件
                button.clicked.connect(self.create_click_handler(button, zhongguyunchar))
                # 设置按钮文字颜色
                button.setStyleSheet("color: #540A03;")  # 改变文字颜色
                button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标
            # 将按钮添加到布局
            button_layout.addWidget(button, row, column)
            # 列数加一
            column += 1
            if column == 8:
                row += 1
                column = 0  # 新行从第 0 列开始

        # 将按钮布局放入主布局
        self.main_layout.addWidget(button_frame)

        # 2. 中间部分 __________________

        # 创建表格布局
        self.table_layout = QGridLayout()
        self.main_layout.addSpacing(2)

        # 创建 QScrollArea 嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)
        scroll_area.setWidget(scroll_widget)

        # 将 QScrollArea 添加到主布局
        self.main_layout.addWidget(scroll_area)

        # 设置主窗口的布局
        self.setLayout(self.main_layout)

    def create_click_handler(self, button, zhongguyunchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_zhongguyun_click(button, zhongguyunchar)

    def on_zhongguyun_click(self, button, zhongguyunchar):
        print("点击的中古韵母：", zhongguyunchar)

        # 如果之前有选中的按钮，将其恢复默认颜色
        if self.selected_button:
            self.selected_button.setStyleSheet("color: #540A03")

        if zhongguyunchar != "以韻圖顯示結果":
            # 设置当前点击的按钮颜色，并记录该按钮为选中按钮
            button.setStyleSheet("background-color: #8B2323;"
                                 "color: #F5F5F5;"
                                 "border-radius: 5px;")  # 设置选中按钮的背景颜色、圓角、邊框
            self.selected_button = button  # 更新为当前选中的按钮

            global zhongguyunchar_select
            zhongguyunchar_select = zhongguyunchar

        # 启动后台线程加载数据
        threading.Thread(target=self.load_data, args=(zhongguyunchar,)).start()

    def load_data(self, zhongguyunchar):
        try:
            # 创建数据库连接
            connection = create_db_connection()

            # 使用 sqlite3 的游标
            cursor = connection.cursor()

            # 查询
            sql = """
                        SELECT 字頭, 上古韻, 中古等
                        FROM ancienttesttable1
                        WHERE 中古韻 = ?
                    """
            cursor.execute(sql, (zhongguyunchar,))
            result = cursor.fetchall()

            # 将结果从元组转换为字典，支持列名访问
            # grouped_data 用来按上古韻分组
            grouped_data = defaultdict(list)
            for row in result:
                grouped_data[row['上古韻']].append(row['字頭'])

            # 将 defaultdict 转换为标准的 list 类型，例如字典的列表
            grouped_data_list = [{"上古韻": key, "字頭": value} for key, value in grouped_data.items()]

            # 发射信号，将数据传递到主线程
            self.zhongguyun_loaded_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")
        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭

    def update_table(self, data):
        # 清空现有表格内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 表头
        header1 = QLabel("上古所屬韻部")
        header1.setFont(QFont("康熙字典體", 17))
        header1.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該中古韻部的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header2.setAlignment(Qt.AlignCenter)
        header2.setFixedHeight(80)

        # 添加表头
        self.table_layout.addWidget(header1, 0, 1)
        self.table_layout.addWidget(header2, 0, 0)

        # 设置布局间距
        self.table_layout.setHorizontalSpacing(0)
        self.table_layout.setVerticalSpacing(0)
        self.table_layout.setContentsMargins(0, 0, 0, 0)

        # 设置列宽比例
        self.table_layout.setColumnStretch(0, 5)  # 中古声列
        self.table_layout.setColumnStretch(1, 1)  # 上古字头列

        # 填充数据
        for row_num, row_data in enumerate(data):
            # 中古音列
            zhongguyun_label = QLabel(row_data["上古韻"])
            zhongguyun_label.setStyleSheet(
                "border: 1px solid brown; padding: 10px; color: #CD3700; background-color: #EEE5DE;")
            zhongguyun_label.setFont(QFont("康熙字典體", 26))
            zhongguyun_label.setAlignment(Qt.AlignCenter)
            zhongguyun_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zhongguyun_label, row_num + 1, 1)

            # 字头列
            zitou_str = " ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown; padding: 10px;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            zitou_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)

    def showTable_window(self):
        if zhongguyunchar_select:
            self.table_window = Subtable_zhongguyun()
            self.table_window.show()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)  # 设置图标为警告
            msg.setWindowTitle("韻圖顯示-警告")  # 设置窗口标题
            msg.setText("還未選擇韻部！")  # 设置提示信息
            msg.setStandardButtons(QMessageBox.Ok)  # 设置按钮，只有一个“确定”按钮
            msg.exec_()  # 显示对话框

    def closeEvent(self, event):
        """窗口关闭时清空 zhongguyunchar_select 变量的值"""
        global zhongguyunchar_select
        if zhongguyunchar_select is not None:
            print("即將清空剛選中的中古韻：【" + zhongguyunchar_select + "】")
            zhongguyunchar_select = None  # 清空变量值
            print("窗口关闭，zhongguyunchar_select 已清空")  # 输出调试信息
        else:
            print("沒有選中任何中古韻，zhongguyunchar_select變量的值本來就是空的，不會對變量做賦空值操作！窗口要關閉啦！")
        # 允许窗口正常关闭
        event.accept()


# 定义中古韻表格视图的子窗口—————————————————————————————————
class Subtable_zhongguyun(QWidget):
    update_table_signal = pyqtSignal(list)  # 定义查询信号
    update_label_signal = pyqtSignal(str)  # 定义更新 label3图例 的信号
    update_radioboxes_signal = pyqtSignal(list)  # 定义更新单选按钮的信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查中古音·韻部 - 韻圖顯示")
        self.setGeometry(100, 100, 1700, 1200)  # 设置窗口大小
        self.setMinimumSize(1300, 1000)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 创建主布局
        layout = QVBoxLayout()

        # 創建顯示韻部韻母的標籤
        zgySelect_layout = QHBoxLayout()
        layout.addLayout(zgySelect_layout)

        # 标签
        label = QLabel("選中的中古韻部:  " + zhongguyunchar_select)
        label.setFont(QFont("康熙字典體", 20))
        label.setStyleSheet("color: #6E2C00;  border: 1px solid brown;")
        label.setAlignment(Qt.AlignVCenter | Qt.AlignCenter)  # 将标签水平居左，垂直居中
        label.setFixedWidth(self.width() // 3)

        self.label3 = QLabel("图例")
        self.label3.setFont(QFont("IpaP", 16))
        self.label3.setStyleSheet("border: 1px solid brown;")

        zgySelect_layout.addWidget(label)
        zgySelect_layout.addWidget(self.label3)

        # 创建表格布局_____________________________
        self.table_layout = QGridLayout()
        self.table_layout.setSpacing(0)  # 设置单元格之间的间距为 0
        self.table_layout.setContentsMargins(0, 0, 0, 0)  # 设置布局的边距为 0
        layout.addSpacing(1)  # 上方空白
        # 创建 QScrollArea 并嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许自动调整子窗口大小
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)  # 将表格布局设为 QScrollArea 的子窗口
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)  # 只有 zhonggushengchar_select 有值时，才添加 scroll_area

        # 添加“可筛选的上古音韵部：”标签
        self.filter_label = QLabel("這些字來自0個上古韻部：")
        self.filter_label.setFont(QFont("康熙字典體", 16))
        self.filter_label.setStyleSheet("color: #6E2C00;")  # 设置标签的字体颜色
        self.filter_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)  # 左对齐并垂直居中
        layout.addWidget(self.filter_label)
        # 添加單選按鈕和按钮的主布局（水平布局）
        options_layout = QHBoxLayout()

        # 添加單選按鈕布局
        radiobox_layout = QHBoxLayout()  # 水平布局
        radiobox_container = QWidget()  # 用于容纳單選按鈕布局
        radiobox_container.setLayout(radiobox_layout)

        # 为整个單選按鈕容器添加边框
        radiobox_container.setStyleSheet("""
            QWidget {border: 1px solid brown; padding: 5px;}
        """)

        # 不需要預先定義標籤列表，將在查詢數據庫後動態創建
        self.radioboxes = []
        self.radiobox_layout = radiobox_layout  # 保存布局的引用以便後續添加按鈕

        # 将單選按鈕容器添加到主布局
        options_layout.addWidget(radiobox_container)

        # 添加主布局到窗口的主布局中
        layout.addLayout(options_layout)

        # 设置主窗口布局
        self.setLayout(layout)
        # 连接信号和槽
        self.update_table_signal.connect(self.update_table)
        self.update_label_signal.connect(self.update_label)
        self.update_radioboxes_signal.connect(self.update_radioboxes)

        # 开启线程查询数据库
        self.load_table_data()

    def load_table_data(self):
        """创建一个新线程去查询数据库，以避免阻塞主线程"""
        print("Loading table data...")
        threading.Thread(target=self.query_database).start()

    def apply_filter(self):
        """應用篩選功能"""
        # 獲取選中的單選按鈕
        selected_shangguyun = None
        for radiobox in self.radioboxes:
            if radiobox.isChecked():
                selected_shangguyun = radiobox.text()
                break
        print(f"選中的上古韻部: {selected_shangguyun}")  # 調試信息

        # 如果選擇了"全部"，重新加載所有數據
        if selected_shangguyun == "全部":
            self.load_table_data()
            return

        # 否則，篩選數據
        connection = None
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 查詢符合條件的數據
            sql = """
                SELECT 字頭, 上古聲, 中古聲, 上古韻, 中古調, 中古等, 開合
                FROM ancienttesttable1
                WHERE 中古韻 = ? AND 上古韻 = ?
            """
            cursor.execute(sql, (zhongguyunchar_select, selected_shangguyun))
            result = cursor.fetchall()

            print(f"查詢結果數量: {len(result)}")  # 調試信息

            if not result:  # 如果沒有查詢結果
                # 發送空列表更新表格
                self.update_table_signal.emit([])
                return

            # 獲取所有不同的上古聲
            unique_shanggusheng = set(row['上古聲'] for row in result)

            # 創建顏色映射
            color_palette = ['#0036BA', '#D84EE7', '#03DD81', '#A4AD03',
                             '#AD033A', '#7300C2', '#00B7FB', '#04552C',
                             '#770028', '#D5A600', '#FF8F00', '#FF1E00', '#000000']
            available_colors = color_palette[:]
            color_mapping = {}

            # 為每個上古聲分配顏色
            for shanggusheng in unique_shanggusheng:
                if shanggusheng not in color_mapping:
                    if available_colors:
                        color = available_colors.pop()
                        color_mapping[shanggusheng] = color
                    else:
                        color_mapping[shanggusheng] = self.random_color()

            # 更新圖例
            html_content = "<b>上古音聲母來源·图例：</b><br>"
            for shanggusheng, color in color_mapping.items():
                html_content += f'<span style="color:{color}; font-size:30px;">[{shanggusheng}]</span>  '
            self.update_label_signal.emit(html_content)

            # 將相同的"中古聲"和"中古等"進行分組
            grouped_data = defaultdict(lambda: defaultdict(list))
            for row in result:
                zhonggusheng = row['中古聲']  # 使用"中古聲"作為行
                zhonggudeng = row['中古等']  # 根據"中古等"來分類
                zhonggudiaos = row['中古調']  # 使用"中古調"決定列
                zitou = row['字頭']  # 字頭作為具體填充數據
                shanggusheng = row['上古聲']  # 上古聲
                kaihe = row['開合']

                # 字頭分類邏輯：根據"中古等"和"中古調"填入對應的列
                if zhonggudeng in ["一", "二", "三", "四", "A", "B"]:
                    deng_type = "等" if zhonggudeng in ["一", "二", "三", "四"] else "類"
                    deng_name = f"{zhonggudeng}{deng_type}"

                    if zhonggudiaos in ["平", "上", "去", "入"]:
                        kaihe_text = "開" if kaihe == "開" else "合"
                        deng = f"{deng_name}{zhonggudiaos}·{kaihe_text}"

                        # 將數據添加到分組中
                        grouped_data[zhonggusheng][deng].append({
                            "字頭": zitou,
                            "上古聲": shanggusheng,
                            "color": color_mapping[shanggusheng]
                        })

            # 轉換為列表形式
            grouped_data_list = []
            for zhonggusheng, deng_dict in grouped_data.items():
                for deng, zitou_list in deng_dict.items():
                    grouped_data_list.append({
                        "中古聲": zhonggusheng,
                        "中古等": deng,
                        "字頭": zitou_list
                    })

            print(f"處理後的數據數量: {len(grouped_data_list)}")  # 調試信息
            # 更新表格
            self.update_table_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"篩選數據時出錯: {e}")
        finally:
            if connection:
                connection.close()

    def reset_filter(self):
        """重置篩選"""
        # 選中"全部"單選按鈕
        for radiobox in self.radioboxes:
            if radiobox.text() == "全部":
                radiobox.setChecked(True)
                break

        # 重新加載所有數據
        self.load_table_data()

    def random_color(self):
        """生成一个随机颜色，确保不为白色"""
        # 定义要排除的颜色列表
        excluded_colors = ['#ffffff', '#0036BA', '#D84EE7', '#03DD81', '#A4AD03',
                           '#AD033A', '#7300C2', '#00B7FB', '#04552C',
                           '#770028', '#D5A600', '#FF8F00', '#FF1E00', '#000000']
        while True:
            h = random.random()  # 生成随机色调 [0, 1]
            s = 0.7  # 饱和度 [0, 1]
            l = 0.5  # 亮度 [0, 1]

            # 转换 HSL 到 RGB
            rgb = colorsys.hls_to_rgb(h, l, s)
            # 将 RGB 值转换为十六进制颜色值
            color = '#{:02x}{:02x}{:02x}'.format(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            # 如果颜色在排除的颜色列表中，继续生成新的颜色
            if color not in excluded_colors:
                return color

    def query_database(self):
        """查询数据库以获取匹配中古韻的结果"""
        connection = None
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 查询所有该声母的字头和中古声
            sql = """
                    SELECT 字頭, 上古聲, 中古聲, 上古韻, 中古調, 中古等, 開合
                    FROM ancienttesttable1
                    WHERE 中古韻 = ?
                """
            cursor.execute(sql, (zhongguyunchar_select,))
            result = cursor.fetchall()

            # 獲取所有不同的上古韻
            unique_shangguyun = set(row['上古韻'] for row in result)
            unique_shangguyun_count = len(unique_shangguyun)
            print('上古韻有：' + str(unique_shangguyun))

            # 發送信號更新單選按鈕
            self.update_radioboxes_signal.emit(list(unique_shangguyun))

            # 获取所有不同的上古声
            unique_shanggusheng = set(row['上古聲'] for row in result)
            unique_shanggusheng_count = len(unique_shanggusheng)

            # 创建颜色列表，用于随机选择
            color_palette = ['#0036BA', '#D84EE7', '#03DD81', '#A4AD03',
                             '#AD033A', '#7300C2', '#00B7FB', '#04552C',
                             '#770028', '#D5A600', '#FF8F00', '#FF1E00', '#000000']
            # 可用的颜色列表，每次从这里选择，并确保颜色不重复
            available_colors = color_palette[:]
            color_mapping = {}  # 存储“上古声”和颜色的对应关系

            # 如果颜色数量不足，随机生成额外的颜色
            if unique_shanggusheng_count > len(available_colors):
                extra_colors_needed = unique_shanggusheng_count - len(available_colors)
                for _ in range(extra_colors_needed):
                    new_color = self.random_color()  # 随机生成一个颜色
                    available_colors.append(new_color)
                print(
                    f"警告：当前查询的上古声種類 ({unique_shanggusheng_count})"
                    f" 超过了调色盘中可用颜色的数量 ({len(available_colors)})")

            # 按照“上古声”分配颜色
            for shanggusheng in unique_shanggusheng:
                if shanggusheng not in color_mapping:
                    if available_colors:  # 如果还有未使用的颜色
                        color = available_colors.pop()  # 从可用颜色列表中获取一个颜色
                        color_mapping[shanggusheng] = color
                    else:
                        print(f"警告：颜色不足以为所有上古声分配颜色，可能出现重复颜色")
            print(color_mapping)

            # 在 query_database 函数中的最后部分添加此逻辑
            html_content = "<b>上古音聲母來源·图例：</b><br>"

            # 遍历 color_mapping，将音标字母与颜色映射为 HTML
            for shanggusheng, color in color_mapping.items():
                html_content += f'<span style="color:{color}; font-size:30px;">[{shanggusheng}]</span>  '

            self.update_label_signal.emit(html_content)  # 使用信号传递数据

            # 将相同的“中古聲”和“中古等”进行分组
            grouped_data = defaultdict(lambda: defaultdict(list))
            for row in result:
                zhonggusheng = row['中古聲']  # 使用“中古聲”作为行
                zhonggudeng = row['中古等']  # 根据“中古等”来分类
                zhonggudiaos = row['中古調']  # 使用“中古調”决定列
                zitou = row['字頭']  # 字头作为具体填充数据
                shanggusheng = row['上古聲']  # 上古声
                kaihe = row['開合']

                # 字頭分類邏輯：根据“中古等”和“中古調”填入对应的列
                if zhonggudeng in ["一", "二", "三", "四", "A", "B"]:
                    deng_type = "等" if zhonggudeng in ["一", "二", "三", "四"] else "類"
                    deng_name = f"{zhonggudeng}{deng_type}"

                    if zhonggudiaos in ["平", "上", "去", "入"]:
                        kaihe_text = "開" if kaihe == "開" else "合"
                        deng = f"{deng_name}{zhonggudiaos}·{kaihe_text}"

                else:
                    continue  # 如果“中古等”值不匹配，跳过该记录

                grouped_data[zhonggusheng][deng].append({
                    "字頭": zitou,
                    "上古聲": shanggusheng,
                    "color": color_mapping[shanggusheng]
                })

                # 转换为列表形式，每个元素包含“中古聲”、“中古等”和相应的“字頭”列表
            grouped_data_list = []
            for zhonggusheng, deng_dict in grouped_data.items():
                for deng, zitou_list in deng_dict.items():
                    grouped_data_list.append({
                        "中古聲": zhonggusheng,
                        "中古等": deng,
                        "字頭": zitou_list
                    })

            # 查询完成后，通过信号传递数据回主线程更新表格
            self.update_table_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")

        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭

    def update_radioboxes(self, unique_shangguyun):
        """更新单选按钮"""
        # 更新filter_label
        self.filter_label.setText(f"這些字來自{len(unique_shangguyun)}個上古韻部：")

        # 清空现有的单选按钮
        for i in reversed(range(self.radiobox_layout.count())):
            widget = self.radiobox_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.radioboxes.clear()

        # 添加"全部"選項
        all_radiobox = QRadioButton("全部")
        all_radiobox.setFont(QFont("康熙字典體", 16))
        all_radiobox.setStyleSheet("border: none;")
        all_radiobox.setChecked(True)  # 默認選中"全部"
        all_radiobox.toggled.connect(self.apply_filter)  # 添加點擊事件
        self.radiobox_layout.addWidget(all_radiobox)
        self.radioboxes.append(all_radiobox)

        # 添加每個上古韻的單選按鈕
        for label in unique_shangguyun:
            radiobox = QRadioButton(label)
            radiobox.setFont(QFont("康熙字典體", 16))
            radiobox.setStyleSheet("border: none;")
            radiobox.toggled.connect(self.apply_filter)  # 添加點擊事件
            self.radiobox_layout.addWidget(radiobox)
            self.radioboxes.append(radiobox)

    def update_label(self, html_content):
        """更新 label3 的内容"""
        # 将生成的 HTML 字符串应用到 label3
        self.label3.setText(html_content)

        # 确保 QLabel 支持富文本（HTML）
        self.label3.setTextFormat(Qt.RichText)
        self.label3.setWordWrap(True)  # 允许文本换行

    def update_table(self, data):
        """在主线程中更新UI，填充表格数据"""
        # 清空表格布局的现有内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 动态生成行(中古聲)和列(中古等)的列表
        rows = sorted({entry["中古聲"] for entry in data},
                      key=lambda x: "幫滂並明端透定泥娘來精清從心邪知徹澄莊初崇生章昌船書禪日見溪群疑曉匣影雲以".index(
                          x))
        cols = sorted({entry["中古等"] for entry in data},
                      key=lambda x: (int(x[0]) if x[0].isdigit() else 5, x))

        # 创建表头
        # 第一行第一列显示韻部
        selected_yunbu_label = QLabel(zhongguyunchar_select + "部")
        selected_yunbu_label.setFont(QFont("康熙字典體", 18))
        selected_yunbu_label.setAlignment(Qt.AlignCenter)
        selected_yunbu_label.setFixedWidth(100)
        selected_yunbu_label.setStyleSheet(
            "border: 2px solid brown; padding: 5px; color: #BA4A00; background-color: white;")
        self.table_layout.addWidget(selected_yunbu_label, 0, 0)

        # 添加列头
        headers = []
        for col_idx, col_name in enumerate(cols, start=1):
            header = QLabel(col_name)
            header.setFont(QFont("康熙字典體", 14))  # 缩小字体适应长文本
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("border: 2px solid #E6B0AA; padding: 2px; color: brown; background-color: #FEF9F6;")
            self.table_layout.addWidget(header, 0, col_idx)
            headers.append(header)

        # 添加行头
        for row_idx, row_name in enumerate(rows, start=1):
            header = QLabel(row_name)
            header.setFont(QFont("康熙字典體", 18))
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("border: 2px solid #E6B0AA; padding: 5px; color: brown; background-color: #FEF9F6;")
            header.setFixedWidth(100)
            self.table_layout.addWidget(header, row_idx, 0)

        # 填充数据
        cells = defaultdict(list)
        for entry in data:
            row_idx = rows.index(entry["中古聲"]) + 1  # +1 因为第一行是表头
            col_idx = cols.index(entry["中古等"]) + 1  # +1 因为第一列是行头

            label = QLabel()
            text = "  ".join([f'<font color="{item["color"]}">{item["字頭"]}[{item["上古聲"]}]</font>'
                              for item in entry["字頭"]])
            label.setText(text)
            label.setFont(QFont("Ipap", 16))
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("border: 1px solid #E6B0AA; padding: 2px; background-color: white;")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)

            # 添加到表格布局
            self.table_layout.addWidget(label, row_idx, col_idx)
            cells[col_idx].append(label)

        # 列可见性处理
        visible_columns = []
        for col_idx in range(1, len(cols) + 1):
            has_content = any(label.text().strip() != "" for label in cells[col_idx])
            if has_content:
                visible_columns.append(col_idx)
                headers[col_idx - 1].show()
            else:
                headers[col_idx - 1].hide()
                for label in cells[col_idx]:
                    label.hide()

        # 为空白单元格添加占位符（修改后的部分）
        for row_idx in range(1, len(rows) + 1):
            for col_idx in range(1, len(cols) + 1):
                # 检查该位置是否已有组件
                if not self.table_layout.itemAtPosition(row_idx, col_idx):
                    placeholder = QLabel()
                    # 统一设置占位符样式
                    placeholder.setStyleSheet("""
                        QLabel {
                        border: 1px solid #E6B0AA;
                        background-color: #EEEEEE;
                        min-width: 80px;
                        min-height: 40px;
                        }
                    """)
                    self.table_layout.addWidget(placeholder, row_idx, col_idx)
                else:
                    # 确保已有单元格保持正确样式
                    widget = self.table_layout.itemAtPosition(row_idx, col_idx).widget()
                    if isinstance(widget, QLabel) and widget.text().strip() == "":
                        widget.setStyleSheet("""
                            border: 1px solid #E6B0AA;
                            background-color: #EEEEEE;
                        """)


# 查上古韻母窗口——————————————————————————————————————————————————————————————————————————————
class ShangguyunWindow(QWidget):
    shangguyun_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查上古音·韻部")
        self.setGeometry(200, 100, 1900, 1300)
        self.setMinimumSize(1400, 1100)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.initUI()

        # 连接信号到表格更新的槽函数
        self.shangguyun_loaded_signal.connect(self.update_table)

    def initUI(self):
        # 创建主布局
        self.main_layout = QHBoxLayout(self)

        global shangguyunchar_select

        # 1. L半部分 - 放置按钮
        button_frame = QFrame(self)
        button_frame.setFixedWidth(600)
        button_layout = QGridLayout(button_frame)

        # 设置按钮之间的间距
        button_layout.setHorizontalSpacing(20)  # 设置按钮左右之间的间距
        button_layout.setVerticalSpacing(20)  # 设置按钮上下之间的间距

        # 字符列表
        self.selected_button = None
        shangguyunchars = ["東", "鐸", "歌¹", "歌²", "歌³", "耕", "盍¹", "盍²",
                           "盍³", "侯", "緝¹", "緝²", "緝³", "佳", "覺", "覺²", "覺³",
                           "麥", "侵¹", "侵²", "侵³", "談¹", "談²", "談³", "微¹", "微²",
                           "文¹", "文²", "物¹", "物²", "屋", "錫", "宵¹", "宵²",
                           "宵³", "陽", "藥¹", "藥²", "藥³", "魚", "幽", "幽²", "幽³", "元¹",
                           "元²", "元³", "月¹", "月²", "月³", "真¹", "真²", "蒸", "之", "脂¹",
                           "脂²", "職", "質¹", "質²", "終"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for shangguyunchar in shangguyunchars:
            button = QPushButton(shangguyunchar, self)
            button.setFont(QFont("康熙字典體", 17))
            # 设置按钮为方形
            button.setFixedSize(80, 80)  # 宽度和高度相同，方形按钮
            # 设置按钮文字颜色
            button.setStyleSheet("color: #540A03;")  # 改变文字颜色

            button.clicked.connect(self.create_click_handler(button, shangguyunchar))  # 正确绑定点击事件
            button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标

            # 将按钮添加到布局
            button_layout.addWidget(button, row, column)
            # 列数加一
            column += 1
            if column == 5:
                row += 1
                column = 0  # 新行从第 0 列开始

        # 将按钮布局放入主布局
        self.main_layout.addWidget(button_frame)

        # 2. R半部分 __________________

        # 创建表格布局
        self.table_layout = QGridLayout()
        self.main_layout.addSpacing(2)

        # 创建 QScrollArea 嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)
        scroll_area.setWidget(scroll_widget)

        # 将 QScrollArea 添加到主布局
        self.main_layout.addWidget(scroll_area)

        # 设置主窗口的布局
        self.setLayout(self.main_layout)

    def create_click_handler(self, button, shangguyunchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_shangguyun_click(button, shangguyunchar)

    def on_shangguyun_click(self, button, shangguyunchar):
        print("点击的上古韵母：", shangguyunchar)

        # 如果之前有选中的按钮，将其恢复默认颜色
        if self.selected_button:
            self.selected_button.setStyleSheet("color: #540A03")

        # 设置当前点击的按钮颜色，并记录该按钮为选中按钮
        button.setStyleSheet("background-color: #8B2323;"
                             "color: #F5F5F5;"
                             "border-radius: 5px;")  # 设置选中按钮的背景颜色、圓角、邊框
        self.selected_button = button  # 更新为当前选中的按钮

        global shangguyunchar_select
        shangguyunchar_select = shangguyunchar

        # 启动后台线程加载数据
        threading.Thread(target=self.load_data, args=(shangguyunchar,)).start()

    def load_data(self, shangguyunchar):
        try:
            # 创建数据库连接
            connection = create_db_connection()

            # 使用 sqlite3 的游标
            cursor = connection.cursor()

            # 查询
            sql = """
                    SELECT 字頭, 中古韻
                    FROM ancienttesttable1
                    WHERE 上古韻 = ?
                """
            cursor.execute(sql, (shangguyunchar,))
            result = cursor.fetchall()

            # 将结果从元组转换为字典，支持列名访问
            grouped_data = defaultdict(list)
            for row in result:
                grouped_data[row['中古韻']].append(row['字頭'])

            # 将 defaultdict 转换为标准的 list 类型，例如字典的列表
            grouped_data_list = [{"中古韻": key, "字頭": value} for key, value in grouped_data.items()]

            # 发射信号，将数据传递到主线程
            self.shangguyun_loaded_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")
        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭

    def update_table(self, data):
        # 清空现有表格内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 表头
        header1 = QLabel("到中古音屬於韻部")
        header1.setFont(QFont("康熙字典體", 18))
        header1.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該上古韻部的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header2.setAlignment(Qt.AlignCenter)
        header2.setFixedHeight(80)

        # 添加表头
        self.table_layout.addWidget(header1, 0, 1)
        self.table_layout.addWidget(header2, 0, 0)

        # 设置布局间距
        self.table_layout.setHorizontalSpacing(0)
        self.table_layout.setVerticalSpacing(0)
        self.table_layout.setContentsMargins(0, 0, 0, 0)

        # 设置列宽比例
        self.table_layout.setColumnStretch(0, 5)  # 中古声列
        self.table_layout.setColumnStretch(1, 1)  # 上古字头列

        # 填充数据
        for row_num, row_data in enumerate(data):
            # 中古音列
            shangguyun_label = QLabel(row_data["中古韻"])
            shangguyun_label.setStyleSheet(
                "border: 1px solid brown; color: #CD3700; padding: 10px; background-color: #EEE5DE;")
            shangguyun_label.setFont(QFont("康熙字典體", 26))
            shangguyun_label.setAlignment(Qt.AlignCenter)
            shangguyun_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(shangguyun_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown; padding: 10px;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            zitou_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)


# 查中古聲母窗口——————————————————————————————————————————————————————————————————————————————
class ZhonggushengWindow(QWidget):
    # 定义一个信号，传递加载的数据
    zhonggusheng_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查中古音·聲母")
        self.setGeometry(200, 100, 1900, 1200)
        self.setMinimumSize(1400, 900)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.initUI()

        # 连接信号到表格更新的槽函数
        self.zhonggusheng_loaded_signal.connect(self.update_table)

    def initUI(self):
        # 创建主布局
        self.main_layout = QHBoxLayout(self)

        global zhonggushengchar_select

        # 1. L半部分 - 放置音标按钮
        button_frame = QFrame(self)
        button_frame.setFixedWidth(600)
        button_layout = QGridLayout(button_frame)

        # 设置按钮之间的间距
        button_layout.setHorizontalSpacing(20)  # 设置按钮左右之间的间距
        button_layout.setVerticalSpacing(20)  # 设置按钮上下之间的间距

        self.selected_button = None
        # 字符列表
        zhonggushengchars = ["幫", "滂", "並", "明", "端", "透", "定", "泥",
                             "精", "清", "從", "心", "邪", "莊", "初", "崇", "生",
                             "章", "昌", "船", "書", "禪", "知", "徹", "澄", "娘",
                             "見", "溪", "群", "疑", "影", "以", "曉", "匣",
                             "來", "日", "雲"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for zhonggushengchar in zhonggushengchars:
            button = QPushButton(zhonggushengchar, self)
            button.setFont(QFont("康熙字典體", 18))
            # 设置按钮为方形
            button.setFixedSize(80, 80)  # 宽度和高度相同，方形按钮
            # 设置按钮文字颜色
            button.setStyleSheet("color: #540A03;")  # 改变文字颜色

            button.clicked.connect(self.create_click_handler(button, zhonggushengchar))  # 正确绑定点击事件
            button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标

            # 将按钮添加到布局
            button_layout.addWidget(button, row, column)
            # 列数加一
            column += 1
            # 如果当前字符是“明”、“泥”、“邪”，换行（行数加1，列数重置为0）
            if zhonggushengchar in ["明", "泥", "邪", "生", "禪", "娘", "疑", "匣"]:
                row += 1
                column = 0  # 让下一行从第 0 列开始
            # 每行最多放置 5 个按钮，如果列数达到5，换行
            elif column == 5:
                row += 1
                column = 0  # 新行从第 0 列开始

        # 将按钮布局放入主布局
        self.main_layout.addWidget(button_frame)

        # 2. R半部分 __________________

        # 创建表格布局
        self.table_layout = QGridLayout()
        self.main_layout.addSpacing(2)

        # 创建 QScrollArea 嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)
        scroll_area.setWidget(scroll_widget)

        # 将 QScrollArea 添加到主布局
        self.main_layout.addWidget(scroll_area)

        # 设置主窗口的布局
        self.setLayout(self.main_layout)

    def create_click_handler(self, button, zhonggushengchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_zhonggusheng_click(button, zhonggushengchar)

    def on_zhonggusheng_click(self, button, zhonggushengchar):
        print("点击的中古声母：", zhonggushengchar)

        # 如果之前有选中的按钮，将其恢复默认颜色
        if self.selected_button:
            self.selected_button.setStyleSheet("color: #540A03")

        # 设置当前点击的按钮颜色，并记录该按钮为选中按钮
        button.setStyleSheet("background-color: #8B2323;"
                             "color: #F5F5F5;"
                             "border-radius: 5px;")  # 设置选中按钮的背景颜色、圓角、邊框
        self.selected_button = button  # 更新为当前选中的按钮

        global zhonggushengchar_select
        zhonggushengchar_select = zhonggushengchar

        # 启动后台线程加载数据
        threading.Thread(target=self.load_data, args=(zhonggushengchar,)).start()

    def load_data(self, zhonggushengchar):
        try:
            # 创建数据库连接
            connection = create_db_connection()

            # 使用 sqlite3 的游标
            cursor = connection.cursor()

            # 查询
            sql = """
                    SELECT 字頭, 上古聲
                    FROM ancienttesttable1
                    WHERE 中古聲 = ?
                """
            cursor.execute(sql, (zhonggushengchar,))
            result = cursor.fetchall()

            # 将结果从元组转换为字典，支持列名访问
            grouped_data = defaultdict(list)
            for row in result:
                grouped_data[row['上古聲']].append(row['字頭'])

            # 将 defaultdict 转换为标准的 list 类型，例如字典的列表
            grouped_data_list = [{"上古聲": key, "字頭": value} for key, value in grouped_data.items()]

            # 发射信号，将数据传递到主线程
            self.zhonggusheng_loaded_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")
        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭

    def update_table(self, data):
        # 清空现有表格内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 表头
        header1 = QLabel("來自上古音聲母")
        header1.setFont(QFont("康熙字典體", 20))
        header1.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該中古音聲母的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header2.setAlignment(Qt.AlignCenter)
        header2.setFixedHeight(80)

        # 添加表头
        self.table_layout.addWidget(header1, 0, 1)
        self.table_layout.addWidget(header2, 0, 0)

        # 设置布局间距
        self.table_layout.setHorizontalSpacing(0)
        self.table_layout.setVerticalSpacing(0)
        self.table_layout.setContentsMargins(0, 0, 0, 0)

        # 设置列宽比例
        self.table_layout.setColumnStretch(0, 5)  # 中古声列
        self.table_layout.setColumnStretch(1, 1)  # 上古字头列

        # 填充数据
        for row_num, row_data in enumerate(data):
            # 中古音列
            zhonggusheng_label = QLabel(row_data["上古聲"])
            zhonggusheng_label.setStyleSheet(
                "border: 1px solid brown; color: #CD3700; padding: 10px; background-color: #EEE5DE;")
            zhonggusheng_label.setFont(QFont("IpaP", 26))
            zhonggusheng_label.setAlignment(Qt.AlignCenter)
            zhonggusheng_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zhonggusheng_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown; padding: 10px;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            zitou_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)


# 查上古声母窗口_______________________________________________________________________________
class ShanggushengWindow(QWidget):
    # 定义一个信号，传递加载的数据
    shanggusheng_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setGeometry(1, 1, 2200, 1200)
        self.setWindowTitle("賢哉古音 - 查上古音·聲母")

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.initUI()

        # 连接信号到表格更新的槽函数
        self.shanggusheng_loaded_signal.connect(self.update_table)

    def initUI(self):

        # 设置主布局为水平布局
        self.main_layout = QHBoxLayout()
        # 设置窗口起始位置，例如 (x, y) = (100, 100)
        self.move(1, 1)

        global shanggushengipa_select

        # 1. L半部分 - 放置音标按钮
        button_frame = QFrame(self)

        button_layout = QGridLayout(button_frame)

        self.selected_button = None  # 用于保存当前选中的按钮
        # 字符列表shanggushengipas
        shanggushengipas = ["b", "bɡˡ", "bɡʳ", "bkʳ", "bˡ", "bl", "b‧l", "bˡʲ",
                            "bʳ", "b‧r", "br", "d", "dʲ", "ɢ", "ɡ", "ɢbˡ", "ɡbˡ",
                            "ɡbʳ", "ɢʲ", "ɡʲ", "ɢl", "ɡl", "ɡˡ", "ɡ‧l", "ɢˡʲ", "ɡˡʲ",
                            "ɢmˡ", "ɢʳ", "ɡr", "ɡʳ", "ɡ‧r", "ɢʷ", "ɡʷ", "ɢʷʲ", "ɢʷˡ", "ɡʷˡ",
                            "ɢʷʳ", "ɡʷʳ", "k", "kʰ", "kʰʲ", "kʰl", "kʰˡ", "kʰˡʲ", "kʰʳ", "kʰr",
                            "kʰʷ", "kʰʷʲ", "kʰʷʳ", "kʲ", "kl", "kˡ", "kˡʲ", "kpʰ", "klʲ", "kpʳ",
                            "kʳ", "kr", "k‧r", "kʷ", "kt", "kʷˡ", "kʷʳ", "kʷʲ", "l", "l̥", "l̥ʰ", "lʲ", "l̥ʲ", "m",
                            "m̥", "mb", "mbˡ", "mblʲ", "mbʳ", "mɡl", "mɡˡ", "mɡr", "mɡʳ", "mɡlʲ", "mɡʷ", "mɡʷˡ", "mɡʷʳ",
                            "mɡʷr",
                            "m̥ʰ", "m̥ʰʳ", "m̥ʰˡ", "m̥ʰʲ", "m̥ʰˡʲ", "mkʳ", "mˡ", "ml", "m̥l", "mlʲ", "mˡ̥ʲ",
                            "mʳ", "mr", "m‧r", "mʳ̥ʰ", "m̥ʳ", "n", "n̥", "nd", "n̥ʰ",
                            "nʲ", "n̥ʲ", "ŋ", "ŋ̊", "ŋɡ", "ŋɡˡ", "ŋɡl", "ŋɡʲe", "ŋɡʳ", "ŋɡʷ", "ŋɡʷʲ", "ŋɡʷʳ", "ŋ̊ʰ",
                            "ŋ̊ʰˡʲ",
                            "ŋ̊ʰʷ", "ŋ̊ʰʳ", "ŋ̊ʰʷʳ", "ŋˡ", "ŋʲ", "ŋ̊ʲ", "ŋpʳ", "ŋʳ", "ŋr", "ŋʷ", "ŋ̊ʳ", "ŋʷʳ", "ŋʷʲ",
                            "p", "pʰ", "pɡʳ", "pʰl", "pʰˡ", "pʰˡʲ", "pʰʳ",
                            "pʰr", "pʲ", "pk", "pkʰ", "pkʰʳ", "pkʰˡ", "pkʳ", "pkˡ", "pˡ", "pl", "p‧l̥", "p‧l̥ʰ", "pˡʲ",
                            "pqʰʳ",
                            "pqʰˡ", "pqʰʷ", "pʳ", "q", "qʰ", "qʰl", "qʰˡ", "qʰʲ", "qʰˡʲ", "qʰʳ", "qʰʷ", "qʰʷʲ", "qʰʷʳ",
                            "qʰʷr",
                            "qˡ", "qn", "qpʰ", "qpʰʳ", "qpʰr", "qpʰˡ", "qpˡ", "qpʳ", "qʳ", "qʷ", "qʷʳ",
                            "qʷʲ", "r", "r̥", "rd", "r̥ʲ", "rn", "rt", "rtʰ", "s", "sb", "sbˡ", "sbˡʲ", "sbr",
                            "sd", "sɡ", "sɢˡ", "sɢ", "sɡl", "sɡˡ", "sɢˡʲ", "sɡr", "sɢʷ", "sɡʷr", "sʰ", "sʰr", "sʰʳ",
                            "sk", "skʰ",
                            "skʰl", "skʰˡ", "skʰr", "skʰʳ", "skʰʷ", "skˡ", "skl", "skʳ", "skr", "skʷ", "skʷˡ", "skʷr",
                            "skʷʳ", "sˡ",
                            "sl̥", "sm", "smˡ", "sn", "sn̥", "sŋ", "s‧ŋ", "sŋ̊", "sŋʳ", "sŋ̊r", "sp", "spʰ", "spʰr",
                            "spˡ",
                            "spʳ", "sqʰ", "sqʰʷ", "sqʳ", "sqʷʳ", "sʳ", "sr", "st", "t", "tʰ", "tʰʲ", "tʲ", "z", "zr",
                            "zˡ"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for i, shanggushengipa in enumerate(shanggushengipas):
            button = QPushButton(shanggushengipa, self)
            button.setFont(QFont("IpaP", 15))
            button.setFixedWidth(80)  # 固定按鈕寬度
            button.setMinimumHeight(60)  # 最小按鈕高度
            button.clicked.connect(self.create_click_handler(button, shanggushengipa))  # 正确绑定点击事件
            button_layout.addWidget(button, i // 12, i % 12)  # 每行放置n个按钮
            button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标

        # 2. R半部分 -

        # 创建表格布局
        self.table_layout = QGridLayout()

        # 创建 QScrollArea 嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)
        scroll_area.setWidget(scroll_widget)

        # 将 button_frame 和 scroll_area 添加到主布局
        self.main_layout.addWidget(button_frame, stretch=1)  # 设置 stretch 为 1
        self.main_layout.addWidget(scroll_area, stretch=1)  # 设置 stretch 为 1
        # 设置主窗口的布局
        self.setLayout(self.main_layout)

    def create_click_handler(self, button, shanggushengipa):
        # 返回lambda以正确处理点击事件，并传入按钮
        return lambda: self.on_shanggusheng_click(button, shanggushengipa)

    def on_shanggusheng_click(self, button, shanggushengipa):
        print("你点击了: ", shanggushengipa)

        # 如果之前有选中的按钮，将其恢复默认颜色
        if self.selected_button:
            self.selected_button.setStyleSheet("")

        # 设置当前点击的按钮颜色，并记录该按钮为选中按钮
        button.setStyleSheet("background-color: #8B2323;"
                             "color: #F5F5F5;"
                             "border-radius: 5px;"
                             "font-weight: bold")  # 设置选中按钮的背景颜色、圓角、邊框
        self.selected_button = button  # 更新为当前选中的按钮

        global shanggushengipa_select
        shanggushengipa_select = shanggushengipa
        # 启动后台线程加载数据
        threading.Thread(target=self.load_data, args=(shanggushengipa,)).start()

    def load_data(self, shanggushengipa):
        # 连接数据库并查询
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 查询所有该声母的字及对应的上古声
            sql = """
                SELECT DISTINCT 字頭, 中古聲
                FROM ancienttesttable1 
                WHERE 上古聲 = ?
            """
            cursor.execute(sql, (shanggushengipa,))
            result = cursor.fetchall()

            # 将结果从元组转换为字典，支持列名访问
            grouped_data = defaultdict(list)
            for row in result:
                grouped_data[row['中古聲']].append(row['字頭'])

            # 将 defaultdict 转换为标准的 list 类型，例如字典的列表
            grouped_data_list = [{"中古聲": key, "字頭": value} for key, value in grouped_data.items()]

            # 发射信号，将数据传递到主线程
            self.shanggusheng_loaded_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")
        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭

    def update_table(self, data):
        # 清空现有表格内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 表头
        header1 = QLabel("演變為中古音聲母")
        header1.setFont(QFont("康熙字典體", 20))
        header1.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該上古音的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; padding: 5px; background-color: #EEE9E9;")
        header2.setAlignment(Qt.AlignCenter)
        header2.setFixedHeight(80)

        # 添加表头
        self.table_layout.addWidget(header1, 0, 1)
        self.table_layout.addWidget(header2, 0, 0)

        # 设置布局间距
        self.table_layout.setHorizontalSpacing(0)
        self.table_layout.setVerticalSpacing(0)
        self.table_layout.setContentsMargins(0, 0, 0, 0)

        # 设置列宽比例
        self.table_layout.setColumnStretch(0, 5)  # 中古声列
        self.table_layout.setColumnStretch(1, 1)  # 上古字头列

        # 填充数据
        for row_num, row_data in enumerate(data):
            # shang古音列
            shanggusheng_label = QLabel(row_data["中古聲"])
            shanggusheng_label.setStyleSheet(
                "border: 1px solid brown; color: #CD3700; padding: 10px; background-color: #EEE5DE;")
            shanggusheng_label.setFont(QFont("康熙字典體", 24))
            shanggusheng_label.setAlignment(Qt.AlignCenter)
            shanggusheng_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(shanggusheng_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown; padding: 10px;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            zitou_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)


# 查字窗口——————————————————————————————————————————————————————————————————————————————————————
class SearchCharaWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查字")
        self.setGeometry(200, 200, 1500, 800)
        self.setFixedWidth(1500)
        self.setMinimumHeight(800)
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.initUI()

    def initUI(self):
        # 创建主布局
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 创建输入框和标签的布局
        input_layout = QHBoxLayout()
        layout.addLayout(input_layout)

        # 标签
        label = QLabel(" 输入要查找的单字:    ")
        label.setFont(QFont("Aa古典刻本宋", 26))
        label.setAlignment(Qt.AlignCenter)  # 将标签居中
        label.setContentsMargins(300, 40, 0, 40)  # 设置 label 和窗口左边的边距
        input_layout.addWidget(label)

        # 输入框
        self.search_chara_entry = QLineEdit()
        self.search_chara_entry.setFont(QFont("宋体", 23, QFont.Bold))  # 设置字体为“宋体”，字号为23
        self.search_chara_entry.setFixedHeight(60)  # 固定输入框的高度为60px
        self.search_chara_entry.setFixedWidth(300)  # 固定输入框的宽度为300px
        self.search_chara_entry.setAlignment(Qt.AlignCenter)  # 将输入框中的文本居中
        input_layout.addWidget(self.search_chara_entry)

        # 在布局中添加两个伸缩空间以使其居中
        input_layout.addStretch(1)

        # 连接回车事件
        self.search_chara_entry.returnPressed.connect(self.check_input)  # 按下回车键时触发查询

        # 创建按钮布局
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # 创建查询按钮
        search_chara_button = QPushButton("查询(暂时只支持繁体)")
        search_chara_button.setFont(QFont("Aa古典刻本宋", 18))
        search_chara_button.setFixedWidth(600)
        search_chara_button.setStyleSheet(f"color: #B03A2E; padding: 20px 5px;")
        search_chara_button.clicked.connect(self.check_input)
        search_chara_button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标
        button_layout.addWidget(search_chara_button)

        # 清空按钮
        clear_button = QPushButton("清空内容")
        clear_button.setFont(QFont("Aa古典刻本宋", 18))
        clear_button.setStyleSheet(f"color: #784212; padding: 20px 5px;")
        clear_button.setFixedWidth(300)
        clear_button.clicked.connect(self.clear_all)
        clear_button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标
        button_layout.addWidget(clear_button)

        # 创建一个滚动区域用于包含表格
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # 创建一个用于包含表格的子控件
        table_container = QWidget()
        self.table_layout = QGridLayout(table_container)
        self.table_layout.setSpacing(2)  # 设置布局的间距为 2
        scroll_area.setWidget(table_container)

    # 清空输入框和表格内容
    def clear_all(self):
        self.search_chara_entry.clear()
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def closeEvent(self, event):
        """在窗口关闭时清空内容"""
        self.clear_all()  # 先调用 clear_all 清空输入框和表格内容
        event.accept()  # 允许窗口关闭

    # 检查输入并查询数据库
    def check_input(self):
        chara = self.search_chara_entry.text()
        if re.fullmatch(r'^.$', chara):  # 正则匹配单个汉字
            print("合法输入")
            self.query_database(chara)
        else:
            QMessageBox.warning(self, "警告", "非法输入，请输入单个汉字")

    # 查询数据库
    def query_database(self, chara):
        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                sql = "SELECT * FROM ancienttesttable1 WHERE 字頭=?"
                cursor.execute(sql, (chara,))
                result = cursor.fetchall()
                if result:
                    print("查询结果:", result)
                    self.display_results(result)
                else:
                    QMessageBox.information(self, "无结果", "没有查询到相关内容")
            except sqlite3.Error as e:
                print(f"数据库查询失败: {e}")
                QMessageBox.warning(self, "警告", "数据库查询失败")
            finally:
                connection.close()
        else:
            QMessageBox.warning(self, "警告", "数据库连接失败")

    # 显示查询结果
    def display_results(self, result):
        # 清空表格布局中的内容
        self.clear_all()

        # 自定义的表头字符
        custom_headers = ["數據id", "字 頭", "上古聲母", "上古韻部", "中古聲母", "中古韻部", "聲 調", "等", "開 合"]
        # 数据库列名，用于从查询结果中获取数据
        headers = result[0].keys()  # 这里仍然保留数据库中的列名
        self.table_layout.setSpacing(2)  # 设置布局的间距为 2，若為0則是去除单元格之间的间隙

        # 创建表头
        for col, header in enumerate(custom_headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("康熙字典體", 18))
            header_label.setStyleSheet("border: 1px solid #6C1002; background-color: #FBF0F0; "
                                       "padding: 5px; color: #6C1002; border-radius: 10px;")
            header_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(header_label, 0, col)

        # 比较每列的值，用于标记不同的列
        column_differences = [False] * len(headers)  # 初始化标记，默认为没有差异

        if len(result) > 1:  # 如果行数大于1，说明是多音字
            for col_num in range(len(headers)):
                first_value = str(result[0][headers[col_num]])  # 取第一行的值
                # 检查该列的所有行是否有不同的值
                for row_num in range(1, len(result)):
                    if str(result[row_num][headers[col_num]]) != first_value:
                        column_differences[col_num] = True  # 如果有不同值，标记该列
                        break

            # 创建表格内容
        for row_num, result in enumerate(result):
            for col_num, key in enumerate(headers):
                value_label = QLabel(str(result[key]))

                # 如果是第3列（col_num == 2）且行号大于等于0（即第二行及之后），设置字体为 IpaP
                if col_num == 2 and row_num >= 0:
                    value_label.setFont(QFont("IpaP", 24))
                else:
                    value_label.setFont(QFont("宋体", 20))

                # 设置默认的样式
                value_label.setStyleSheet(
                    "border: 1px solid #8A1A00; background-color: #FFF9F9; "
                    "padding: 10px; color: #3C0D00; border-radius: 10px;")

                # 如果该列的值不同，设置不同樣式
                if column_differences[col_num]:
                    value_label.setStyleSheet(
                        "border: 1px solid #CF3801; background-color: #FFECD4; "
                        "padding: 10px; color: #D53A00; border-radius: 10px;")
                value_label.setAlignment(Qt.AlignCenter)
                value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
                self.table_layout.addWidget(value_label, row_num + 1, col_num)  # 使用 row_num + 1 使其显示在第二行及以后


# 更新日誌窗口
class UpdateLogWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("賢哉古音 - 更新日誌")
        self.setGeometry(400, 300, 1300, 900)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 设置窗口内容
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        # 创建布局
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 创建日志内容标签
        log_label = QLabel()
        log_label.setTextFormat(Qt.RichText)  # 设置为富文本模式
        log_label.setText("""
            <h3 style="font-family: '康熙字典體'; font-size: 72px; color: #8B1A1A;">更新日誌</h3>
            <ul style="font-family: '楷体'; font-size: 35px; line-height: 3.8;">
                <li>v1.3.5【當前版本】<br>
                            ·賢哉bot：對話查字功能閃退bug已修復；修改了聊天氣泡大小。<br>
                <li>v1.3.4<br>
                            ·中古音韻部-韻圖顯示：修復左上角選中的韻部提示顯示不全的bug；韻圖首列按照《方言調查字表》的聲母順序重新排布；<br>
                            ·已知問題：使用bot對話查詢時，可能出現閃退，待修復。<br>
                <li>v1.3.3<br>
                            ·查字窗口:允許調整高度、允許表格滾動，以支持顯示讀音較多的字；<br>
                            ·中古音韻部-韻圖顯示：可以篩選上古韻部來源。<br>
                <li>v1.3.0<br>
                            ·各窗口的輸出表格：支持選中單元格内的字符，使用Ctrl+C複制。<br>
                <li>v1.2.9<br>
                            ·賢哉bot：修改了對話查字時多音字的呈現方式；增加了bot的幫助提示；<br>
                            ·查字：修復了關閉窗口再重新打開時，上一次查詢的結果未被清除的bug；<br>
                            ·更新日誌：修改了“關閉”按鈕的樣式。<br>
                <li>v1.2.8<br>
                            ·賢哉bot：修改了對話查字的呈現方式；另外，可以直接在bot中輸入想查詢的中古音聲母、上古音和中古音韻部。<br>
                <li>v1.2.7<br>
                            ·改動了查字窗口的表格UI。當查詢多音字時，值不同的列會高亮顯示。<br>
                <li>v1.2.5<br>
                            ·賢哉bot：可以直接在bot中輸入想查詢的字。<br>
                <li>v1.2.4<br>
                            ·查字：修復窗口尺寸bug；<br>
                            ·應用程序圖標更新；<br>
                            ·賢哉bot：更新聊天窗口樣式；<br>
                            ·[bot功能預告]：未來可以直接在bot中輸入想查詢的字。<br>
                <li>v1.2.3<br>
                            ·bot圖標：新增眨眼動畫。<br>
                <li>v1.2.2<br>
                            ·修復bot圖標消失的bug。<br>
                <li>v1.2.1<br>
                            ·首頁UI更新：增加bot用於解答問題。【問答功能測試中，後續版本完善】<br>
                <li>v1.2.0<br>
                            ·軟件名稱煥新，歡迎使用[賢哉古音]；<br>
                            ·增加所有輸出結果的表格邊距，使輸出的字符不會緊貼邊框；<br>
                            ·上古音聲母：選中按鈕時，音標字體加粗；<br>
                            ·中古音韻部-韻圖顯示：優化了歸字填入列表時的判斷代碼；<br>
                            ·中古音韻部：修復了未選中韻部時多次點擊“以韻圖顯示結果”會卡死的bug；<br>
                            ·查字：上古音的聲母音標改用國際音標專用字體（IpaP）；<br>
                            ·上古音韻部、中古音韻部查詢：窗口標題的“韻母”改為“韻部”。<br>
                <li>v1.1.9<br>
                            ·中古音韻部-韻圖顯示：加入了篩選維度“等”。<br>
                <li>v1.1.8<br>
                            ·中古音韻部-韻圖顯示：加入上古音聲母的顏色圖例；<br>
                              未選中韻部時，點擊“以韻圖顯示結果”會彈出警告；<br>
                            ·所有頁面的按鈕：鼠標移動到按鈕上時，指針變成手形。<br>
                <li>v1.1.7<br>
                            ·中古音韻部-韻圖顯示：1.1.6版本中，顏色重複使用的bug和調整窗口大小導致的表格列寬顯示bug已修復；
                                同時修復了結果中有概率出現白色字體的問題；<br>
                            ·代碼：優化了窗口圖標的調用方法。<br>
                <li>v1.1.6<br>
                            ·中古音韻部-韻圖顯示：現在可以从“等”、“中古音聲母”、“聲調”、“上古音聲母”四個維度分類顯示中古音韻部的歸屬字；<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>  
                            ·更新日誌：更改了日誌的文本字體。<br>
                            ·[韻圖顯示]已知問題：<br>
                                -①程序隨機選取顏色時可能重複使用某種顏色，待修復 <br>
                                -②在調整窗口大小時，結果表格的寬度顯示bug<br>
                <li>v1.1.5<br>
                            ·中古音韻部-韻圖顯示：現在可以从“等”、“中古音聲母”、“聲調”三個維度分類顯示中古音韻部的歸屬字。<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>           
                <li>v1.1.3<br>
                            ·中古音聲母：增加“雲”母按鈕；<br>
                            ·中古音韻部：增加“以韻圖形式顯示”按鈕，可以在新窗口用韻圖的形式，从“等”和“中古音聲母”兩個維度分類顯示中古音韻部的歸屬字；<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>                
                            ·中古音韻部：v1.0.9版本加入的篩選按鈕已移除。<br>
                <li>v1.1.1<br>
                            ·數據庫：更正了“𥝖”字的中古音韻部數據，修改了中古音韻部查詢的相關按鈕。<br>
                <li>v1.1.0<br>
                            ·中古音韻部查詢：嘗試標記“等”時，顯示“加载中”提示【測試功能，未來版本可能修改或移除】；<br>
                            ·中古音韻部查詢：優化輸出結果的字間距，使文字顏色變化前後字間距一致；<br>
                            ·更新日誌窗口：更改為倒序排列，最新版本的修改點置頂顯示，方便查閱。<br>
                <li>v1.0.9<br>
                            ·上古音韻部查詢、中古音聲母&韻部查詢：修復了點擊過的按鈕文字變黑的問題；<br>
                            ·中古音韻部查詢：加入多維度標記按鈕【測試中，目前儘能標記“等”】。 <br>              
                <li>v1.0.4 <br>
                            ·中古音聲母查詢窗口：表格字符改動“中古音的歸屬字”→“該中古音聲母的歸屬字”；<br>
                            ·更新日誌窗口：內容支持滾動；<br>
                            ·上古音聲母&韻部查詢、中古音聲母&韻部查詢窗口：輸出結果時，允許點擊的按鈕保持高亮；<br>
                            ·主窗口只允許同時存在一個，子窗口逐一適配中。 <br>  
                <li>v1.0.3 <br>
                            ·上古音聲母查詢窗口：更新頁面佈局與查詢邏輯；<br>
                            ·查字窗口：支持輸入后按Enter鍵查詢。<br>
                <li>v1.0.2 <br>  
                            ·更新數據庫條目：修正中古韻部[咸]誤作[鹹]的錯誤；<br>
                            ·中古音韻部查詢按鈕：基於切韻韻系、廣韻韻目重新排序；<br>
                            ·增加[更新日誌]查看功能。<br>                                
                <li>v1.0.1 - 修復了部分屏幕分辨率的UI適配問題。</li>                          
                <li>v1.0.0 - 初始版本打包發佈。</li>
            </ul>
        """)  # 這屬於html代碼↑
        font = QFont("Aa古典刻本宋", 20)  # 设置字体和字号
        log_label.setFont(font)
        log_label.setAlignment(Qt.AlignTop)
        log_label.setWordWrap(True)  # 允许自动换行
        layout.addWidget(log_label)

        # 创建滚动区域并将 log_label 放入
        scroll_area = QScrollArea()
        scroll_area.setWidget(log_label)  # 将 log_label 设置为 QScrollArea 的子控件
        scroll_area.setWidgetResizable(True)  # 使 log_label 在滚动区域内可调整大小
        layout.addWidget(scroll_area)  # 将滚动区域添加到主布局

        # 添加一个关闭按钮
        close_button = QPushButton("關 閉")
        close_button.setStyleSheet("""
                    QPushButton {
                        background-color: #8B1A1A;
                        color: white;
                        border-radius: 10px;
                        padding: 4px 16px;
                        font-size: 28px;
                        font-family: "康熙字典體"
                    }
                    QPushButton:hover {
                        background-color: #a32f2f;
                        font-weight: bold;
                    }
                """)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)


# ————————————————————————————————————————————————————————————————————————————————————————————
if __name__ == '__main__':
    # 创建唯一实例的检测
    single_instance = SingleInstanceApplication("UniqueAppIdentifier")

    if single_instance.is_running():
        # 如果已有实例在运行，激活现有实例并退出
        single_instance.activate_existing_instance()
        sys.exit(0)
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
