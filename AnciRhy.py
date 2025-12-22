import colorsys
import json
import math
import os
import time
import sys
import re
import threading
from collections import defaultdict
import random
import html
import markdown
import requests
from PyQt5 import sip
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QLabel, QPushButton,
                             QGridLayout, QHBoxLayout, QMessageBox,
                             QLineEdit, QFrame, QSizePolicy, QScrollArea,
                             QToolTip, QRadioButton, QComboBox, QDialog, QTextEdit, QDialogButtonBox, QMenu,
                             QAbstractItemView, QHeaderView, QTableWidgetItem, QTableWidget, QFormLayout,
                             QToolButton, QSpacerItem, QTextBrowser, QProgressDialog, QGroupBox, QProgressBar, )
from PyQt5.QtGui import QFont, QIcon, QCursor, QColor, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSharedMemory, QSystemSemaphore, QSize, QEvent, QTimer, \
    QRect, QThread
import sqlite3

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
        self.cursor = self.conn.cursor()
        self.thread_connections = {}  # 存储线程ID到(connection, cursor)的映射

        self.search_window = None  # 查字初始化为空
        self.shanggusheng_window = None  # 上古声母窗口初始化为空
        self.shangguyun_window = None
        self.zhonggusheng_window = None
        self.zhongguyun_window = None
        self.update_log_window = None
        self.fanqieduizhao_window = None
        self.shengfu_sanbu_window = None
        self.shengfu_zhonggusheng_window = None
        self.shengyun_match_window = None

        self.shengfu_sanbu_data_cache = None  # 添加聲符散佈的数据缓存变量

        self.is_waiting_for_column_choice = False  # 标志位，用来跟踪是否等待用户选择列
        self.pending_character = None  # 用于存储待查询的字符
        self.confirmed_character = None  # 新增：用于存储用户确认的字符

        self.progress_dialog = None  # 进度对话框变量
        self.bot_chat_window = None  # 确保 bot 聊天窗口变量已初始化

        self.windows_to_close = []  # 新增：用于跟踪所有子窗口的列表

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
        buttons_texts = ["查上古音·聲母", "查中古音·聲母", "查上古音·韻部", "查中古音·韻部"]
        button_fonts = QFont("康熙字典體", 17)
        button_colors = ["#3C0D00", "#3C0D00", "#8E4A37", "#8E4A37"]
        button_commands = [self.open_shanggusheng_window,
                           self.open_zhonggusheng_window,
                           self.open_shangguyun_window,
                           self.open_zhongguyun_window]

        # 创建按钮容器布局（QHBoxLayout）放置按钮
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

        button_layout2 = QHBoxLayout()  # 第二行按钮的布局
        buttons_texts2 = ["查字（字典模式）", "反切對照查詢", ]
        button_colors2 = ["#CA6503", "#3C0D00"]
        button_commands2 = [self.open_search_chara_window,
                            self.open_fanqieduizhao_window
                            ]
        for text, color, command in zip(buttons_texts2, button_colors2, button_commands2):
            button2 = QPushButton(text)
            button2.setFont(button_fonts)
            button2.setStyleSheet(f"""
                QPushButton {{
                    color: {color}; padding: 20px 5px;
                }}
                QPushButton:hover {{
                    font-weight: bold;
                }}
            """)
            button2.setCursor(Qt.PointingHandCursor)
            button2.clicked.connect(command)
            button_layout2.addWidget(button2)  # 将按钮添加到水平布局

        button_layout3 = QHBoxLayout()  # 第3行按钮的布局
        buttons_texts3 = ["《廣韻》聲符散佈", "[聲符 - 中古聲母]  關係", "聲韻匹配試煉場【嘗嘗賢淡】"]
        button_colors3 = ["#8E4A37", "#8C0D28", "#CA6503"]
        button_commands3 = [self.open_shengfu_sanbu_window,
                            self.open_shengfu_zhonggusheng_window,
                            self.open_shengyun_match_window
                            ]
        for text, color, command in zip(buttons_texts3, button_colors3, button_commands3):
            button3 = QPushButton(text)
            button3.setFont(button_fonts)
            button3.setStyleSheet(f"""
                        QPushButton {{
                            color: {color}; padding: 20px 5px;
                        }}
                        QPushButton:hover {{
                            font-weight: bold;
                        }}
                    """)
            button3.setCursor(Qt.PointingHandCursor)
            button3.clicked.connect(command)
            button_layout3.addWidget(button3)  # 将按钮添加到水平布局

        layout.addLayout(button_layout)  # 将按钮水平布局添加到主垂直布局
        layout.addLayout(button_layout2)  # 第2排按钮的布局添加到主布局
        layout.addLayout(button_layout3)  # 第3排按钮的布局添加到主布局
        bottom_layout = QHBoxLayout()

        # 更新日志按钮样式优化
        log_button = QPushButton("v 1.4.5 關於賢哉古音")
        log_button.setStyleSheet("""
           QPushButton {
               color: #B22222;  
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

        # 新增DeepSeek相关属性
        self.api_key = None
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model_name = "deepseek-chat"
        self.load_api_key()  # 启动时尝试加载保存的API密钥
        self.conversation_history = []  # 对话历史记录
        self.deepseek_thread = None  # API调用线程
        self.api_timeout = 180  # 增加超时时间
        # 内存管理相关
        self.active_threads = []  # 跟踪所有活动线程
        self.is_closing = False  # 标记应用程序是否正在关闭

        # 加载保存的API密钥
        self.load_api_key()

        # 提示词配置
        self.system_prompt = """你是一位顶尖的汉语音韵学专家，专注于上古音（先秦两汉）和中古音（隋唐宋）研究。请严格遵循以下要求：
1. **专业领域聚焦**：
- 只回答与汉语音韵学、上古音、中古音相关的问题
- 涉及范围：声母系统、韵母系统、声调演变、音系构拟、切韵音系、诗经用韵、谐声系统、方言比较等
- 非音韵学问题请回答："此问题超出我的研究范围"
2. **回答规范**：
- 所有古音构拟必须标注国际音标(IPA)
- 中古音必须标注《切韵》音系地位（如：帮母、东韵、平声）
- 上古音必须标注韵部（如：之部、鱼部）、声母类别（如：帮组、见系）
- 引用重要学者观点（高本汉、王力、郑张尚芳、潘悟云等）
3. **回答结构**：
[问题核心概念]
- 音韵地位：中古/上古音系定位
- 音值构拟：IPA标注（附发音描述）
- 历史演变：从上古到中古的演变路径
- 例证分析：经典文献用例（如《诗经》《切韵》）
- 现代留存：在现代方言/汉语中的痕迹
4. **教学辅助**：
- 复杂概念用表格对比呈现：
| 时期 | 声母特征 | 韵部系统 | 代表文献 |
|---|---|---|---|
| 上古音 | 复辅音存在 | 31韵部 | 诗经用韵 |
| 中古音 | 全浊声母 | 206韵 | 切韵音系 |
- 重要概念标注★符号
5. **交互风格**：
- 语言严谨但不晦涩
- 关键术语首次出现时加注解释
- 复杂理论分步骤讲解
-适当使用音韵学专业符号（如：*表示构拟形式）
6. **资料引用规范**：
- 古籍引用格式：《广韵》"东德红切"
- 现代著作：作者（年份）《著作》页数
- 优先推荐：丁邦新《音韵学讲义》、郑张尚芳《上古音系》
示例回答框架：
问："请解释'古无轻唇音'理论"
答：
【理论核心】清代钱大昕提出的声母演变规律
★ 古无轻唇音：上古汉语无[f]组声母，中古轻唇音（非敷奉微）来自上古重唇音（帮滂並明）
【音值演变】
上古（先秦）  中古（切韵）  现代普通话
*p-    →    帮母/p-/    →    b-/p-
（构拟IPA：*[p] → [p] → [pʰ]/[p]）
【例证分析】
1. "反"从"又"声：上古*panʔ → 中古帮母合韵*puan
2. "粪"从"番"声：上古*pənʔ → 中古帮母*pjən
【方言印证】
闽南语保留重唇读法：飞[pə] 斧[pɔ]
【延伸阅读】
王力（1980）《汉语史稿》第三章
"""

    def get_thread_safe_cursor(self):
        """为当前线程创建独立的数据库连接和游标"""
        # 获取当前线程ID
        thread_id = threading.current_thread().ident

        # 如果当前线程没有连接，创建一个新的
        if thread_id not in self.thread_connections:
            connection = create_db_connection()
            cursor = connection.cursor()
            self.thread_connections[thread_id] = (connection, cursor)

        # 返回当前线程的游标
        return self.thread_connections[thread_id][1]

    def close_thread_connections(self):
        """关闭所有线程的数据库连接"""
        # 创建一个新列表来存储需要关闭的连接
        connections_to_close = []

        # 遍历所有线程连接
        for thread_id, (connection, cursor) in self.thread_connections.items():
            # 只关闭当前线程的连接
            if thread_id == threading.current_thread().ident:
                try:
                    cursor.close()
                    connection.close()
                except:
                    pass  # 忽略关闭错误
            else:
                # 对于其他线程的连接，标记为需要关闭
                connections_to_close.append((thread_id, connection, cursor))

        # 清空线程连接字典
        self.thread_connections = {}

        # 处理需要关闭的其他线程连接
        for thread_id, connection, cursor in connections_to_close:
            try:
                # 尝试在创建线程中关闭连接
                # 注意：这只是一个安全措施，实际应用中可能需要更复杂的线程管理
                cursor.close()
                connection.close()
            except:
                pass  # 忽略关闭错误

    def closeEvent(self, event):
        """重写关闭事件，关闭所有数据库连接"""
        # 创建自定义对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("賢哉古音 - 退出確認")
        msg_box.setText("確實要退出？這將關閉所有窗口")
        msg_box.setIcon(QMessageBox.Question)

        # 创建自定义按钮
        yes_button = msg_box.addButton("去意已決", QMessageBox.YesRole)
        no_button = msg_box.addButton("再等等", QMessageBox.NoRole)
        yes_button.setCursor(Qt.PointingHandCursor)
        no_button.setCursor(Qt.PointingHandCursor)

        # 设置默认按钮
        msg_box.setDefaultButton(no_button)

        # 显示对话框并等待用户响应
        msg_box.exec_()

        if msg_box.clickedButton() == yes_button:
            # 用户确认退出 - 执行关闭操作
            # 1. 关闭所有子窗口
            self.close_all_child_windows()

            # 2. 关闭数据库连接
            if hasattr(self, 'cursor') and self.cursor:
                try:
                    self.cursor.close()
                except:
                    pass
            if hasattr(self, 'conn') and self.conn:
                try:
                    self.conn.close()
                except:
                    pass

            # 3. 关闭所有子线程连接
            self.close_thread_connections()

            # 4. 标记应用程序正在关闭
            self.is_closing = True

            # 5. 调用父类的关闭事件
            super().closeEvent(event)
        else:
            # 用户取消退出 - 忽略关闭事件
            event.ignore()

    def close_all_child_windows(self):
        """关闭所有打开的子窗口"""
        # 定义需要关闭的窗口列表
        windows = [
            self.search_window,
            self.shanggusheng_window,
            self.shangguyun_window,
            self.zhonggusheng_window,
            self.zhongguyun_window,
            self.update_log_window,
            self.fanqieduizhao_window,
            self.shengfu_sanbu_window,
            self.shengfu_zhonggusheng_window,
            self.shengyun_match_window
        ]

        # 安全关闭每个窗口
        for window in windows:
            if window is not None:
                try:
                    # 检查窗口是否有效且可见
                    if not sip.isdeleted(window) and window.isVisible():
                        window.close()
                except RuntimeError:
                    pass  # 忽略无效窗口引用

    # ————————————下面是bot图标代碼——————————————————————————
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

    # ————————————下面是bot调用ai的代碼——————————————————————————
    # 线程类用于异步调用API
    class DeepSeekThread(QThread):
        response_received = pyqtSignal(str)

        def __init__(self, api_call_func, user_input, parent=None):
            super().__init__(parent)
            self.api_call_func = api_call_func
            self.user_input = user_input
            self.parent_window = parent  # 保存父窗口引用
            self.progress_dialog = None  # 添加bot进度对话框变量

        def run(self):
            try:
                # 在这里不需要创建数据库连接，因为get_db_knowledge内部会使用线程安全的游标
                response = self.api_call_func(self.user_input)
                self.response_received.emit(response)
            except Exception as e:
                self.response_received.emit(f"处理请求时出错: {str(e)}")
            finally:
                # 确保在线程结束时清理自己的数据库连接
                self.cleanup_thread_connections()

        def cleanup_thread_connections(self):
            """清理当前线程的数据库连接"""
            if not self.parent_window:
                return

            thread_id = threading.current_thread().ident
            if thread_id in self.parent_window.thread_connections:
                connection, cursor = self.parent_window.thread_connections[thread_id]
                try:
                    cursor.close()
                except:
                    pass
                try:
                    connection.close()
                except:
                    pass
                # 从字典中移除
                del self.parent_window.thread_connections[thread_id]

    def ask_for_api_key(self):
        """创建自定义API密钥设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("賢哉Bot - 大模型API設置")
        # 禁用问号帮助按钮
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setFixedSize(500, 800)  # 增加高度以容纳重置按钮

        # 主布局
        layout = QVBoxLayout(dialog)

        # 标题
        title_label = QLabel("DeepSeek API設置")
        title_label.setFont(QFont("Aa古典刻本宋", 16, QFont.Bold))
        title_label.setStyleSheet("color: #580A00;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 创建自定义的文本浏览器类，禁用缩放
        class NonZoomableTextBrowser(QTextBrowser):
            def wheelEvent(self, event):
                # 检查是否按下了Ctrl键（通常用于缩放）
                if event.modifiers() & Qt.ControlModifier:
                    # 如果是Ctrl+滚轮事件，忽略它（禁用缩放）
                    event.ignore()
                    return
                # 其他情况（普通滚动）正常处理
                super().wheelEvent(event)

        # 说明文本区域
        help_text = NonZoomableTextBrowser()
        help_text.setOpenExternalLinks(True)  # 自动在浏览器中打开链接
        help_text.setHtml("""
        <h3>為什麼需要填API-key</h3>
          <li>賢哉Bot是基礎問答+DeepSeek智能問答的結合，當基礎問答無法解決問題時，將連接大模型解答。在軟件內使用大模型必須填寫API才能使用DeepSeek提供的服務。</li>
          <li>——————————————</li>
        <h3>如何獲取API-key</h3>
        <ol>
          <li>訪問 <a href='https://platform.deepseek.com/'>DeepSeek平台</a></li>
          <li>註冊/登入賬號</li>
          <li>進入<a href='https://platform.deepseek.com/api-keys'>API密鑰管理頁面</a></li>
          <li>點按"創建API"生成新key</li>
          <li>將生成的key粘貼到下方輸入框</li>
        </ol>
        <p><b>※</b>API-key僅顯示一次，請妥善保存！</p>
        """)
        help_text.setFont(QFont("IpaP", 13))
        help_text.setFixedHeight(500)
        layout.addWidget(help_text)

        # 输入区域
        input_layout = QFormLayout()

        # API密钥标签
        api_label = QLabel("API:")
        api_label.setFont(QFont("Aa古典刻本宋", 12))

        # API密钥输入框
        self.api_input = QLineEdit()
        self.api_input.setFont(QFont("IpaP", 12))
        self.api_input.setPlaceholderText("在此粘貼API-key")
        self.api_input.setEchoMode(QLineEdit.Password)  # 密码模式
        self.api_input.setMinimumHeight(40)

        # 如果已有密钥，显示掩码提示
        if self.api_key:
            self.api_input.setPlaceholderText("key已設置過，重新輸入可替換")

        # 显示/隐藏按钮
        toggle_btn = QToolButton()
        toggle_btn.setIcon(QIcon("eye_icon.png"))  # 准备一个眼睛图标
        toggle_btn.setCheckable(True)
        toggle_btn.setToolTip("顯示/隱藏key")
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.toggled.connect(lambda checked:
                                   self.api_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))

        # 将按钮添加到输入框右侧
        input_hbox = QHBoxLayout()
        input_hbox.addWidget(self.api_input)
        input_hbox.addWidget(toggle_btn)

        input_layout.addRow(api_label, input_hbox)

        # 按钮布局
        btn_layout = QHBoxLayout()

        # 重置按钮
        reset_btn = QPushButton("重置已保存的key")
        reset_btn.setFont(QFont("康熙字典體", 12))
        reset_btn.setStyleSheet("color: #BB4200;")
        reset_btn.setMinimumSize(100, 40)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(lambda: self.reset_api_key(dialog))

        # 添加按钮到布局
        btn_layout.addStretch()
        btn_layout.addWidget(reset_btn)

        # 确定和取消按钮布局
        action_btn_layout = QHBoxLayout()
        action_btn_layout.addStretch()

        # 确定按钮
        ok_btn = QPushButton("保存並退出")
        ok_btn.setFont(QFont("康熙字典體", 12))
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setMinimumSize(100, 40)

        ok_btn.clicked.connect(lambda: self.save_api_key_and_close(dialog))

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFont(QFont("康熙字典體", 12))
        cancel_btn.setStyleSheet("color: #66361B;")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setMinimumSize(100, 40)

        cancel_btn.clicked.connect(dialog.reject)

        action_btn_layout.addWidget(ok_btn)
        action_btn_layout.addWidget(cancel_btn)

        layout.addLayout(input_layout)
        layout.addLayout(btn_layout)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addLayout(action_btn_layout)

        # 显示对话框
        dialog.exec_()

    def reset_api_key(self, dialog):
        """重置API密钥"""
        reply = QMessageBox.question(
            dialog,
            "確認重置",
            "確實要重置API-key嗎？此操作将清除當前保存的key。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清除内存中的密钥
            self.api_key = None

            # 清除输入框
            self.api_input.clear()
            self.api_input.setPlaceholderText("API-key已重置，請輸入新key。")

            # 删除保存的密钥文件
            self.delete_api_key_file()

            # 更新UI状态
            QMessageBox.information(
                dialog,
                "重置成功",
                "API-key已重置。"
            )

    def delete_api_key_file(self):
        """删除保存的API密钥文件"""
        try:
            import os
            if os.path.exists("api_key.txt"):
                os.remove("api_key.txt")
                return True
        except Exception as e:
            print(f"删除API密钥文件失败: {str(e)}")
        return False

    def save_api_key_and_close(self, dialog):
        """保存API密钥并关闭对话框"""
        api_key = self.api_input.text().strip()

        # 如果输入为空，但已有密钥，视为保留原密钥
        if not api_key and self.api_key:
            dialog.accept()
            return

        if not api_key:
            QMessageBox.warning(dialog, "輸入錯誤", "API-key不能为空！")
            return

        # 简单验证密钥格式
        if len(api_key) < 20 or not api_key.startswith("sk-"):
            reply = QMessageBox.question(
                dialog,
                "格式警告",
                "key格式看起来不正确，確認保存？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 保存密钥
        self.api_key = api_key
        self.save_api_key()

        # 测试连接（可选）
        QMessageBox.information(dialog, "保存成功", "API-key已保存！")
        dialog.accept()

    def save_api_key(self):
        """保存API密钥到文件"""
        try:
            with open("api_key.txt", "w") as f:
                f.write(self.api_key)
            return True
        except Exception as e:
            print(f"保存API-key失败: {str(e)}")
            return False

    def load_api_key(self):
        """从文件加载API密钥"""
        try:
            with open("api_key.txt", "r") as f:
                self.api_key = f.read().strip()
            return True
        except FileNotFoundError:
            self.api_key = None
            return False
        except Exception as e:
            print(f"加载API密钥失败: {str(e)}")
            self.api_key = None
            return False

    def configure_api(self):
        """打开API设置对话框"""
        if self.ask_for_api_key():
            QMessageBox.information(self, "成功", "API已保存！")
            return True
        return False

    def call_deepseek_api(self, user_input):
        """调用DeepSeek API获取回复"""
        thread_id = threading.current_thread().ident
        try:
            if not self.api_key:
                if not self.ask_for_api_key():
                    return "API-key未設置，僅能使用基礎问答。"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 确保有对话历史属性
            if not hasattr(self, 'conversation_history'):
                self.conversation_history = []

            # 构建当前消息
            current_message = {"role": "user", "content": user_input}

            # 构建完整消息列表（最近的历史 + 当前消息）
            messages = []

            # 1. 添加系统提示词（如果存在）
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            # 2. 添加历史对话消息
            if self.conversation_history:
                # 确保只保留有效的消息对象
                valid_history = [msg for msg in self.conversation_history
                                 if isinstance(msg, dict) and 'role' in msg and 'content' in msg]
                messages.extend(valid_history[-3:])  # 只保留最近的3条历史消息
            # 3. 注入数据库知识 - 关键修改部分
            db_knowledge = self.get_db_knowledge(user_input)
            if db_knowledge:
                messages.append({
                    "role": "system",
                    "content": f"以下是从音韵学数据库中提取的相关知识：\n{db_knowledge}\n请基于这些知识回答用户的问题。"
                })
            # 4. 添加当前用户消息
            messages.append({"role": "user", "content": user_input})
            payload = {
                "model": self.model_name,
                "messages": messages,  # 使用修正后的 messages 列表
                "temperature": 0.7,
                "max_tokens": 2000
            }
            print(messages)
            try:

                # 发送请求（增加超时时间）
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=self.api_timeout  # 使用配置的超时时间
                )

                if response.status_code == 200:
                    # 获取并保存回复内容
                    response_data = response.json()
                    reply_content = response_data['choices'][0]['message']['content'].strip()

                    # 更新对话历史
                    self.conversation_history.append(current_message)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": reply_content
                    })

                    # 限制历史记录长度（避免token超限）
                    if len(self.conversation_history) > 6:  # 保留最近的几组对话
                        self.conversation_history = self.conversation_history[-6:]
                    return reply_content

                else:
                    # 尝试解析错误详情
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', '未知错误')
                        return f"API错误: {response.status_code}\n{error_msg}"
                    except:
                        return f"API错误: {response.status_code}\n{response.text[:200]}"
            except requests.exceptions.Timeout:
                return "網絡超時，簡化您的問題或稍後再試"
            except Exception as e:
                return f"請求異常: {str(e)}"
        finally:
            # 确保清理当前线程的连接
            if thread_id in self.thread_connections:
                connection, cursor = self.thread_connections[thread_id]
                try:
                    cursor.close()
                except:
                    pass
                try:
                    connection.close()
                except:
                    pass
                del self.thread_connections[thread_id]

    def markdown_to_html(self, text):
        """
        将 Markdown 转换为安全的 HTML
        """
        # 转换 Markdown 为 HTML
        html_content = markdown.markdown(text)

        # 定义允许的标签列表
        allowed_tags = {'p', 'br', 'ul', 'ol', 'li', 'strong', 'em',
                        'blockquote', 'code', 'pre', 'h1', 'h2', 'h3',
                        'h4', 'h5', 'h6', 'a'}

        # 安全清理HTML
        def clean_html(html_str):
            # 第一步：转义所有特殊字符
            escaped = html.escape(html_str)

            # 第二步：恢复允许的标签
            for tag in allowed_tags:
                # 处理开始标签
                escaped = re.sub(
                    r'&lt;(' + tag + r')(\s[^&]*?)?&gt;',
                    lambda m: f'<{m.group(1)}{m.group(2) or ""}>',
                    escaped
                )
                # 处理结束标签
                escaped = escaped.replace(f'&lt;/{tag}&gt;', f'</{tag}>')

            # 第三步：清理属性（只保留href）
            escaped = re.sub(
                r'<a\s+(.*?)>',
                lambda m: '<a ' + ''.join(
                    f'href="{v}"'
                    for k, v in re.findall(r'href="([^"]*)"', m.group(1))
                ) + '>',
                escaped
            )

            return escaped

        return clean_html(html_content)

    # 添加从数据库提取知识的方法
    def get_db_knowledge(self, user_input):
        """从数据库中提取与用户输入相关的音韵学知识"""
        # 获取线程安全的游标
        cursor = self.get_thread_safe_cursor()
        # 提取用户输入中的汉字（每个字符）
        chinese_chars = [char for char in user_input if '\u4e00' <= char <= '\u9fff']

        if not chinese_chars:
            return ""

        # 去重
        unique_chars = set(chinese_chars)
        knowledge = []

        for char in unique_chars:
            # 查询数据库
            cursor.execute("SELECT * FROM ancienttable1 WHERE 字頭=?", (char,))
            results = cursor.fetchall()

            if results:
                char_knowledge = [f"字【{char}】的音韵信息："]
                for idx, row in enumerate(results, 1):
                    # 根据表结构提取知识
                    char_knowledge.append(
                        f"上古声母: {row['上古聲']}, "
                        f"上古韵部: {row['上古韻']}; "
                        f"中古声母: {row['中古聲']}, "
                        f"中古韵部: {row['中古韻']}, "
                        f"声调: {row['中古調']}, "
                        f"等: {row['中古等']}, "
                        f"开合: {row['開合']}, "
                        f"声符: {row['聲符']}"
                    )
                knowledge.append("\n".join(char_knowledge))

        # 如果没有找到具体字符的知识，尝试提取相关韵部或声母的知识
        if not knowledge:
            # 提取韵部关键词
            rhyme_keywords = ["韵", "部", "韵部", "韻", "韻部"]
            if any(kw in user_input for kw in rhyme_keywords):
                # 随机提取一些韵部知识作为示例
                cursor.execute("SELECT DISTINCT 上古韻, 中古韻 FROM ancienttable1 LIMIT 3")
                rhyme_results = cursor.fetchall()
                if rhyme_results:
                    knowledge.append("韵部知识示例:")
                    for row in rhyme_results:
                        knowledge.append(f"上古韵部: {row['上古韻']}, 对应中古韵部: {row['中古韻']}")

            # 提取声母关键词
            initial_keywords = ["声", "母", "声母", "聲", "聲母"]
            if any(kw in user_input for kw in initial_keywords):
                # 随机提取一些声母知识作为示例
                cursor.execute("SELECT DISTINCT 上古聲, 中古聲 FROM ancienttable1 LIMIT 3")
                initial_results = cursor.fetchall()
                if initial_results:
                    knowledge.append("声母知识示例:")
                    for row in initial_results:
                        knowledge.append(f"上古声母: {row['上古聲']}, 对应中古声母: {row['中古聲']}")

        return "\n\n".join(knowledge) if knowledge else ""

    # ————————————下面是bot功能代碼——————————————————————————

    def reset_variables_on_close(self, event):
        """当聊天窗口关闭时重置变量"""
        self.is_waiting_for_column_choice = False
        self.pending_character = None
        event.accept()  # 确保窗口正常关闭
        print("bot窗口將關閉……")

    def open_bot_dialog(self):  # ————————————————————————————
        """创建一个聊天窗口"""

        # 定义清除引用的局部函数
        def clear_bot_window_ref():
            """安全清除bot窗口引用"""
            print("清除bot窗口引用")
            if getattr(self, 'bot_chat_window', None) is not None:
                try:
                    if sip.isdeleted(self.bot_chat_window):
                        self.bot_chat_window = None
                except:
                    self.bot_chat_window = None

        # 安全访问窗口引用
        window = getattr(self, 'bot_chat_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.bot_chat_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("bot窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"bot窗口引用异常: {e}")
                self.bot_chat_window = None
        # 创建新窗口
        print("打开bot窗口")

        self.bot_chat_window = QMainWindow(self)
        self.conversation_history = []  # 每次打开聊天窗口时重置历史
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
        self.bot_chat_window.setGeometry(400, 200, 700, 1000)
        # self.bot_chat_window.setFixedSize(700, 1000)

        # 创建主部件和布局
        central_widget = QWidget(self.bot_chat_window)
        layout = QVBoxLayout(central_widget)

        # 聊天记录显示区域（使用 ScrollArea）
        # 创建文本编辑区域替代原来的气泡布局
        self.chat_layout = QTextEdit(self.bot_chat_window)
        self.chat_layout.setReadOnly(True)  # 设置为只读
        self.chat_layout.setFont(QFont("等线", 14))
        self.chat_layout.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)

        # 创建滚动区域并添加文本编辑框
        scroll_area = QScrollArea(self.bot_chat_window)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.chat_layout)

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

        # ========== 新增：API设置按钮 ==========
        api_setting_button = QPushButton("設置", self.bot_chat_window)
        api_setting_button.setFont(QFont("Aa古典刻本宋", 14))
        api_setting_button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: #6c757d;
                                    color: white; 
                                    padding: 10px;
                                    border-radius: 15px; 
                                    margin-left: 10px;
                                }}
                                QPushButton:hover {{
                            font-weight: bold;
                            background-color: #5a6268;
                        }}
                """)
        api_setting_button.setCursor(Qt.PointingHandCursor)
        api_setting_button.clicked.connect(self.configure_api)
        # =====================================

        # 将输入框和按钮添加到输入布局
        input_layout.addWidget(self.input_field)  # 输入框
        input_layout.addWidget(send_button)  # 发送按钮
        input_layout.addWidget(api_setting_button)  # 设置按钮

        # 将输入布局加入主布局
        layout.addLayout(input_layout)

        # 确保输入框获取焦点
        self.input_field.setFocus()  # 让输入框获取焦点，光标开始闪烁

        # 让 bot 先发送一条消息
        self.add_message("賢哉Bot", "我是賢哉Bot，請隨時向我提問。輸入help以獲取幫助", is_user=False)

        # 如果API密钥未设置，添加提示消息
        if not self.api_key:
            self.add_message("賢哉Bot", "⚠️未檢測到API-key，請點按'設置'按鈕填寫DeepSeek API-key。", is_user=False)

            # 设置中心部件
        self.bot_chat_window.setCentralWidget(central_widget)

        # 设置关闭时自动销毁
        self.bot_chat_window.setAttribute(Qt.WA_DeleteOnClose)
        self.bot_chat_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_bot_window_conn'):
            try:
                self.bot_chat_window.destroyed.disconnect(self._bot_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._bot_window_conn = clear_bot_window_ref
        self.bot_chat_window.destroyed.connect(self._bot_window_conn)

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
        """处理 bot 的回应"""
        response = self.handle_bot_response(user_input)
        if response:  # 如果 response 不为 None，才添加消息
            self.add_message("賢哉Bot", response, is_user=False)

        # 发送消息后重新设置焦点到输入框
        self.input_field.setFocus()

    def add_message(self, sender, message, is_user=False):
        """添加消息到聊天窗口"""
        if is_user:
            prefix = "您: "
            color = "#0088CC"  # 用户消息为蓝色
            display_message = message  # 用户消息不需要转换
        else:
            prefix = "賢哉Bot: "
            # 根据内容判断是否为错误消息
            color = "#CC0000" if "⚠️" in message else "#7D2D00"  # 错误消息红色，普通消息绿色
            # 转换机器人消息
            display_message = self.markdown_to_html(message)

        # 创建带格式的消息
        formatted_message = f"<div style='margin: 10px 0;'>"
        formatted_message += f"<span style='font-weight: bold; color: {color};'>{prefix}</span>"
        formatted_message += f"<span style='color: #333333;'>{display_message}</span>"
        formatted_message += "</div>"

        # 添加消息到文本区域
        self.chat_layout.append(formatted_message)

        # 自动滚动到底部
        self.chat_layout.ensureCursorVisible()

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
            return "可以直接輸入韻部、聲母、單個字。例如“東”，輸入后根據bot提示選擇查字、查聲母或查韻部。填寫API可連接到DeepSeek進行智能問答。"
        elif ("你是谁" in user_input or "你是誰" in user_input or "能幹什麼" in user_input or "能做什麼"
              in user_input or "能干什么" in user_input or "能做什么" in user_input or "你好" in user_input):
            return "我是賢哉Bot，請隨時向我提問。輸入help以獲取幫助。"
        else:
            if self.api_key:  # 如果有API密钥
                # 确保聊天窗口已打开
                if not self.bot_chat_window or not self.bot_chat_window.isVisible():
                    self.open_bot_dialog()

                # 显示进度对话框
                self.show_progress_dialog("獲取DeepSeek的回答，預計耗時0~3分鐘...")
                # 创建并启动API调用线程
                self.deepseek_thread = self.DeepSeekThread(self.call_deepseek_api, user_input)
                self.deepseek_thread.response_received.connect(self.handle_deepseek_response)
                self.deepseek_thread.start()

                return None  # 返回None，后续通过信号处理回复

            else:
                # 如果没有API密钥，提示用户设置
                return "⚠️API未設置，請點按'設置'按鈕以輸入DeepSeek API-key。"

    def handle_deepseek_response(self, response):
        """处理DeepSeek API返回的响应"""
        # 隐藏进度对话框
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except:
                pass
            self.progress_dialog = None

        try:
            # 将 Markdown 转换为 HTML
            html_content = self.markdown_to_html(response)

            # 添加发送者信息
            formatted_html = f"""
                <div style="margin: 5px 0;">
                    <span style="font-weight: bold; color: #7D2D00;">賢哉Bot: </span>
                    {html_content}
                </div>
                """

            # 显示HTML格式的回复
            self.chat_layout.append(formatted_html)
        except Exception as e:
            # 如果转换失败，使用纯文本显示
            print(f"Markdown转换失败: {str(e)}")
            self.add_message("賢哉Bot", response, is_user=False)

            # 自动滚动到底部
        self.chat_layout.ensureCursorVisible()

        # 发送消息后重新设置焦点到输入框
        self.input_field.setFocus()

    def process_character_query(self, character):
        """处理字符查询逻辑"""
        # 获取线程安全的游标
        cursor = self.get_thread_safe_cursor()
        # 检查字符是否出现在上古韻、中古聲、中古韻列中
        columns_to_check = ["上古韻", "中古聲", "中古韻"]
        results = {}

        for column in columns_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM ancienttable1 WHERE {column}=?", (character,))
            count = cursor.fetchone()[0]
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
        # 获取线程安全的游标
        cursor = self.get_thread_safe_cursor()

        if user_input in ["上古韻", "中古聲", "中古韻"]:
            # 查询指定列的值
            cursor.execute(f"SELECT 字頭 FROM ancienttable1 WHERE {user_input}=?", (self.pending_character,))
            values = cursor.fetchall()
            response = f"所有 '{user_input}' 為 '{self.pending_character}' 的字頭：\n"
            for row in values:
                response += f"{row[0]}\n"
            self.is_waiting_for_column_choice = False
            return response
        elif user_input == "字頭":
            # 查询字头信息
            self.is_waiting_for_column_choice = False  # 重置标志位
            return self.query_character_info(self.pending_character)
        else:
            return "輸入無效\n請輸列名(如'中古聲'或'字頭')\n輸入“取消”以停止當前查詢"

    def query_column_values(self, column, value):
        """查询指定列的值"""
        self.cursor.execute(f"SELECT 字頭 FROM ancienttable1 WHERE {column}=?", (value,))
        return self.cursor.fetchall()

    def query_character_info(self, character):
        """查询字头信息"""
        # 获取线程安全的游标
        cursor = self.get_thread_safe_cursor()
        cursor.execute("SELECT * FROM ancienttable1 WHERE 字頭=?", (character,))
        results = cursor.fetchall()  # 获取所有结果
        result_count = len(results)  # 结果数量

        if result_count == 0:
            return f"未找到'{character}'字的信息。"
        elif result_count == 1:
            result_strings = []  # 用来存储每一条数据对应的结果字符串
            for result in results:
                # 表中有9列数据
                col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = result

                # 构建单条结果的字符串
                result_string = (
                    f"“{col2}”是上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。聲符是{col10}。備註{col11}"
                )
                result_strings.append(result_string)
            # 将所有结果字符串拼接在一起，用换行分隔
            return "\n".join(result_strings)
        else:
            # 如果有多条结果（多音字），依次显示每个读音的详细信息
            for i, result in enumerate(results, start=1):
                # 假设表中有9列数据
                col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = result
                result_string_1 = (
                    f"“{col2}”是上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。聲符是{col10}。備註{col11}"
                )
                result_string_i = (
                    f"上古[{col3}]母字，屬於{col4}部；"
                    f"中古{col5}母字，屬於{col6}部，"
                    f"{col8}等{col9}口{col7}聲字。聲符是{col10}。備註{col11}"
                )
                if i == 1:
                    response = f"第 {i} 个读音：\n{result_string_1}"
                else:
                    response = f"第 {i} 个读音：\n{result_string_i}"
                self.add_message("賢哉Bot", response, is_user=False)
            return None  # 返回 None，避免重复添加消息

    def show_progress_dialog(self, message):
        """显示进度对话框"""
        # 确保聊天窗口存在
        if not self.bot_chat_window or not self.bot_chat_window.isVisible():
            return
        # 关闭现有的进度对话框
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except:
                pass
            self.progress_dialog = None

        self.progress_dialog = QProgressDialog(message, "取消", 0, 0, self.bot_chat_window)
        self.progress_dialog.setWindowTitle("請稍候")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)  # 移除取消按钮
        self.progress_dialog.setRange(0, 0)  # 设置为不确定进度模式
        self.progress_dialog.setMinimumDuration(0)  # 立即显示

        # 设置对话框样式
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: white;

            }
            QLabel {
                font-family: "康熙字典體";
                font-size: 14pt;
                color: #8B2500; 
                text-align: center;
            }
        """)

        self.progress_dialog.show()

    # ————————————下面是打开各种窗口的代碼——————————————————————————
    def open_search_chara_window(self):
        # 定义清除引用的局部函数
        def clear_search_ref():
            """安全清除窗口引用"""
            print("清除查字窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'search_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.search_window):
                        self.search_window = None
                except:
                    self.search_window = None

        # 安全访问窗口引用
        window = getattr(self, 'search_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.search_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("查字窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"查字窗口引用异常: {e}")
                self.search_window = None

        # 创建新窗口
        print("打开了查字窗口")
        self.search_window = SearchCharaWindow()
        # 设置关闭时自动销毁
        self.search_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.search_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_search_window_conn'):
            try:
                self.search_window.destroyed.disconnect(self._search_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._search_window_conn = clear_search_ref
        self.search_window.destroyed.connect(self._search_window_conn)

    def open_shengyun_match_window(self):
        # 定义清除引用的局部函数
        def clear_shengyun_match_window_ref():
            """安全清除窗口引用"""
            print("清除查字窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'shengyun_match_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.shengyun_match_window):
                        self.shengyun_match_window = None
                except:
                    self.shengyun_match_window = None

        # 安全访问窗口引用
        window = getattr(self, 'shengyun_match_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.shengyun_match_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("聲韻匹配窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"聲韻匹配窗口引用异常: {e}")
                self.shengyun_match_window = None

        # 创建新窗口
        print("打开了聲韻匹配窗口")
        self.shengyun_match_window = ShengyunMatchWindow()
        # 设置关闭时自动销毁
        self.shengyun_match_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.shengyun_match_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_shengyun_match_window_conn'):
            try:
                self.shengyun_match_window.destroyed.disconnect(self._shengyun_match_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._shengyun_match_window_conn = clear_shengyun_match_window_ref
        self.shengyun_match_window.destroyed.connect(self._shengyun_match_window_conn)

    def open_shanggusheng_window(self):
       # 定义清除引用的局部函数
        def clear_shanggusheng_window_ref():
            """安全清除窗口引用"""
            print("清除上古声窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'shanggusheng_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.shanggusheng_window):
                        self.shanggusheng_window = None
                except:
                    self.shanggusheng_window = None

        # 安全访问窗口引用
        window = getattr(self, 'shanggusheng_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.shanggusheng_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("上古声窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"上古声窗口引用异常: {e}")
                self.shanggusheng_window = None

        # 创建新窗口
        print("打开上古声窗口")
        self.shanggusheng_window = ShanggushengWindow()
        # 设置关闭时自动销毁
        self.shanggusheng_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.shanggusheng_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_shanggusheng_window_conn'):
            try:
                self.shanggusheng_window.destroyed.disconnect(self._shanggusheng_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._shanggusheng_window_conn = clear_shanggusheng_window_ref
        self.shanggusheng_window.destroyed.connect(self._shanggusheng_window_conn)

    def open_zhonggusheng_window(self):
       # 定义清除引用的局部函数
        def clear_zhonggusheng_window_ref():
            """安全清除窗口引用"""
            print("清除中古声窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'zhonggusheng_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.zhonggusheng_window):
                        self.zhonggusheng_window = None
                except:
                    self.zhonggusheng_window = None

        # 安全访问窗口引用
        window = getattr(self, 'zhonggusheng_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.zhonggusheng_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("中古声窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"中古声窗口引用异常: {e}")
                self.zhonggusheng_window = None

        # 创建新窗口
        print("打开中古声窗口")
        self.zhonggusheng_window = ZhonggushengWindow()
        # 设置关闭时自动销毁
        self.zhonggusheng_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.zhonggusheng_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_zhonggusheng_window_conn'):
            try:
                self.zhonggusheng_window.destroyed.disconnect(self._zhonggusheng_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._zhonggusheng_window_conn = clear_zhonggusheng_window_ref
        self.zhonggusheng_window.destroyed.connect(self._zhonggusheng_window_conn)

    def open_shangguyun_window(self):
        # 定义清除引用的局部函数
        def clear_shangguyun_window_ref():
            """安全清除窗口引用"""
            print("清除上古韵窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'shangguyun_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.shangguyun_window):
                        self.shangguyun_window = None
                except:
                    self.shangguyun_window = None

        # 安全访问窗口引用
        window = getattr(self, 'shangguyun_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.shangguyun_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("上古韵窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"上古韵窗口引用异常: {e}")
                self.shangguyun_window = None

        # 创建新窗口
        print("打开上古韵窗口")
        self.shangguyun_window = ShangguyunWindow()
        # 设置关闭时自动销毁
        self.shangguyun_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.shangguyun_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_shangguyun_window_conn'):
            try:
                self.shangguyun_window.destroyed.disconnect(self._shangguyun_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._shangguyun_window_conn = clear_shangguyun_window_ref
        self.shangguyun_window.destroyed.connect(self._shangguyun_window_conn)

    def open_zhongguyun_window(self):
       # 定义清除引用的局部函数
        def clear_zhongguyun_window_ref():
            """安全清除窗口引用"""
            print("清除中古韵窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'zhongguyun_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.zhongguyun_window):
                        self.zhongguyun_window = None
                except:
                    self.zhongguyun_window = None

        # 安全访问窗口引用
        window = getattr(self, 'zhongguyun_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.zhongguyun_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showMaximized()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("中古韵窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"中古韵窗口引用异常: {e}")
                self.zhongguyun_window = None

        # 创建新窗口
        print("打开中古韵窗口")
        self.zhongguyun_window = ZhongguyunWindow()
        # 设置关闭时自动销毁
        self.zhongguyun_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.zhongguyun_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_zhongguyun_window_conn'):
            try:
                self.zhongguyun_window.destroyed.disconnect(self._zhongguyun_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._zhongguyun_window_conn = clear_zhongguyun_window_ref
        self.zhongguyun_window.destroyed.connect(self._zhongguyun_window_conn)

    def open_shengfu_zhonggusheng_window(self):
      # 定义清除引用的局部函数
        def clear_shengfu_zhonggusheng_window_ref():
            """安全清除窗口引用"""
            print("清除声符-中古声窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'shengfu_zhonggusheng_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.shengfu_zhonggusheng_window):
                        self.shengfu_zhonggusheng_window = None
                except:
                    self.shengfu_zhonggusheng_window = None

        # 安全访问窗口引用
        window = getattr(self, 'shengfu_zhonggusheng_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.shengfu_zhonggusheng_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showMaximized()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("声符-中古声窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"声符-中古声窗口引用异常: {e}")
                self.shengfu_zhonggusheng_window = None

        # 创建新窗口
        print("打开声符-中古声窗口")
        self.shengfu_zhonggusheng_window = Shengfu_zhonggushengWindow()
        # 设置关闭时自动销毁
        self.shengfu_zhonggusheng_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.shengfu_zhonggusheng_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_shengfu_zhonggusheng_window_conn'):
            try:
                self.shengfu_zhonggusheng_window.destroyed.disconnect(self._shengfu_zhonggusheng_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._shengfu_zhonggusheng_window_conn = clear_shengfu_zhonggusheng_window_ref
        self.shengfu_zhonggusheng_window.destroyed.connect(self._shengfu_zhonggusheng_window_conn)

    def open_shengfu_sanbu_window(self):
      # 定义清除引用的局部函数
        def clear_shengfu_sanbu_window_ref():
            """安全清除窗口引用"""
            print("清除聲符散佈窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'shengfu_sanbu_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.shengfu_sanbu_window):
                        self.shengfu_sanbu_window = None
                except:
                    self.shengfu_sanbu_window = None

        # 安全访问窗口引用
        window = getattr(self, 'shengfu_sanbu_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.shengfu_sanbu_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showMaximized()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("聲符散佈窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"聲符散佈窗口引用异常: {e}")
                self.shengfu_sanbu_window = None

        # 创建新窗口
        print("打开聲符散佈窗口")
        self.shengfu_sanbu_window = ShengfuSanbuWindow(cache_data=self.shengfu_sanbu_data_cache)
        # 设置关闭时自动销毁
        self.shengfu_sanbu_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.shengfu_sanbu_window.show()

        # 当窗口加载完成后更新缓存
        self.shengfu_sanbu_window.data_loaded.connect(self.update_cache)

        # 确保只有一个清除引用连接
        if hasattr(self, '_shengfu_sanbu_window_conn'):
            try:
                self.shengfu_sanbu_window.destroyed.disconnect(self._shengfu_sanbu_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._shengfu_sanbu_window_conn = clear_shengfu_sanbu_window_ref
        self.shengfu_sanbu_window.destroyed.connect(self._shengfu_sanbu_window_conn)
    def update_cache(self, cache_data):
        """更新缓存数据"""
        self.shengfu_sanbu_data_cache = cache_data
        print("聲符散佈數據已緩存")

    def open_fanqieduizhao_window(self):
       # 定义清除引用的局部函数
        def clear_fanqieduizhao_window_ref():
            """安全清除窗口引用"""
            print("清除反切對照窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'fanqieduizhao_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.fanqieduizhao_window):
                        self.fanqieduizhao_window = None
                except:
                    self.fanqieduizhao_window = None

        # 安全访问窗口引用
        window = getattr(self, 'fanqieduizhao_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.fanqieduizhao_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("反切對照窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"反切對照窗口引用异常: {e}")
                self.fanqieduizhao_window = None

        # 创建新窗口
        print("打开反切對照窗口")
        self.fanqieduizhao_window = FanqieCompareWindow()
        # 设置关闭时自动销毁
        self.fanqieduizhao_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.fanqieduizhao_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_fanqieduizhao_window_conn'):
            try:
                self.fanqieduizhao_window.destroyed.disconnect(self._fanqieduizhao_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._fanqieduizhao_window_conn = clear_fanqieduizhao_window_ref
        self.fanqieduizhao_window.destroyed.connect(self._fanqieduizhao_window_conn)

    # 打开更新日志窗口的函数
    def open_update_log_window(self):
       # 定义清除引用的局部函数
        def clear_update_log_window_ref():
            """安全清除窗口引用"""
            print("清除关于窗口引用")
            # 只有在引用仍然指向同一窗口时才清除
            if getattr(self, 'update_log_window', None) is not None:
                try:
                    # 检查对象是否仍然有效
                    if sip.isdeleted(self.update_log_window):
                        self.update_log_window = None
                except:
                    self.update_log_window = None

        # 安全访问窗口引用
        window = getattr(self, 'update_log_window', None)
        if window is not None:
            try:
                # 检查窗口是否有效且可见
                if sip.isdeleted(window) or not window.isVisible():
                    # 窗口无效或已关闭
                    self.update_log_window = None
                else:
                    # 处理最小化状态
                    if window.isMinimized():
                        window.showNormal()
                    # 激活并置顶
                    window.activateWindow()
                    window.raise_()
                    print("关于窗口已激活并置顶")
                    return
            except RuntimeError as e:
                # 处理PyQt对象已被删除的情况
                print(f"关于窗口引用异常: {e}")
                self.update_log_window = None

        # 创建新窗口
        print("打开关于窗口")
        self.update_log_window = UpdateLogWindow()
        # 设置关闭时自动销毁
        self.update_log_window.setAttribute(Qt.WA_DeleteOnClose)
        # 显示窗口
        self.update_log_window.show()

        # 确保只有一个清除引用连接
        if hasattr(self, '_update_log_window_conn'):
            try:
                self.update_log_window.destroyed.disconnect(self._update_log_window_conn)
            except TypeError:
                pass

        # 创建新连接
        self._update_log_window_conn = clear_update_log_window_ref
        self.update_log_window.destroyed.connect(self._update_log_window_conn)

#聲韻匹配測試遊戲————————————————————————————————————————————————————————————
class ShengyunMatchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 聲韻匹配試煉場【嘗嘗賢淡】")
        self.setGeometry(110, 200, 1600, 1000)
        self.setFixedWidth(1600)
        self.setMinimumHeight(800)
        # 调用外部图标设置函数
        set_window_icon(self, 'icon.ico')  # 直接使用外部函数
        # 使用外部数据库连接函数创建连接
        self.conn = create_db_connection()  # 调用外部函数创建连接
        self.cursor = self.conn.cursor()  # 创建游标

        self.progress_timer = None  # 确保初始化

        self.current_difficulty = "normal"
        self.current_mode = "zhonggusheng"  # 新增：当前选择的表
        self.current_character = ""
        self.correct_values = []
        self.options = []
        self.correct_option_index = -1
        self.answer_buttons = []
        self.base_path = self.get_base_path()
        self.initUI()

    def get_base_path(self):
        """获取资源文件的基础路径（兼容PyInstaller打包环境）"""
        if getattr(sys, 'frozen', False):
            # 打包后的exe执行路径
            return sys._MEIPASS
        else:
            # 正常Python脚本执行路径
            return os.path.dirname(os.path.abspath(__file__))

    def resource_path(self, relative_path):
        """获取资源的绝对路径"""
        return os.path.join(self.base_path, relative_path)

    def initUI(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 初始化统计变量
        self.total_questions = 0
        self.correct_answers = 0

        # ===== 顶部布局 =====
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # ===== 顶部容器（添加边框）=====
        top_container = QWidget()
        top_container.setObjectName("topContainer")  # 添加对象名
        top_container.setStyleSheet("""
                    #topContainer {  /* 使用ID选择器精确指定 */
                        border: 2px solid #5D4037;  /* 深棕色边框 */
                        border-radius: 8px;         /* 圆角 */
                    }
               """)
        top_layout = QHBoxLayout(top_container)  # 使用容器包裹顶部布局
        main_layout.addWidget(top_container)  # 将容器添加到主布局

        # ==== 左侧区域：模式选择 ====
        left_layout = QVBoxLayout()
        top_layout.addLayout(left_layout)

        # 模式选择标签
        table_label = QLabel("選擇試煉模式:")
        table_label.setFont(QFont("康熙字典體", 16))
        table_label.setStyleSheet("""
                    color: #662A1D; 
                    margin-right: 10px;
                    background-color: transparent;  /* 透明背景 */
                """)
        left_layout.addWidget(table_label)

        # 下拉选择框
        self.table_combo = QComboBox()
        self.table_combo.addItem("[字-中古聲母] 匹配")
        self.table_combo.addItem("[字-中古韻部] 匹配")
        self.table_combo.addItem("[字-上古韻部] 匹配")
        self.table_combo.setFont(QFont("康熙字典體", 15))
        self.table_combo.setCursor(Qt.PointingHandCursor)
        self.table_combo.setFixedHeight(50)
        self.table_combo.currentIndexChanged.connect(self.mode_changed)
        left_layout.addWidget(self.table_combo)

        # ==== 中间区域：难度选择组 ====
        center_layout = QHBoxLayout()
        top_layout.addLayout(center_layout, 1)  # 添加伸缩因子使居中

        # 难度选择组
        difficulty_group = QGroupBox("試煉難度")
        difficulty_group.setFont(QFont("康熙字典體", 14))
        difficulty_layout = QHBoxLayout()
        difficulty_group.setLayout(difficulty_layout)
        self.difficulty_normal = QRadioButton("普通（默認）")
        self.difficulty_normal.setChecked(True)
        self.difficulty_hard = QRadioButton("困難（限時10秒）")
        self.difficulty_hell = QRadioButton("地獄（限時5秒）")
        for btn in [self.difficulty_normal, self.difficulty_hard, self.difficulty_hell]:
            btn.setFont(QFont("康熙字典體", 14))
            btn.setCursor(Qt.PointingHandCursor)
            difficulty_layout.addWidget(btn)
        # 连接信号
        self.difficulty_normal.toggled.connect(self.update_difficulty)
        self.difficulty_hard.toggled.connect(self.update_difficulty)
        self.difficulty_hell.toggled.connect(self.update_difficulty)

        center_layout.addWidget(difficulty_group, alignment=Qt.AlignCenter)  # 居中对齐
        # ==== 右侧区域：统计标签 ====
        right_layout = QHBoxLayout()
        top_layout.addLayout(right_layout)

        # 创建统计标签
        self.stats_label = QLabel("已答0題，做對0題 | 正確率: 0%")
        self.stats_label.setFont(QFont("康熙字典體", 14))
        self.stats_label.setStyleSheet("""
                        color: #5D4037;
                        background-color: #f7eee6;
                        border: 2px solid #8D6E63;
                        border-radius: 10px;
                        padding: 5px 15px;
                        margin-left: 15px;
                    """)
        right_layout.addWidget(self.stats_label)

        # ===== Bot提示区域 =====
        bot_layout = QHBoxLayout()
        bot_layout.setContentsMargins(10, 10, 10, 10)  # 设置边距
        bot_layout.setSpacing(10)  # 设置组件间距
        main_layout.addLayout(bot_layout)
        # 添加伸缩空间
        bot_layout.addStretch(1)
        # Bot头像
        self.bot_icon = QLabel()
        self.bot_icon.setFixedSize(70, 70)
        self.bot_icon.setScaledContents(True)
        self.set_bot_icon('bot.png')  # 初始图标
        bot_layout.addWidget(self.bot_icon)

        # 提示气泡
        self.hint_bubble = QLabel()
        self.hint_bubble.setFont(QFont("宋体", 16))
        self.hint_bubble.setStyleSheet("""
            background-color: #f0f8ff;
            color: #333;
            border: 2px solid #c0d6e4;
            border-radius: 15px;
            padding: 15px;
            margin: 5px;
        """)
        self.hint_bubble.setWordWrap(True)
        self.hint_bubble.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.hint_bubble.setMinimumHeight(85)
        bot_layout.addWidget(self.hint_bubble, 1)  # 设置拉伸因子为1

        # 添加伸缩空间
        bot_layout.addStretch(1)

        # ===== 字符显示区域 =====
        self.char_label = QLabel()
        self.char_label.setFont(QFont("宋体", 120))
        self.char_label.setAlignment(Qt.AlignCenter)
        self.char_label.setStyleSheet("""
            color: #8B4513;
            background-color: #fdfbf9;
            border: 3px solid #8B4513;
            border-radius: 20px;
            padding: 20px;
            margin: 20px;
        """)
        main_layout.addWidget(self.char_label)

        # ===== 选项按钮区域 =====
        options_layout = QHBoxLayout()  # 改为水平布局
        main_layout.addLayout(options_layout)
        options_layout.setSpacing(30)  # 设置按钮间距

        # 创建选项按钮
        self.option_buttons = []
        for i in range(4):
            btn = QPushButton()
            btn.setFont(QFont("康熙字典體", 28))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(200, 130)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ebd4bf;
                    color: #5D4037;
                    border: 3px solid #8D6E63;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #D7C29D;
                    border: 4px solid #6D4C41;
                }
            """)
            btn.clicked.connect(lambda _, idx=i: self.check_answer(idx))
            self.option_buttons.append(btn)
            options_layout.addWidget(btn)  # 直接添加到水平布局

        # 添加伸缩空间
        main_layout.addStretch(1)

        # ==== 新增倒计时区域 ====
        self.timer_layout = QHBoxLayout()
        main_layout.addLayout(self.timer_layout)
        self.timer_layout.setAlignment(Qt.AlignCenter)

        # ===== 底部按钮 =====
        bottom_layout = QHBoxLayout()
        main_layout.addLayout(bottom_layout)

        # 在 timer_label 前面添加弹性空间
        self.timer_layout.addStretch(1)  # 添加左侧弹性空间

        # 倒计时标签
        self.timer_label = QLabel("剩餘時間:")
        self.timer_label.setFont(QFont("康熙字典體", 18))
        self.timer_label.setStyleSheet("color: #5D4037;")
        self.timer_layout.addWidget(self.timer_label)

        # 倒计时显示
        self.timer_display = QLabel("10秒")
        self.timer_display.setFont(QFont("康熙字典體", 18, QFont.Bold))
        self.timer_display.setStyleSheet("color: #D32F2F;")
        self.timer_layout.addWidget(self.timer_display)

        # 倒计时进度条
        self.timer_progress = QProgressBar()
        self.timer_progress.setFixedHeight(20)
        self.timer_progress.setRange(0, 100)
        self.timer_progress.setValue(100)
        self.timer_progress.setTextVisible(False)

        # 修改为：宽度为窗口宽度的60%
        self.timer_progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.timer_progress.setMinimumWidth(200)  # 最小宽度
        self.timer_progress.setMaximumWidth(400)  # 最大宽度

        self.timer_progress.setStyleSheet("""
            QProgressBar {
            border: 2px solid #8D6E63;
            border-radius: 5px;
            background: #f7eee6;
            width: 200px;
            }
            QProgressBar::chunk {
            background-color: #4CAF50; /* 默认绿色 */
            border-radius: 3px;
            }
        """)
        self.timer_layout.addWidget(self.timer_progress)

        # 在 timer_progress 后面添加弹性空间
        self.timer_layout.addStretch(1)  # 添加右侧弹性空间

        # 初始隐藏倒计时区域
        self.timer_layout.setEnabled(False)
        for i in range(self.timer_layout.count()):
            widget = self.timer_layout.itemAt(i).widget()
            if widget:
                widget.hide()

        # 添加左侧伸缩空间
        bottom_layout.addStretch(1)

        # 下一题按钮
        self.next_btn = QPushButton("下一題☞")
        self.next_btn.setFont(QFont("康熙字典體", 20))
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setFixedHeight(80)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.next_btn.clicked.connect(self.new_question)
        self.next_btn.setEnabled(False)
        bottom_layout.addWidget(self.next_btn)

        # 添加右侧伸缩空间
        bottom_layout.addStretch(1)

        # 在 initUI 后调用 update_difficulty 来生成第一题
        QTimer.singleShot(100, self.update_difficulty)

    def set_bot_icon(self, filename):
        """设置机器人图标（使用资源路径）"""
        icon_path = self.resource_path(filename)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            print(f"无法加载图片: {icon_path}")
        else:
            pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.bot_icon.setPixmap(pixmap)

    def update_hint_text(self):
        """更新提示气泡文本"""
        if self.current_mode == "zhonggusheng":
            hint = "選擇該字對應的中古聲母"
        elif self.current_mode == "zhongguyun":
            hint = "選擇該字對應的中古韻部"
        else:  # shangguyun
            hint = "選擇該字對應的上古韻部"  # 新增提示文本
        if len(self.correct_values) > 1:
            hint += "\n注意：該字有多個讀音"
        self.hint_bubble.setText(hint)

    # 添加难度更新方法
    def update_difficulty(self):
        """更新难度设置"""
        # 停止任何正在运行的计时器
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        if hasattr(self, 'progress_timer') and self.progress_timer and self.progress_timer.isActive():
            self.progress_timer.stop()
        if self.difficulty_normal.isChecked():
            self.current_difficulty = "normal"
            # 隐藏倒计时区域
            self.timer_layout.setEnabled(False)
            for i in range(self.timer_layout.count()):
                widget = self.timer_layout.itemAt(i).widget()
                if widget:
                    widget.hide()
        elif self.difficulty_hard.isChecked():
            self.current_difficulty = "hard"
            self.timer_seconds = 10  # 困难模式10秒
            # 显示倒计时区域
            self.timer_layout.setEnabled(True)
            for i in range(self.timer_layout.count()):
                widget = self.timer_layout.itemAt(i).widget()
                if widget:
                    widget.show()
        elif self.difficulty_hell.isChecked():
            self.current_difficulty = "hell"
            self.timer_seconds = 5  # 地狱模式5秒
            # 显示倒计时区域
            self.timer_layout.setEnabled(True)
            for i in range(self.timer_layout.count()):
                widget = self.timer_layout.itemAt(i).widget()
                if widget:
                    widget.show()

        # 更新倒计时显示
        self.update_timer_display()

        # 生成新题目
        self.new_question()

    # 添加倒计时更新显示方法
    def update_timer_display(self):
        """更新倒计时显示"""
        if self.current_difficulty == "hard":
            self.timer_display.setText(f"{self.timer_seconds}秒")
            progress_value = int((self.timer_seconds / 10) * 100)
            self.timer_progress.setValue(progress_value)

            # 根据剩余时间比例设置颜色
            if progress_value > 50:
                color = "#4CAF50"  # 绿色
            else:
                color = "#F44336"  # 红色

            self.timer_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid #8D6E63;
                    border-radius: 5px;
                    background: #f7eee6;
                    width: 200px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)

        elif self.current_difficulty == "hell":
            self.timer_display.setText(f"{self.timer_seconds}秒")
            progress_value = int((self.timer_seconds / 5) * 100)
            self.timer_progress.setValue(progress_value)

            # 根据剩余时间比例设置颜色
            if progress_value > 50:
                color = "#4CAF50"  # 绿色
            else:
                color = "#F44336"  # 红色

            self.timer_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid #8D6E63;
                    border-radius: 5px;
                    background: #f7eee6;
                    width: 200px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)

    def mode_changed(self, index):
        """处理模式切换事件"""
        # 停止任何正在运行的计时器
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        # 重置难度为普通
        self.difficulty_normal.setChecked(True)
        self.current_difficulty = "normal"

        # 更新模式
        if index == 0:
            self.current_mode = "zhonggusheng"
        elif index == 1:
            self.current_mode = "zhongguyun"
        else:  # index == 2
            self.current_mode = "shangguyun"  # 新增模式

        # 更新UI显示
        self.timer_layout.setEnabled(False)
        for i in range(self.timer_layout.count()):
            widget = self.timer_layout.itemAt(i).widget()
            if widget:
                widget.hide()

        self.new_question()

    def get_random_character(self):
        """从数据库中按优先级随机获取一个字符"""
        # 优先级1: 基本汉字区 [\u4E00-\u9FFF]
        self.cursor.execute("""
            SELECT 字頭 
            FROM ancienttable1 
            WHERE unicode(字頭) BETWEEN 19968 AND 40879  -- \u4E00-\u9FFF
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        result = self.cursor.fetchone()

        if result:
            return result[0]

        # 优先级2: 扩展A区 [\u3400-\u4DBF]
        self.cursor.execute("""
            SELECT 字頭 
            FROM ancienttable1 
            WHERE unicode(字頭) BETWEEN 13312 AND 19903  -- \u3400-\u4DBF
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        result = self.cursor.fetchone()

        if result:
            return result[0]

        # 优先级3: 其他字符
        self.cursor.execute("""
            SELECT 字頭 
            FROM ancienttable1 
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        result = self.cursor.fetchone()

        return result[0] if result else "字"

    def get_character_values(self, character):
        """获取字符对应的所有声母或韵部值"""
        if self.current_mode == "zhonggusheng":
            column = "中古聲"
        elif self.current_mode == "zhongguyun":
            column = "中古韻"
        else:  # shangguyun
            column = "上古韻"  # 新增列名

        self.cursor.execute(f"SELECT {column} FROM ancienttable1 WHERE 字頭 = ?", (character,))
        results = self.cursor.fetchall()
        return list(set([r[0] for r in results]))  # 去重

    def get_random_values(self, exclude_list, count=3):
        """从数据库中随机获取指定数量的值（排除正确值）"""
        if self.current_mode == "zhonggusheng":
            column = "中古聲"
        elif self.current_mode == "zhongguyun":
            column = "中古韻"
        else:  # shangguyun
            column = "上古韻"  # 新增列名

        placeholders = ','.join(['?'] * len(exclude_list))
        query = f"""
            SELECT DISTINCT {column} 
            FROM ancienttable1 
            WHERE {column} NOT IN ({placeholders})
            ORDER BY RANDOM() 
            LIMIT ?
        """
        self.cursor.execute(query, (*exclude_list, count))
        results = self.cursor.fetchall()
        return [r[0] for r in results]

    def new_question(self):
        """生成新题目"""
        # 停止可能正在运行的计时器
        if hasattr(self, 'timer') and self.timer and self.timer.isActive():
            self.timer.stop()
        if hasattr(self, 'progress_timer') and self.progress_timer and self.progress_timer.isActive():
            self.progress_timer.stop()
        # 重置按钮状态
        self.next_btn.setEnabled(False)
        # 重置Bot图标和提示
        self.set_bot_icon('bot.png')
        for btn in self.option_buttons:
            btn.setEnabled(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ebd4bf;
                    color: #5D4037;
                    border: 3px solid #8D6E63;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #D7C29D;
                    border: 4px solid #6D4C41;
                }
            """)
        # 根据难度设置倒计时
        if self.current_difficulty == "hard":
            self.timer_seconds = 10
            self.start_time = time.time()
            self.update_timer_display()

            # 启动主计时器（1秒刷新字符）
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_timer)
            self.timer.start(1000)

            # 进度条计时器（0.1秒刷新实现平滑动画）
            self.progress_timer = QTimer(self)
            self.progress_timer.timeout.connect(self.update_progress_bar)
            self.progress_timer.start(100)  # 改为100毫秒

        elif self.current_difficulty == "hell":
            self.timer_seconds = 5
            self.start_time = time.time()
            self.update_timer_display()

            # 启动主计时器（1秒刷新字符）
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_timer)
            self.timer.start(1000)

            # 进度条计时器（0.1秒刷新实现平滑动画）
            self.progress_timer = QTimer(self)
            self.progress_timer.timeout.connect(self.update_progress_bar)
            self.progress_timer.start(100)  # 改为100毫秒
        else:  # 普通模式
            # 确保普通模式下没有计时器运行
            if hasattr(self, 'timer') and self.timer and self.timer.isActive():
                self.timer.stop()
            if hasattr(self, 'progress_timer') and self.progress_timer and self.progress_timer.isActive():
                self.progress_timer.stop()
        # 获取随机字符
        self.current_character = self.get_random_character()
        # 获取字符对应的所有值
        self.correct_values = self.get_character_values(self.current_character)
        # 设置字符显示（如果是多音字则添加星号）
        if len(self.correct_values) > 1:
            self.char_label.setText(f"{self.current_character}*")
        else:
            self.char_label.setText(self.current_character)
        # 更新提示文本
        self.update_hint_text()
        # 准备选项
        correct_value = random.choice(self.correct_values)  # 随机选择一个正确值
        other_values = self.get_random_values(self.correct_values, 3)  # 获取三个干扰项
        self.options = other_values + [correct_value]
        random.shuffle(self.options)  # 随机打乱选项顺序
        # 记录正确答案的索引
        self.correct_option_index = self.options.index(correct_value)
        # 更新按钮文本
        for i, btn in enumerate(self.option_buttons):
            btn.setText(self.options[i])

    # 新增方法：专门更新进度条
    def update_progress_bar(self):
        """每0.1秒更新一次进度条，实现平滑动画"""
        if self.current_difficulty == "hard":
            total_time = 10.0
        elif self.current_difficulty == "hell":
            total_time = 5.0
        else:
            return

        # 计算已用时间和剩余时间比例
        elapsed = time.time() - self.start_time
        remaining = max(0, total_time - elapsed)
        remaining_ratio = remaining / total_time

        # 使用线性插值计算进度值（更平滑）
        progress_value = int(remaining_ratio * 100)

        # 平滑的颜色过渡（从绿到黄再到红）
        if remaining_ratio > 0.5:
            # 绿色到黄色的过渡（50%-100%）
            green = 180
            red = min(255, int(510 * (1 - remaining_ratio)))
            blue = 0
        else:
            # 黄色到红色的过渡（0%-50%）
            red = 255
            green = min(180, int(360 * remaining_ratio))
            blue = 0

        color = f"#{red:02X}{green:02X}{blue:02X}"

        # 添加平滑结束效果（最后0.5秒闪烁）
        if remaining < 0.5:
            # 使用正弦函数创建闪烁效果
            blink = int(127 + 128 * math.sin(time.time() * 10))
            color = f"#{blink:02X}00{blink:02X}"

        # 更新进度条
        self.timer_progress.setValue(progress_value)

        # 优化样式表 - 只更新颜色部分
        self.timer_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #8D6E63;
                border-radius: 5px;
                background: #f7eee6;
                width: 200px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

        # 时间耗尽时停止计时器
        if remaining <= 0:
            self.progress_timer.stop()

    # 修改原方法：只更新字符显示
    def update_timer(self):
        """更新倒计时（每秒更新字符）"""
        # 计算剩余时间
        if self.current_difficulty == "hard":
            total_time = 10.0
        elif self.current_difficulty == "hell":
            total_time = 5.0
        else:
            return

        elapsed = time.time() - self.start_time
        remaining = max(0, total_time - elapsed)

        # 更新显示 - 使用整数秒数
        seconds_left = int(remaining) + 1 if remaining % 1 > 0.5 else int(remaining)
        self.timer_display.setText(f"{seconds_left}秒")
        self.timer_seconds = seconds_left  # 更新状态变量

        # 时间耗尽
        if remaining <= 0:
            self.timer.stop()
            if hasattr(self, 'progress_timer') and self.progress_timer and self.progress_timer.isActive():
                self.progress_timer.stop()
            # 模拟错误选择
            self.check_answer(-1)  # 使用-1表示超时

    def check_answer(self, selected_index):
        """检查用户选择的答案"""
        # 停止所有可能正在运行的计时器
        if hasattr(self, 'timer') and self.timer and self.timer.isActive():
            self.timer.stop()
        if hasattr(self, 'progress_timer') and self.progress_timer and self.progress_timer.isActive():
            self.progress_timer.stop()

        # 禁用所有按钮
        for btn in self.option_buttons:
            btn.setEnabled(False)

        # 获取用户选择的答案
        if selected_index >= 0:  # 正常选择
            selected_value = self.options[selected_index]
        else:  # 超时
            selected_value = None

        # 检查答案是否正确
        if selected_index >= 0 and selected_value in self.correct_values:
            # 正确答案样式
            self.option_buttons[selected_index].setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 3px solid #388E3C;
                    border-radius: 15px;
                }
            """)
            result = "✓正確！"
            result_color = "#4CAF50"
            # 更新Bot图标
            self.set_bot_icon('botcorrect.png')
        else:
            # 错误答案或超时
            if selected_index >= 0:
                # 用户选择了错误答案
                self.option_buttons[selected_index].setStyleSheet("""
                    QPushButton {
                        background-color: #F44336;
                        color: white;
                        border: 3px solid #D32F2F;
                        border-radius: 15px;
                    }
                """)
                result = "×錯誤！"
                self.set_bot_icon('boterror.png')  # 使用超时图标
            else:
                # 超时情况
                result = "×超時！"
                self.set_bot_icon('boterror.png')  # 使用超时图标

            result_color = "#F44336"

            # 同时显示正确答案
            self.option_buttons[self.correct_option_index].setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 3px solid #388E3C;
                    border-radius: 15px;
                }
            """)

        # 更新提示文本 - 使用HTML格式实现不同颜色
        if self.current_mode == "zhonggusheng":
            info = f"""
                <html>
                <span style="color:{result_color}; font-weight:bold; font-size:16pt;">{result}</span>
                <span style="color:black;">{self.current_character}的聲母：{'、'.join(self.correct_values)}</span>
                </html>
            """
        elif self.current_mode == "zhongguyun":
            info = f"""
                <html>
                <span style="color:{result_color}; font-weight:bold; font-size:16pt;">{result}</span>
                <span style="color:black;">{self.current_character}的韻部：{'、'.join(self.correct_values)}</span>
                </html>
            """
        else:  # shangguyun
            info = f"""
                <html>
                <span style="color:{result_color}; font-weight:bold; font-size:16pt;">{result}</span>
                <span style="color:black;">{self.current_character}的上古韻部：{'、'.join(self.correct_values)}</span>
                </html>
            """
        self.hint_bubble.setText(info)

        # 更新答题统计
        self.total_questions += 1
        if selected_index >= 0 and selected_value in self.correct_values:
            self.correct_answers += 1
        # 计算正确率（避免除以0）
        accuracy = 0
        if self.total_questions > 0:
            accuracy = (self.correct_answers / self.total_questions) * 100
        # 更新统计标签
        self.stats_label.setText(
            f"已答{self.total_questions}題，做對{self.correct_answers}題 | "
            f"正確率: {accuracy:.1f}%"
        )

        # 启用下一题按钮
        self.next_btn.setEnabled(True)

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.conn.close()
        event.accept()

# 聲符-中古聲窗口——————————————————————————————————————————————————————————————————————————————
from PyQt5.QtCore import pyqtSignal, QObject

# 与聲符-中古聲class搭配使用的數據庫相關函數
class DatabaseWorker(QObject):
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, selected_zgs, zgs_list):
        super().__init__()
        self.selected_zgs = selected_zgs
        self.zgs_list = zgs_list

    def run(self):
        connection = None
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 第一步：查询选中声母的所有声符并统计频率
            sql_shengfu = """
                SELECT 聲符, COUNT(*) as count
                FROM ancienttable1
                WHERE 中古聲 = ?
                GROUP BY 聲符
                ORDER BY count DESC, 聲符
            """
            cursor.execute(sql_shengfu, (self.selected_zgs,))
            shengfu_results = cursor.fetchall()

            # 提取声符列表（按频率排序）
            shengfu_list = [row[0] for row in shengfu_results]

            # 如果没有数据，发送空结果
            if not shengfu_list:
                self.finished.emit([], [])
                return

            # 第二步：查询所有声符-中古声母组合对应的字头
            # 构建查询参数 - 所有声符和所有中古声母
            params = shengfu_list + self.zgs_list
            placeholders = ",".join(["?"] * len(shengfu_list))
            zgs_placeholders = ",".join(["?"] * len(self.zgs_list))

            sql_zi = f"""
                SELECT 聲符, 中古聲, GROUP_CONCAT(字頭, ' ') as zi_list
                FROM ancienttable1
                WHERE 聲符 IN ({placeholders})
                  AND 中古聲 IN ({zgs_placeholders})
                GROUP BY 聲符, 中古聲
            """
            cursor.execute(sql_zi, params)
            zi_results = cursor.fetchall()

            # 构建字头数据字典 {(声符, 中古声): 字头列表}
            zi_dict = {}
            for row in zi_results:
                key = (row[0], row[1])
                zi_dict[key] = row[2]

            # 第三步：构建表格数据
            table_data = []
            for shengfu in shengfu_list:
                row_data = []
                for zgs in self.zgs_list:
                    key = (shengfu, zgs)
                    row_data.append(zi_dict.get(key, ""))
                table_data.append(row_data)

            # 发送结果信号
            self.finished.emit(shengfu_list, table_data)

        except Exception as e:
            self.error.emit(f"查询数据库时出错: {e}")
        finally:
            if connection:
                connection.close()
class Shengfu_zhonggushengWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 聲符和中古聲母的關係")
        self.setGeometry(0, 0, 1900, 1300)
        self.setMinimumSize(1400, 1100)
        # 初始最大化窗口
        self.setWindowState(Qt.WindowMaximized)
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.zhonggushengchar_selectForSF = ""

        # 固定中古声母列表
        self.zhonggushengcharsForSF = ["幫", "滂", "並", "明", "端", "透", "定", "泥",
                                       "精", "清", "從", "心", "邪", "莊", "初", "崇", "生",
                                       "章", "昌", "船", "書", "禪", "知", "徹", "澄", "娘",
                                       "見", "溪", "群", "疑", "影", "以", "曉", "匣",
                                       "來", "日", "雲"]
        # 创建主布局
        layout = QVBoxLayout()

        # 創建顯示中古聲母的標籤和下拉框布局
        zgsSelect_layout = QHBoxLayout()
        layout.addLayout(zgsSelect_layout)

        # 创建垂直布局用于提示文本和下拉框 combo box
        label_combo_layout2 = QVBoxLayout()
        label_combo_layout2.setSpacing(5)  # 设置间距

        # 标签
        labelSelect = QLabel("選擇中古聲母:")
        labelSelect.setFont(QFont("康熙字典體", 18))
        labelSelect.setStyleSheet("color: #6E2C00; margin-right: 10px;")  # 添加右边距

        # 创建下拉选择框
        self.combo_box_zgs = QComboBox()
        self.combo_box_zgs.setFont(QFont("康熙字典體", 18))
        self.combo_box_zgs.setStyleSheet("""
                            QComboBox {
                                color: black;
                                padding: 5px;
                                min-width: 200px;  
                            }
                        """)
        self.combo_box_zgs.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 添加尺寸策略
        self.combo_box_zgs.setCursor(Qt.PointingHandCursor)
        # 添加默认提示项
        self.combo_box_zgs.addItem("請選擇")
        self.combo_box_zgs.setCurrentIndex(0)  # 默认选中提示项
        self.combo_box_zgs.model().item(0).setEnabled(False)  # 禁用提示项

        self.combo_box_zgs.addItems(self.zhonggushengcharsForSF)

        # 连接下拉框的选择变更信号
        self.combo_box_zgs.currentTextChanged.connect(self.on_combobox_changedZgs)

        # 将 labelSelect 和 combo box zgs 添加到垂直布局
        label_combo_layout2.addWidget(labelSelect)
        label_combo_layout2.addWidget(self.combo_box_zgs)

        # 将垂直布局添加到水平布局
        zgsSelect_layout.addLayout(label_combo_layout2)

        self.label4 = QLabel("功能說明：選擇中古聲母，查看該聲母對應的聲符分佈詳情")
        self.label4.setFont(QFont("康熙字典體", 17))
        self.label4.setAlignment(Qt.AlignCenter)
        self.label4.setStyleSheet("border: 1px solid brown; padding: 10px; color:#DC6500")

        zgsSelect_layout.addWidget(self.label4)

        # 创建表格控件 - 使用QTableWidget
        self.table_widget = QTableWidget()
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #E6B0AA;
                background-color: #F3F3F3;
                alternate-background-color: #F9F9F9;
            }
            QHeaderView::section {
                background-color: #FEF9F6;
                border: 2px solid #E6B0AA;
                font-weight: bold;
                font-family: "IpaP";
                font-size: 16pt;
                padding: 2px;
            }
            QTableWidget::item {
                border: 1px solid #E6B0AA;
                padding: 2px;
                font-family: "IpaP";
                font-size: 16pt;
            }

        """)

        # 设置表格属性
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setWordWrap(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)

        # 添加表格到主布局
        layout.addWidget(self.table_widget)

        # 设置主窗口布局
        self.setLayout(layout)

        # 初始化表格状态
        self.clear_table()

        # 用于线程管理的成员变量
        self.worker_thread = None
        self.worker = None

    def clear_table(self):
        """清空表格内容"""

        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.table_widget.clear()

        # 显示占位符文本
        self.table_widget.setRowCount(1)
        self.table_widget.setColumnCount(1)

        placeholder = QLabel("請選擇中古聲母以顯示數據")
        placeholder.setFont(QFont("康熙字典體", 20))
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray;")
        self.table_widget.setCellWidget(0, 0, placeholder)

        # 确保表头被清除
        self.table_widget.setHorizontalHeaderLabels([""])
        self.table_widget.setVerticalHeaderLabels([""])

    def on_combobox_changedZgs(self, text):
        """处理下拉框选择变更"""
        if text == "請選擇":
            self.clear_table()
            return

        self.zhonggushengchar_selectForSF = text
        self.label4.setText(f"正加載: 【中古{text}母】的聲符分佈…… 數據量大，可能卡頓，請勿重複點按！")
        self.label4.setStyleSheet(
            "border: 1px solid brown; padding: 10px; color: red;"
        )
        self.load_table_dataForSF()

    def load_table_dataForSF(self):
        """创建一个新线程去查询数据库"""
        print("Loading table data...")

        # 清理之前的线程
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

        # 创建新线程和工作对象
        self.worker_thread = QThread()
        self.worker = DatabaseWorker(
            self.zhonggushengchar_selectForSF,
            self.zhonggushengcharsForSF
        )
        self.worker.moveToThread(self.worker_thread)

        # 连接信号
        self.worker.finished.connect(self.update_table)
        self.worker.error.connect(self.handle_error)

        # 启动线程
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def handle_error(self, error_msg):
        """处理错误信号"""
        print(error_msg)
        self.label4.setText(f"數據加載失敗: {error_msg.split(':')[-1].strip()}")

        # 清理线程
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def update_table(self, shengfu_list, table_data):
        """更新表格UI"""
        # 清理线程
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

        # 清空表格
        self.table_widget.clear()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)

        # 清空表头标签
        self.table_widget.setHorizontalHeaderLabels([])
        self.table_widget.setVerticalHeaderLabels([])

        # 如果没有数据，显示提示
        if not shengfu_list:
            self.table_widget.setRowCount(1)
            self.table_widget.setColumnCount(1)

            placeholder = QLabel("沒有找到匹配的數據")
            placeholder.setFont(QFont("IpaP", 20))
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: gray;")
            self.table_widget.setCellWidget(0, 0, placeholder)
            self.label4.setText(f"{self.zhonggushengchar_selectForSF} 聲母沒有對應的聲符數據")
            return

        # 设置表格行列数
        row_count = len(shengfu_list)
        col_count = len(self.zhonggushengcharsForSF)
        self.table_widget.setRowCount(row_count)
        self.table_widget.setColumnCount(col_count)

        # 设置表头
        self.table_widget.setHorizontalHeaderLabels(self.zhonggushengcharsForSF)
        self.table_widget.setVerticalHeaderLabels(shengfu_list)

        # 填充表格内容
        for row in range(row_count):
            for col in range(col_count):
                cell_data = table_data[row][col]
                item = QTableWidgetItem(cell_data)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont("IpaP", 14))
                item.setFlags(Qt.ItemIsEnabled)  # 只读

                # 高亮显示选中的声母列
                if self.zhonggushengcharsForSF[col] == self.zhonggushengchar_selectForSF:
                    item.setBackground(QColor("#F9E79F"))

                self.table_widget.setItem(row, col, item)

        # 设置列宽
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 更新状态标签
        self.label4.setText(
            f"已顯示: 【中古{self.zhonggushengchar_selectForSF}母】的聲符分佈 | 共 {len(shengfu_list)} 個聲符")
        self.label4.setStyleSheet("border: 1px solid brown; padding: 10px; color: #004AA2")


# 聲符散佈数据窗口———————————————————————————————————————————————————————
class ShengfuSanbuWindow(QWidget):
    # 添加数据加载完成信号
    data_loaded = pyqtSignal(object)
    def __init__(self, cache_data=None):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 《廣韻》聲符散佈表")
        self.setMinimumSize(1400, 1100)
        # 初始最大化窗口
        self.setWindowState(Qt.WindowMaximized)
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 创建主布局
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 创建状态标签
        self.status_label = QLabel("正加載: 《廣韻》聲符的散佈…… 數據量大，可能卡頓，請勿重複點按！")
        self.status_label.setFont(QFont("康熙字典體", 16))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red; padding: 10px;")
        layout.addWidget(self.status_label)

        # 添加提示標籤
        sanbu_tip_label = QLabel("————數據源：Poem《廣韻字表》————")
        sanbu_tip_label.setFont(QFont("Ipap", 13))
        sanbu_tip_label.setStyleSheet("color: gray;")
        sanbu_tip_label.setAlignment(Qt.AlignCenter)  # 水平居中
        layout.addWidget(sanbu_tip_label)

        # 创建表格控件
        self.table_widget = QTableWidget()
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #E6B0AA;
                background-color: #F3F3F3;
                alternate-background-color: #F9F9F9;
            }
            QHeaderView::section {
                background-color: #FEF9F6;
                border: 2px solid #E6B0AA;
                font-weight: bold;
                font-family: "IpaP";
                font-size: 16pt;
                padding: 2px;
            }
            QTableWidget::item {
                border: 1px solid #E6B0AA;
                padding: 2px;
                font-family: "IpaP";
                font-size: 16pt;
            }
        """)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setWordWrap(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)

        # 添加表格到布局
        layout.addWidget(self.table_widget)

        #双击单元格的事件
        self.table_widget.cellDoubleClicked.connect(self.handle_cell_click)

        # 保存缓存数据引用
        self.cache_data = cache_data

        # 如果已有缓存数据，立即加载
        if cache_data:
            QTimer.singleShot(50, self.load_from_cache)
        else:
            # 否则从数据库加载
            QTimer.singleShot(50, self.load_table_data)

    def load_from_cache(self):
        """从缓存加载数据"""
        if not self.cache_data:
            return

        try:
            shengmu_list = self.cache_data['shengmu_list']
            shengfu_list = self.cache_data['shengfu_list']
            total_counts = self.cache_data['total_counts']
            all_count_dicts = self.cache_data['all_count_dicts']

            # 设置表格
            self.setup_table(shengmu_list, shengfu_list, total_counts, all_count_dicts)

            # 更新状态
            self.status_label.setText(f"已顯示 {len(shengfu_list)} 個聲符的分佈數據 (從緩存)，雙擊單元格可查看轄字詳情")
            self.status_label.setStyleSheet("color: #004AA2; padding: 10px;")

        except Exception as e:
            self.status_label.setText(f"緩存加載出錯: {str(e)}")
            # 回退到数据库加载
            QTimer.singleShot(0, self.load_table_data)

    def load_table_data(self):
        """加载表格数据"""
        try:
            # 连接数据库
            connection = create_db_connection()
            cursor = connection.cursor()

            # 使用固定的广韵声母列表（按照您提供的顺序）
            shengmu_list = ["幫", "滂", "並", "明", "端", "透", "定", "知", "徹", "澄",
                            "精", "清", "從", "心", "邪", "莊", "初", "崇", "生", "俟",
                            "章", "昌", "常", "書", "船", "見", "溪", "羣", "疑", "匣",
                            "曉", "影", "云", "日", "泥", "娘", "來", "以"]

            # 查询所有广韵声符及其出现频次
            cursor.execute("SELECT 廣韻聲符, COUNT(*) as cnt FROM guangyun GROUP BY 廣韻聲符 ORDER BY cnt DESC")
            shengfu_results = cursor.fetchall()

            # 创建声符列表和总次数字典
            shengfu_list = []
            total_counts = {}  # 存储每个声符的总次数
            for row in shengfu_results:
                shengfu_list.append(row[0])
                total_counts[row[0]] = row[1]  # 保存总次数

            # 如果没有数据，显示提示
            if not shengmu_list or not shengfu_list:
                self.status_label.setText("未找到《廣韻》聲符數據")
                return

            # 设置表格行列数
            self.table_widget.setRowCount(len(shengfu_list))
            self.table_widget.setColumnCount(len(shengmu_list) + 2)  # +1 为声符列

            #设置表头
            headers = ["聲符", "頻次"] + shengmu_list
            self.table_widget.setHorizontalHeaderLabels(headers)

            # 固定前两列的宽度
            header = self.table_widget.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)  # 固定声符列宽度
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # 固定频次列宽度
            self.table_widget.setColumnWidth(0, 80)  # 声符列宽度
            self.table_widget.setColumnWidth(1, 80)  # 频次列宽度
            # 其余列保持自适应
            for col in range(2, self.table_widget.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Stretch)

            # 填充表格数据
            for row_idx, shengfu in enumerate(shengfu_list):
                # 第一列：声符
                item_shengfu = QTableWidgetItem(shengfu)
                item_shengfu.setTextAlignment(Qt.AlignCenter)
                self.table_widget.setItem(row_idx, 0, item_shengfu)

                # 设置字体：宋体、粗体、18pt
                font = QFont("宋体")
                font.setBold(True)
                font.setPointSize(16)
                item_shengfu.setFont(font)
                self.table_widget.setItem(row_idx, 0, item_shengfu)

                # 第二列：声符总频次
                total_count = total_counts.get(shengfu, 0)
                item_count = QTableWidgetItem(str(total_count))
                item_count.setTextAlignment(Qt.AlignCenter)
                self.table_widget.setItem(row_idx, 1, item_count)

                # 查询该声符在不同声母下的字头数量
                cursor.execute("""
                    SELECT 廣韻聲母, COUNT(*) as cnt 
                    FROM guangyun 
                    WHERE 廣韻聲符 = ? 
                    GROUP BY 廣韻聲母
                """, (shengfu,))
                counts = cursor.fetchall()
                count_dict = {row[0]: row[1] for row in counts}

                # 填充各列数据
                for col_idx, shengmu in enumerate(shengmu_list, start=2):
                    cnt = count_dict.get(shengmu, 0)
                    if cnt > 0:
                        item = QTableWidgetItem(str(cnt))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.table_widget.setItem(row_idx, col_idx, item)

            # 保存完整数据用于缓存
            all_count_dicts = {}
            for shengfu in shengfu_list:
                cursor.execute("""
                    SELECT 廣韻聲母, COUNT(*) as cnt 
                    FROM guangyun 
                    WHERE 廣韻聲符 = ? 
                    GROUP BY 廣韻聲母
                """, (shengfu,))
                counts = cursor.fetchall()
                all_count_dicts[shengfu] = {row[0]: row[1] for row in counts}
            # 设置表格
            self.setup_table(shengmu_list, shengfu_list, total_counts, all_count_dicts)

            # 更新状态
            self.status_label.setText(f"已顯示 {len(shengfu_list)} 個聲符的分佈數據，雙擊單元格可查看轄字詳情")
            self.status_label.setStyleSheet("color: #004AA2; padding: 10px;")

            # 发送缓存数据
            cache_data = {
                'shengmu_list': shengmu_list,
                'shengfu_list': shengfu_list,
                'total_counts': total_counts,
                'all_count_dicts': all_count_dicts
            }
            self.data_loaded.emit(cache_data)

        except Exception as e:
            self.status_label.setText(f"加載數據出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"數據庫查詢出錯: {str(e)}")
        finally:
            if connection:
                connection.close()

    def setup_table(self, shengmu_list, shengfu_list, total_counts, all_count_dicts):
        """通用表格设置方法"""
        # 设置表格行列数
        self.table_widget.setRowCount(len(shengfu_list))
        self.table_widget.setColumnCount(len(shengmu_list) + 2)

        # 设置表头
        headers = ["聲符", "頻次"] + shengmu_list
        self.table_widget.setHorizontalHeaderLabels(headers)

        # 设置列宽
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table_widget.setColumnWidth(0, 80)
        self.table_widget.setColumnWidth(1, 80)
        for col in range(2, self.table_widget.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)

        # 填充数据
        for row_idx, shengfu in enumerate(shengfu_list):
            # 声符列
            item_shengfu = QTableWidgetItem(shengfu)
            item_shengfu.setTextAlignment(Qt.AlignCenter)
            font = QFont("宋体")
            font.setBold(True)
            font.setPointSize(16)
            item_shengfu.setFont(font)
            self.table_widget.setItem(row_idx, 0, item_shengfu)

            # 频次列
            total_count = total_counts.get(shengfu, 0)
            item_count = QTableWidgetItem(str(total_count))
            item_count.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_idx, 1, item_count)

            # 各声母数量
            count_dict = all_count_dicts.get(shengfu, {})
            for col_idx, shengmu in enumerate(shengmu_list, start=2):
                cnt = count_dict.get(shengmu, 0)
                if cnt > 0:
                    item = QTableWidgetItem(str(cnt))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table_widget.setItem(row_idx, col_idx, item)

    def handle_cell_click(self, row, col):
        """处理单元格点击事件"""
        # 忽略表头行和声符列（第一列）
        if col == 0 or col == 1 or not self.table_widget.item(row, col):
            return

        # 获取声符和声母
        shengfu = self.table_widget.item(row, 0).text()
        shengmu = self.table_widget.horizontalHeaderItem(col).text()

        # 获取当前单元格值（字头数量）
        cell_value = int(self.table_widget.item(row, col).text())

        # 查询数据库获取字头详情
        try:
            connection = create_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                SELECT 廣韻字頭 
                FROM guangyun 
                WHERE 廣韻聲符 = ? AND 廣韻聲母 = ?
            """, (shengfu, shengmu))
            results = cursor.fetchall()
            zitou_list = [row[0] for row in results]

            # 验证数量是否匹配
            if len(zitou_list) != cell_value:
                QMessageBox.warning(self, "數據不一致",
                                    f"數據庫查詢到{len(zitou_list)}個字頭，但表格顯示{cell_value}個，程序可能出錯，請聯繫開發者。")

            # 显示详情对话框
            self.show_zitou_detail(shengfu, shengmu, cell_value, zitou_list)

        except Exception as e:
            QMessageBox.critical(self, "查詢錯誤", f"數據庫查詢失敗: {str(e)}")
        finally:
            if connection:
                connection.close()

    def show_zitou_detail(self, shengfu, shengmu, count, zitou_list):
        """显示字头详情对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"聲符「{shengfu}」- 聲母「{shengmu}」")
        dialog.setMinimumSize(600, 400)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout()

        # 标题标签
        title_label = QLabel(f"聲符為「{shengfu}」的「{shengmu}」母字共 {count} 個:")
        title_label.setFont(QFont("宋体", 16))
        title_label.setStyleSheet("color: #8B0000; padding: 10px;")
        layout.addWidget(title_label)

        # 文本显示区域
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("宋体", 16))
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FEF9F6;
                border: 2px solid #E6B0AA;
                padding: 10px;
            }
        """)

        # 按每行10个字格式化显示
        formatted_text = ""
        for i, zitou in enumerate(zitou_list):
            formatted_text += zitou + " "
            if (i + 1) % 10 == 0:
                formatted_text += "\n"

        text_edit.setText(formatted_text.strip())
        layout.addWidget(text_edit)


        dialog.setLayout(layout)
        dialog.exec_()


# 查中古韻母窗口——————————————————————————————————————————————————————————————————————————————
class ZhongguyunWindow(QWidget):
    update_table_signal = pyqtSignal(list)  # 定义查询信号
    update_label_signal = pyqtSignal(str)  # 定义更新 label3图例 的信号
    update_radioboxes_signal = pyqtSignal(list, dict, dict, int)  # 修改信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 查中古音·韻部")
        self.setGeometry(0, 0, 1900, 1300)
        self.setMinimumSize(1400, 1100)

        # 初始最大化窗口
        self.setWindowState(Qt.WindowMaximized)

        # 添加类属性
        self.zhongguyunchar_select = ""
        self.color_mapping = {}  # 确保在__init__中初始化

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 创建主布局
        layout = QVBoxLayout()

        # 創建顯示韻部韻母的標籤和下拉框布局
        zgySelect_layout = QHBoxLayout()
        layout.addLayout(zgySelect_layout)

        # 创建垂直布局用于 label 和 combo box
        label_combo_layout = QVBoxLayout()
        label_combo_layout.setSpacing(5)  # 设置间距

        # 标签
        label = QLabel("選擇中古韻部:")
        label.setFont(QFont("康熙字典體", 18))
        label.setStyleSheet("color: #6E2C00; margin-right: 10px;")  # 添加右边距

        # 创建下拉选择框
        self.combo_box = QComboBox()
        self.combo_box.setFont(QFont("康熙字典體", 18))
        self.combo_box.setStyleSheet("""
                    QComboBox {
                        color: black;
                        padding: 5px;
                        min-width: 200px;  
                    }
                """)
        self.combo_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 添加尺寸策略
        self.combo_box.setCursor(Qt.PointingHandCursor)
        # 添加默认提示项
        self.combo_box.addItem("請選擇")
        self.combo_box.setCurrentIndex(0)  # 默认选中提示项
        self.combo_box.model().item(0).setEnabled(False)  # 禁用提示项

        # 添加选项
        zhongguyunchars = ["東", "屋", "冬", "沃", "鍾", "燭", "江", "覺", "支", "脂",
                           "之", "微", "魚", "虞", "模", "齊", "祭", "泰",
                           "佳", "皆", "夬", "灰", "咍", "廢", "真", "質", "臻", "櫛",
                           "文", "物", "殷", "迄", "元", "月", "魂", "沒", "痕", "寒", "曷", "删", "黠", "山", "鎋",
                           "先", "屑", "仙", "薛", "蕭", "宵", "肴", "豪", "歌", "麻",
                           "陽", "藥", "唐", "鐸", "庚", "陌", "耕", "麥", "清", "昔", "青", "錫", "蒸", "職", "登",
                           "德", "尤", "侯", "幽", "侵", "緝", "覃", "合", "談", "盍", "鹽", "葉", "添", "帖",
                           "咸", "洽", "銜", "狎", "嚴", "業", "凡", "乏"]
        self.combo_box.addItems(zhongguyunchars)

        # 连接下拉框的选择变更信号
        self.combo_box.currentTextChanged.connect(self.on_combobox_changed)

        # 将 label 和 combo box 添加到垂直布局
        label_combo_layout.addWidget(label)
        label_combo_layout.addWidget(self.combo_box)

        # 将垂直布局添加到水平布局
        zgySelect_layout.addLayout(label_combo_layout)

        self.label3 = QLabel("圖例")
        self.label3.setFont(QFont("IpaP", 16))
        self.label3.setStyleSheet("border: 1px solid brown;")

        zgySelect_layout.addWidget(self.label3)

        # 创建表格布局_____________________________
        # 创建表头容器和内容容器
        self.header_widget = QWidget()
        self.header_layout = QGridLayout()
        self.header_layout.setSpacing(0)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_widget.setLayout(self.header_layout)
        self.header_widget.setStyleSheet("""
                            QWidget {
                                background-color: white;
                            }
                            QLabel {
                                border: 2px solid #E6B0AA;
                                background-color: #FEF9F6;
                            }
                        """)

        self.content_widget = QWidget()
        self.content_layout = QGridLayout()
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget.setLayout(self.content_layout)
        # 内容区域基础样式
        self.content_widget.setStyleSheet("""
                                   QWidget {
                                       background-color: #F3F3F3;
                                   }
                                   QLabel[has_content="false"] {  /* 空白单元格 */
                                       background-color: #EEEEEE;
                                       border: 1px solid #E6B0AA;
                                       min-width: 80px;
                                       min-height: 40px;
                                   }
                                   QLabel[has_content="true"] {  /* 有内容的单元格 */
                                       background-color: #F3F3F3;
                                       border: 1px solid #E6B0AA;
                                   }
                               """)

        # 配置滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.content_widget)

        # 将表头和滚动区域添加到主布局
        layout.addWidget(self.header_widget)
        layout.addWidget(scroll_area)  # 只有 zhonggushengchar_select 有值时，才添加 scroll_area

        # 添加"可筛选的上古音韵部："标签和關於按鈕 (水平佈局)
        filter_layout = QHBoxLayout()

        # 標籤
        self.filter_label = QLabel("這些字來自0個上古韻部：")
        self.filter_label.setFont(QFont("康熙字典體", 16))
        self.filter_label.setStyleSheet("color: #6E2C00;")  # 设置标签的字体颜色
        self.filter_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐并垂直居中
        filter_layout.addWidget(self.filter_label)

        # 添加彈性空間，讓按鈕靠右
        filter_layout.addStretch()

        # 在filter_layout中添加打印按钮
        self.print_button = QPushButton("打印此表")
        self.print_button.setFont(QFont("康熙字典體", 14))
        self.print_button.setStyleSheet("""
                        QPushButton {
                            color: #6E2C00;
                            background-color: #FEF9F6;
                            border: 1px solid #E6B0AA;
                            padding: 5px 10px;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #F5EEF8;
                        }
                    """)
        self.print_button.setCursor(Qt.PointingHandCursor)
        self.print_button.clicked.connect(self.save_table_image)

        filter_layout.addWidget(self.print_button)  # 添加到关于按钮之前

        # 將這個水平佈局添加到主佈局
        layout.addLayout(filter_layout)

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
        layout.addWidget(radiobox_container)

        # 设置主窗口布局
        self.setLayout(layout)
        # 连接信号和槽
        self.update_table_signal.connect(self.update_table)
        self.update_label_signal.connect(self.update_label)
        self.update_radioboxes_signal.connect(self.update_radioboxes)

        # 开启线程查询数据库
        self.load_table_data()
        # 新增右键菜单相关属性
        self.selected_text = ""
        self.current_label = None

        self._show_remark_result.connect(self.show_remark_dialog)

    def on_combobox_changed(self, text):
        """处理下拉框选择变更"""
        self.zhongguyunchar_select = text
        self.load_table_data()

    def load_table_data(self):
        """创建一个新线程去查询数据库，以避免阻塞主线程"""
        print("Loading table data...")
        threading.Thread(target=self.query_database).start()

    def apply_filter(self):
        """應用篩選功能"""
        # 獲取選中的單選按鈕
        selected_shangguyun = None
        # 在获取颜色映射前添加保护逻辑
        if not hasattr(self, 'color_mapping') or not self.color_mapping:
            self.color_mapping = {}  # 防止属性不存在
        for radiobox in self.radioboxes:
            # 遍历所有单选按钮，找到被选中的项目
            if radiobox.isChecked():
                raw_text = radiobox.text().split('(')[0].strip()
                selected_shangguyun = raw_text if raw_text != "全部" else "全部"
                break  # 找到之後退出循環
        print(f"選中的上古韻部: {selected_shangguyun}")  # 調試信息，顯示選中的韻部

        # 如果選擇了"全部"，重新加載所有數據
        if selected_shangguyun == "全部":
            self.load_table_data()  # 調用函數加載全部數據
            return  # 結束函數執行

        # 否則，篩選數據
        connection = None  # 初始化數據庫連接變量
        try:
            connection = create_db_connection()  # 創建數據庫連接
            cursor = connection.cursor()  # 創建游標以操作數據庫

            # 查詢符合條件的數據
            sql = """
                        SELECT 字頭, 上古聲, 中古聲, 上古韻, 中古調, 中古等, 開合
                        FROM ancienttable1
                        WHERE 中古韻 = ? AND 上古韻 = ?
                    """
            cursor.execute(sql, (self.zhongguyunchar_select, selected_shangguyun))
            result = cursor.fetchall()

            print(f"查詢結果數量: {len(result)}")  # 調試信息

            if not result:  # 如果沒有查詢結果
                # 發送空列表更新表格
                self.update_table_signal.emit([])
                return

            # 獲取所有不同的上古yun
            unique_shangguyun = set(row['上古韻'] for row in result)

            # 創建顏色映射
            color_palette = ['#7300C2', '#BA21C9', '#00CC76', '#A4AD03',
                             '#AD033A', '#0036BA', '#770028', '#04552C',
                             '#E67F00', '#BD9300', '#00A4E0']
            available_colors = color_palette[:]
            color_mapping = {}

            # 為每個上古韵分配顏色
            for shangguyun in unique_shangguyun:
                if shangguyun not in color_mapping:
                    if available_colors:
                        color = available_colors.pop()
                        color_mapping[shangguyun] = color
                    else:
                        color_mapping[shangguyun] = self.random_color()

            # 更新圖例
            # 获取并处理上古声母数据（去重不排序）
            unique_shanggusheng = list({row['上古聲'] for row in result})
            shangsheng_str = '  '.join([f'[{s}]' for s in unique_shanggusheng]) if unique_shanggusheng else '【未選擇】'
            html_content = f"<b>上古音聲母來源：</b><br>{shangsheng_str}"

            self.update_label_signal.emit(html_content)

            # 將相同的"中古聲"和"中古等"進行分組
            grouped_data = defaultdict(lambda: defaultdict(list))
            for row in result:
                zhonggusheng = row['中古聲']  # 使用"中古聲"作為行
                zhonggudeng = row['中古等']  # 根據"中古等"來分類
                zhonggudiaos = row['中古調']  # 使用"中古調"決定列
                zitou = row['字頭']  # 字頭作為具體填充數據
                shanggusheng = row['上古聲']  # 上古聲
                shangguyun = row['上古韻']
                kaihe = row['開合']

                # 字頭分類邏輯：根據"中古等"和"中古調"填入對應的列
                if zhonggudeng in ["一", "二", "三", "四", "A", "B"]:
                    deng_type = "等" if zhonggudeng in ["一", "二", "三", "四"] else "類"
                    deng_name = f"{zhonggudeng}{deng_type}"

                    if zhonggudiaos in ["平", "上", "去", "入"]:
                        kaihe_text = "開" if kaihe == "開" else "合"
                        # 每个元素单独换行
                        text = f"{deng_name}{zhonggudiaos}·{kaihe_text}"
                        deng = '\n'.join(char for char in text)

                        # ========== 新增颜色判断逻辑 ==========
                        if selected_shangguyun == "全部":
                            # 使用预设颜色
                            color = color_mapping.get(shangguyun, "#000000")
                        else:
                            # 强制使用黑色
                            color = "#000000"
                        # 將數據添加到分組中
                        grouped_data[zhonggusheng][deng].append({
                            "字頭": zitou,
                            "上古聲": shanggusheng,
                            "color": color  # <-- 应用动态颜色
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

            sql = """
                            SELECT 字頭, 上古聲, 中古聲, 上古韻, 中古調, 中古等, 開合
                            FROM ancienttable1
                            WHERE 中古韻 = ?
                        """
            cursor.execute(sql, (self.zhongguyunchar_select,))
            result = cursor.fetchall()

            # 新增：统计每个上古韵部出现次数
            from collections import defaultdict
            shangguyun_counts = defaultdict(int)
            for row in result:
                shangguyun_counts[row['上古韻']] += 1

            # 獲取所有不同的上古韻
            unique_shangguyun = set(row['上古韻'] for row in result)
            unique_shangguyun_count = len(unique_shangguyun)
            print('上古韻有：' + str(unique_shangguyun))

            # 获取所有不同的上古声
            unique_shanggusheng = set(row['上古聲'] for row in result)
            unique_shanggusheng_count = len(unique_shanggusheng)

            # 创建颜色列表，用于随机选择
            color_palette = ['#7300C2', '#BA21C9', '#00CC76', '#A4AD03',
                             '#AD033A', '#0036BA', '#770028', '#04552C',
                             '#E67F00', '#BD9300', '#00A4E0']
            # 可用的颜色列表，每次从这里选择，并确保颜色不重复
            available_colors = color_palette[:]
            color_mapping = {}  # 存储"上古韵"和颜色的对应关系

            # 如果颜色数量不足，随机生成额外的颜色
            if unique_shangguyun_count > len(available_colors):
                extra_colors_needed = unique_shangguyun_count - len(available_colors)
                for _ in range(extra_colors_needed):
                    new_color = self.random_color()  # 随机生成一个颜色
                    available_colors.append(new_color)
                print(
                    f"当前查询的上古韻部種類 ({unique_shangguyun_count})"
                    f" 超过了调色盘中可用颜色的数量 ({len(available_colors)})")

            # 按照"上古韵"分配颜色
            for shangguyun in unique_shangguyun:
                if shangguyun not in color_mapping:
                    if available_colors:  # 如果还有未使用的颜色
                        color = available_colors.pop()  # 从可用颜色列表中获取一个颜色
                        color_mapping[shangguyun] = color
                    else:
                        print(f"警告：颜色不足以为所有上古韻部分配颜色，随机生成中")
            print(color_mapping)

            # 在分配颜色后保存到类属性
            self.color_mapping = color_mapping
            # 获取总字数（所有记录的数量）
            total_count = len(result)
            # 发送信号时传递颜色映射
            self.update_radioboxes_signal.emit(
                list(unique_shangguyun),
                self.color_mapping,
                shangguyun_counts,  # 新增字数统计字典
                total_count  # 新增总字数参数
            )
            # 获取并处理上古声母数据（去重不排序）
            unique_shanggusheng = list({row['上古聲'] for row in result})
            shangsheng_str = '  '.join([f'[{s}]' for s in unique_shanggusheng])
            html_content = f"<b>上古音聲母來源：</b><br>{shangsheng_str}" if unique_shanggusheng else ('【功能說明】：'
                                                                                                      '用韻圖分類顯示中古韻部的轄字。'
                                                                                                      '查詢後可據上古韻部的來源篩選，'
                                                                                                      '轄字後為該字上古聲母，'
                                                                                                      '選定轄字可右鍵複製或查看備註。')
            # html_content = f"<b>上古音聲母來源：</b><br>{shangsheng_str}"

            self.update_label_signal.emit(html_content)  # 使用信号传递数据

            # 将相同的"中古聲"和"中古等"进行分组
            grouped_data = defaultdict(lambda: defaultdict(list))
            for row in result:
                zhonggusheng = row['中古聲']  # 使用"中古聲"作为行
                zhonggudeng = row['中古等']  # 根据"中古等"来分类
                zhonggudiaos = row['中古調']  # 使用"中古調"决定列
                zitou = row['字頭']  # 字头作为具体填充数据
                shanggusheng = row['上古聲']  # 上古声
                shangguyun = row['上古韻']
                kaihe = row['開合']

                # 字頭分類邏輯：根据"中古等"和"中古調"填入对应的列
                if zhonggudeng in ["一", "二", "三", "四", "A", "B"]:
                    deng_type = "等" if zhonggudeng in ["一", "二", "三", "四"] else "類"
                    deng_name = f"{zhonggudeng}{deng_type}"

                    if zhonggudiaos in ["平", "上", "去", "入"]:
                        kaihe_text = "開" if kaihe == "開" else "合"
                        text = f"{deng_name}{zhonggudiaos}·{kaihe_text}"
                        deng = '\n'.join(char for char in text)

                else:
                    continue  # 如果"中古等"值不匹配，跳过该记录

                grouped_data[zhonggusheng][deng].append({
                    "字頭": zitou,
                    "上古聲": shanggusheng,
                    "color": color_mapping[shangguyun]
                })

                # 转换为列表形式，每个元素包含"中古聲"、"中古等"和相应的"字頭"列表
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

    def update_radioboxes(self, unique_shangguyun, color_mapping, shangguyun_counts, total_count):
        """更新单选按钮"""
        # 更新filter_label
        filter_label_context = f"這些字來自{len(unique_shangguyun)}個上古韻部：" if unique_shangguyun else '【篩選器】'
        self.filter_label.setText(filter_label_context)

        # 清空现有的单选按钮
        for i in reversed(range(self.radiobox_layout.count())):
            widget = self.radiobox_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.radioboxes.clear()

        # 添加"全部"选项（黑色）
        all_radiobox = QRadioButton(f"全部({total_count})")
        all_radiobox.setFont(QFont("康熙字典體", 16))  # 添加字体设置
        all_radiobox.setStyleSheet("color: #000000; border: none;")
        all_radiobox.setChecked(True)  # 设置默认选中
        all_radiobox.toggled.connect(self.apply_filter)  # 连接信号
        self.radiobox_layout.addWidget(all_radiobox)  # <-- 关键修复：添加到布局
        self.radioboxes.append(all_radiobox)  # <-- 添加到按钮列表

        # 按字数降序排序（排除"全部"）
        sorted_yun = sorted(
            unique_shangguyun,
            key=lambda x: shangguyun_counts.get(x, 0),
            reverse=True
        )
        # 动态添加带颜色的单选按钮
        for yun in sorted_yun:
            count = shangguyun_counts.get(yun, 0)  # 获取当前韵部字数
            rb = QRadioButton(f"{yun}({count})")
            color = color_mapping.get(yun, "#000000")
            rb.setStyleSheet(f"color: {color}; border: none;")
            rb.setFont(QFont("康熙字典體", 16))
            rb.toggled.connect(self.apply_filter)  # 连接信
            self.radiobox_layout.addWidget(rb)
            self.radioboxes.append(rb)

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
        # 清空两个容器的内容
        for i in reversed(range(self.header_layout.count())):
            self.header_layout.itemAt(i).widget().deleteLater()
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().deleteLater()

        # 动态生成行(中古聲)和列(中古等)的列表
        rows = sorted({entry["中古聲"] for entry in data},
                      key=lambda x: "幫滂並明端透定泥娘來精清從心邪知徹澄莊初崇生章昌船書禪日見溪群疑曉匣影雲以".index(
                          x))

        # 三级排序函数：先按等/类排序，再按声调排序，最后按开合排序
        def sort_key(col_name):
            # 移除换行符以便于处理
            flat_name = col_name.replace('\n', '')

            # 解析列名中的等/类信息
            deng_priority = 7  # 默认优先级最低
            if "一等" in flat_name:
                deng_priority = 1
            elif "二等" in flat_name:
                deng_priority = 2
            elif "三等" in flat_name:
                deng_priority = 3
            elif "四等" in flat_name:
                deng_priority = 4
            elif "A類" in flat_name:
                deng_priority = 5
            elif "B類" in flat_name:
                deng_priority = 6

            # 解析声调信息
            tone_priority = {"平": 1, "上": 2, "去": 3, "入": 4}
            tone_value = 5  # 默认值
            for t in ["平", "上", "去", "入"]:
                if t in flat_name:
                    tone_value = tone_priority[t]
                    break

            # 解析开合信息
            kai_he_priority = 3  # 默认值
            if "開" in flat_name:
                kai_he_priority = 1
            elif "合" in flat_name:
                kai_he_priority = 2

            return (deng_priority, tone_value, kai_he_priority)

        cols = sorted({entry["中古等"] for entry in data}, key=sort_key)

        # 创建表头
        # 第一行第一列显示韻部
        selected_yunbu_label = QLabel(self.zhongguyunchar_select + "\n部" if self.zhongguyunchar_select else "")
        selected_yunbu_label.setFont(QFont("康熙字典體", 18))
        selected_yunbu_label.setAlignment(Qt.AlignCenter)
        selected_yunbu_label.setFixedWidth(100)
        selected_yunbu_label.setStyleSheet(
            "border: 2px solid brown; padding: 5px; color: #BA4A00; background-color: white;")
        self.header_layout.addWidget(selected_yunbu_label, 0, 0)
        # 如果未选择韻部，隐藏该单元格
        if not self.zhongguyunchar_select:
            selected_yunbu_label.hide()

        # 添加列头
        self.header_columns = []
        for col_idx, col_name in enumerate(cols, start=1):
            header = QLabel(col_name)
            header.setFont(QFont("康熙字典體", 14))  # 缩小字体适应长文本
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("border: 2px solid #E6B0AA; padding: 2px; color: brown; background-color: #FEF9F6;")
            self.header_layout.addWidget(header, 0, col_idx)
            self.header_columns.append(header)

        # 添加行头
        for row_idx, row_name in enumerate(rows, start=1):
            header = QLabel(row_name)
            header.setFont(QFont("康熙字典體", 16))
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("border: 2px solid #E6B0AA; padding: 5px; color: brown; background-color: #FEF9F6;")
            header.setFixedWidth(100)
            self.content_layout.addWidget(header, row_idx, 0)

        # =============== 列宽同步处理 ===============
        # 修改为立即同步列宽
        self.sync_column_widths()
        # 添加定时器处理可能的延迟渲染
        QTimer.singleShot(100, lambda: (
            self.sync_column_widths(),
            self.header_widget.setFixedWidth(self.content_widget.width() +
                                             self.findChild(QScrollArea).verticalScrollBar().width())
        ))

        # 填充数据
        cells = defaultdict(list)
        cell_matrix = {}  # 記錄所有單元格位置

        for entry in data:
            row_idx = rows.index(entry["中古聲"]) + 1  # +1 因为第一行是表头
            col_idx = cols.index(entry["中古等"]) + 1  # +1 因为第一列是行头

            label = QLabel()
            text = "  ".join([f'<font color="{item["color"]}">{item["字頭"]}[{item["上古聲"]}]</font>'
                              for item in entry["字頭"]])
            label.setText(text)
            label.setFont(QFont("Ipap", 15))
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("border: 1px solid #E6B0AA; padding: 2px; background-color: white;")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label.setProperty("has_content", "true")  # 标记有内容
            # 启用文本选择并添加事件过滤
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label.setContextMenuPolicy(Qt.CustomContextMenu)  # 启用自定义右键菜单
            label.customContextMenuRequested.connect(self.show_context_menu)
            label.installEventFilter(self)  # 安装事件过滤器

            # 添加到表格布局
            self.content_layout.addWidget(label, row_idx, col_idx)
            cells[col_idx].append(label)
            cell_matrix[(row_idx, col_idx)] = True  # 標記該位置有內容

        # 列可见性处理
        visible_columns = []
        for col_idx in range(1, len(cols) + 1):
            has_content = any(label.text().strip() != "" for label in cells[col_idx])
            if has_content:
                visible_columns.append(col_idx)
                self.header_columns[col_idx - 1].show()
            else:
                self.header_columns[col_idx - 1].hide()
                for label in cells[col_idx]:
                    label.hide()

        # 為空白單元格添加占位符
        for row_idx in range(1, len(rows) + 1):
            for col_idx in range(1, len(cols) + 1):
                if (row_idx, col_idx) not in cell_matrix:
                    placeholder = QLabel()
                    placeholder.setProperty("has_content", "false")  # 標記空白
                    placeholder.setStyleSheet("""
                        background-color: #EEEEEE;
                        border: 1px solid #E6B0AA;
                        min-width: 80px;
                        min-height: 40px;
                    """)  # 直接應用樣式
                    self.content_layout.addWidget(placeholder, row_idx, col_idx)

    def sync_column_widths(self):
        """同步表头和内容的列宽"""
        content_col_widths = {}
        for col in range(1, self.content_layout.columnCount()):
            max_width = 0
            for row in range(self.content_layout.rowCount()):
                item = self.content_layout.itemAtPosition(row, col)
                if item and item.widget().isVisible():
                    max_width = max(max_width, item.widget().width())
            content_col_widths[col] = max_width

        # 设置表头列宽（保持与内容列对齐）
        for col in range(1, self.header_layout.columnCount()):
            if col in content_col_widths:
                width = content_col_widths[col]
                header_item = self.header_layout.itemAtPosition(0, col)
                if header_item:
                    header_item.widget().setFixedWidth(width)

        # 调整表头容器布局策略
        self.header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.header_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐

    def resizeEvent(self, event):
        """重写窗口大小变化事件"""
        # 先执行同步列宽
        self.sync_column_widths()
        # 然后调整表头容器的总宽度（加上滚动条宽度）
        scrollbar_width = self.findChild(QScrollArea).verticalScrollBar().width()
        self.header_widget.setFixedWidth(self.content_widget.width() + scrollbar_width)
        super().resizeEvent(event)

    def save_table_image(self):
        """支持用户选择存储路径的方案"""
        from PyQt5.QtGui import QPainter, QImage
        from PyQt5.QtCore import Qt, QStandardPaths, QDateTime, QTimer
        from PyQt5.QtWidgets import QApplication, QFileDialog
        import os
        try:
            # 公共参数准备
            desktop = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd-hhmmss")
            base_name = f"韻圖_{self.zhongguyunchar_select or '未選擇'}_{timestamp}"
            # 强制界面刷新
            self.header_widget.updateGeometry()
            QApplication.processEvents()

            def capture_and_save():
                try:
                    # === 表头截图 ===
                    header_img = QImage(self.header_widget.size(), QImage.Format_ARGB32)
                    header_img.fill(Qt.white)
                    painter = QPainter(header_img)
                    self.header_widget.render(painter)
                    painter.end()
                    # 裁剪右侧25像素
                    cropped_header = header_img.copy(0, 0, max(50, header_img.width() - 25), header_img.height())
                    # === 内容截图 ===
                    scroll_area = self.findChild(QScrollArea)
                    content_widget = scroll_area.widget()
                    original_size = content_widget.size()
                    target_width = cropped_header.width()
                    scale_ratio = target_width / original_size.width()
                    target_height = int(original_size.height() * scale_ratio)
                    content_img = QImage(target_width, target_height, QImage.Format_ARGB32)
                    content_img.fill(Qt.white)
                    painter = QPainter(content_img)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    painter.scale(scale_ratio, scale_ratio)
                    content_widget.render(painter)
                    painter.end()
                    # === 合并图片 ===
                    combined = QImage(
                        cropped_header.width(),
                        cropped_header.height() + content_img.height(),
                        QImage.Format_ARGB32
                    )
                    combined.fill(Qt.white)
                    painter = QPainter(combined)
                    painter.drawImage(0, 0, cropped_header)
                    painter.drawImage(0, cropped_header.height(), content_img)
                    painter.end()
                    # === 用户选择保存路径 ===
                    default_path = os.path.join(desktop, f"{base_name}.png")
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "保存當前韻圖",
                        default_path,
                        "PNG圖片 (*.png);;所有文件 (*)"
                    )
                    if file_path:
                        # 自动添加扩展名
                        if not file_path.lower().endswith('.png'):
                            file_path += '.png'
                        combined.save(file_path)
                        QMessageBox.information(
                            self,
                            "保存成功",
                            f"韻圖已保存至：\n{file_path}"
                        )
                    else:
                        QMessageBox.warning(self, "取消保存", "您取消了操作")
                except Exception as e:
                    QMessageBox.critical(self, "錯誤", f"截圖失敗：{str(e)}")

            QTimer.singleShot(200, capture_and_save)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"初始化失敗：{str(e)}")

    def eventFilter(self, source, event):
        """处理文本选择事件（新逻辑）"""
        if isinstance(source, QLabel) and event.type() == QEvent.MouseButtonRelease:
            # 仅记录原始选中文本（不清理格式）
            self.raw_selected_text = source.selectedText().strip()  # 新字段
            self.current_label = source
            # 初始化清理后的文本字段
            self.cleaned_selected_text = ""  # 新字段
        return super().eventFilter(source, event)

    def show_context_menu(self, pos):
        """显示自定义右键菜单"""
        menu = QMenu()

        # 添加动作
        copy_action = menu.addAction("複製")
        remark_action = menu.addAction("備註")
        # 更新信号连接方式
        copy_action.triggered.connect(self._handle_raw_copy)  # 修改点1
        remark_action.triggered.connect(self._handle_remark_query)  # 修改点2

        menu.exec_(self.current_label.mapToGlobal(pos))

    def _handle_raw_copy(self):
        """处理原始复制操作"""
        if hasattr(self, 'raw_selected_text') and self.raw_selected_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.raw_selected_text)

            # 设置工具提示的全局样式
            QToolTip.setFont(QFont("IpaP", 15))  # 设置字体和大小
            QToolTip.showText(
                QCursor.pos(),
                f"已複製原始字符: {self.raw_selected_text}",
                self,
                QRect(),
                1700
            )

    def _handle_remark_query(self):
        """处理需要清理格式的備註查询"""
        # 汉字正则表达式（包含所有Unicode汉字区块）
        hanzi_pattern = r'''
            [\u4E00-\u9FFF]            
            |[\u3400-\u4DBF]            
            |[\U00020000-\U0002A6DF]    
            |[\U0002A700-\U0002B73F]    
            |[\U0002B740-\U0002B81F]    
            |[\U0002B820-\U0002CEAF]    
            |[\U0002CEB0-\U0002EBEF]    
            |[\U00030000-\U0003134F]    
            |[\uF900-\uFAFF]          
            |[\U0002F800-\U0002FA1F]   
        '''

        # 查找第一个汉字（支持代理对）
        match = re.search(
            hanzi_pattern,
            self.raw_selected_text,
            re.VERBOSE | re.UNICODE
        )

        if not match:
            QMessageBox.warning(self, "提示",
                                f"未檢測到有效漢字（原始內容：{self.raw_selected_text}）")
            return

        # 提取匹配结果（自动处理代理对）
        self.cleaned_selected_text = match.group()
        print(f"原始文本：{self.raw_selected_text} → 精确提取：{self.cleaned_selected_text}")

        # 使用清洗后字头进行查询
        self.selected_text = self.cleaned_selected_text
        threading.Thread(target=self._query_remark_db).start()

    def _query_remark_db(self):
        """数据库查询后台任务（增强版）"""
        connection = None
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 1. 先查询字头出现次数判断是否多音字
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ancienttable1
                WHERE 字頭 = ? 
                LIMIT 1
            """, (self.selected_text,))

            count_result = cursor.fetchone()
            variant_pron = count_result[0] > 1 if count_result else False

            # 2. 查询备注内容
            cursor.execute("""
                            SELECT 備註 
                            FROM ancienttable1
                            WHERE 字頭 = ? 
                            LIMIT 1
                        """, (self.selected_text,))

            remark_result = cursor.fetchone()

            # 3. 根据多音字状态和备注内容组合最终输出
            if remark_result and remark_result['備註']:  # 存在有效备注
                remark_content = remark_result['備註']
                status = "found"

                # 添加多音字提示前缀
                if variant_pron:
                    remark_content = f"【{self.selected_text}字存在異讀】\n{remark_content}"
            else:  # 无有效备注
                status = "not_found"
                # 根据多音字状态生成不同提示
                if variant_pron:
                    remark_content = f"{self.selected_text}字存在異讀，但暫無其它備註信息。"
                else:
                    remark_content = f"{self.selected_text}字暫無備註。"
            # 传递结果
            self._show_remark_result.emit(remark_content, self.selected_text, status)
        except Exception as e:
            self._show_remark_result.emit(f"查询失败：{str(e)}", "", "error")
        finally:
            if connection:
                connection.close()

    # 修改信号定义
    _show_remark_result = pyqtSignal(str, str, str)  # (备注内容, 字头, 状态)

    def show_remark_dialog(self, remark, character, status):
        """显示备注对话框（增强版）"""
        dialog = QDialog(self)
        # 关键代码：禁用帮助按钮
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle(f"字頭備註 - {self.cleaned_selected_text}")

        layout = QVBoxLayout()

        # 创建带格式的文本显示
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMinimumSize(400, 300)

        # 设置不同状态的显示样式
        if status == "not_found":
            text_edit.setHtml(f"""
                <p style='color: black; font-size: 14pt; text-align: center;'>
                    {remark}
                </p>
            """)
        elif status == "error":
            text_edit.setHtml(f"""
                <p style='color: red; font-weight: bold;'>
                    {remark}
                </p>
            """)
        else:
            # 保留数据库原始格式（含换行符）
            formatted_remark = remark.replace('\n', '<br>')
            text_edit.setHtml(f"""
                <div style='font-size: 14pt; line-height: 1.5;'>
                    {formatted_remark}
                </div>
            """)

        # 添加操作按钮
        btn_box = QDialogButtonBox()
        btn_box.setStyleSheet('font-size: 14pt')
        copy_btn = btn_box.addButton("複製備註內容", QDialogButtonBox.ActionRole)

        copy_btn.clicked.connect(lambda: self._copy_remark(text_edit.toPlainText()))

        layout.addWidget(text_edit)
        layout.addWidget(btn_box)
        dialog.setLayout(layout)
        dialog.exec_()

    def _copy_remark(self, text):
        """复制备注内容"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QToolTip.setFont(QFont("IpaP", 15))  # 设置字体和大小
        QToolTip.showText(
            QCursor.pos(),
            "備註內容已複製",
            self,
            QRect(),
            1700
        )


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
            cursor = connection.cursor()

            # 查询
            sql = """
                    SELECT 字頭, 中古韻
                    FROM ancienttable1
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
            cursor = connection.cursor()
            # 查询
            sql = """
                    SELECT 字頭, 上古聲
                    FROM ancienttable1
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
                FROM ancienttable1 
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
        self.setGeometry(110, 200, 1600, 900)
        self.setFixedWidth(1600)
        self.setMinimumHeight(800)
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        self.current_table = "ancienttable1"  # 新增：当前选择的表
        self.initUI()

    def initUI(self):
        # 創建主布局
        layout = QVBoxLayout()
        self.setLayout(layout)
        # ========== 左上角下拉选择框 ==========
        top_layout = QHBoxLayout()
        layout.insertLayout(0, top_layout)  # 插入到最顶部

        # 标签
        table_label = QLabel("選擇字表:")
        table_label.setFont(QFont("康熙字典體", 16))
        table_label.setStyleSheet("color: #662A1D; margin-right: 10px;")
        top_layout.addWidget(table_label)

        # 下拉选择框
        self.table_combo = QComboBox()
        self.table_combo.addItem("古音表 (默認)")
        self.table_combo.addItem("廣韻字表")
        self.table_combo.addItem("玉篇反切校表")
        self.table_combo.setFont(QFont("康熙字典體", 15))
        self.table_combo.setCursor(Qt.PointingHandCursor)
        self.table_combo.setFixedHeight(50)

        self.table_combo.currentIndexChanged.connect(self.change_table)
        top_layout.addWidget(self.table_combo)
        top_layout.addStretch(1)  # 右侧伸缩空间
        # ========================================

        # 創建輸入框和標籤的布局
        input_layout = QHBoxLayout()
        layout.addLayout(input_layout)

        # 在左側添加伸縮空間
        input_layout.addStretch(1)

        # 標籤
        label = QLabel("輸入待查字:    ")
        label.setFont(QFont("康熙字典體", 24))
        label.setAlignment(Qt.AlignCenter)  # 將標籤居中
        label.setStyleSheet("color: #662A1D;")  # 設置標籤文字顏色
        label.setContentsMargins(0, 40, 0, 40)  # 設置上下邊距
        input_layout.addWidget(label)

        # 輸入框
        self.search_chara_entry = QLineEdit()
        self.search_chara_entry.setFont(QFont("宋体", 23, QFont.Bold))  # 設置字體為"宋体"，字號為23
        self.search_chara_entry.setFixedHeight(60)  # 固定輸入框的高度為60px
        self.search_chara_entry.setFixedWidth(300)  # 固定輸入框的寬度為300px
        self.search_chara_entry.setAlignment(Qt.AlignCenter)  # 將輸入框中的文本居中
        input_layout.addWidget(self.search_chara_entry)

        # 創建查詢按鈕 - 直接添加到input_layout
        search_chara_button = QPushButton("查詢")
        search_chara_button.setFont(QFont("康熙字典體", 16))
        search_chara_button.setFixedWidth(150)  # 縮小按鈕寬度以適應水平排列
        search_chara_button.setFixedHeight(60)  # 設置按鈕高度與輸入框一致
        search_chara_button.setStyleSheet(f"color: #B03A2E; padding: 5px;")
        search_chara_button.clicked.connect(self.check_input)
        search_chara_button.setCursor(Qt.PointingHandCursor)  # 鼠標懸停時顯示手形光標
        input_layout.addWidget(search_chara_button)

        # 清空按鈕 - 直接添加到input_layout
        clear_button = QPushButton("重置")
        clear_button.setFont(QFont("康熙字典體", 16))
        clear_button.setFixedWidth(150)  # 縮小按鈕寬度以適應水平排列
        clear_button.setFixedHeight(60)  # 設置按鈕高度與輸入框一致
        clear_button.setStyleSheet(f"color: #784212; padding: 5px;")
        clear_button.clicked.connect(self.clear_all)
        clear_button.setCursor(Qt.PointingHandCursor)  # 鼠標懸停時顯示手形光標
        input_layout.addWidget(clear_button)

        # 在右側添加伸縮空間
        input_layout.addStretch(1)

        # ========== 提示标签区域 ==========
        # 创建提示标签（作为实例变量）
        self.tip_label = QLabel()
        self.tip_label.setFont(QFont("Ipap", 13))
        self.tip_label.setStyleSheet("color: gray;")
        self.tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tip_label)

        # 初始化提示文本 - 确保在UI初始化后调用
        self.update_tip_label()  # 更新提示标签

        # 連接回車事件
        self.search_chara_entry.returnPressed.connect(self.check_input)

        # 创建一个滚动区域用于包含表格
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # 创建一个用于包含表格的子控件
        table_container = QWidget()
        self.table_layout = QGridLayout(table_container)
        self.table_layout.setSpacing(2)  # 设置布局的间距为 2
        scroll_area.setWidget(table_container)

    # 更新提示标签的方法（带动画效果）
    def update_tip_label(self, animate=True):
        # 获取当前提示文本
        base_tip = "*提示：僅支持繁體、單個漢字輸入"
        if self.current_table == "ancienttable1":
            tip_text = f"{base_tip}\n————古音表18668條數據：王弘治老師————"
        elif self.current_table == "guangyun":
            tip_text = f"{base_tip}\n————廣韻字表25035條數據：Poem————"
        elif self.current_table == "yupianfanqiejiao":
            tip_text = f"{base_tip}\n————玉篇反切校24154條數據：Poem————"
        else:
            tip_text = base_tip

        # 设置文本
        print(f"更新提示标签: {self.current_table} -> {tip_text}")
        self.tip_label.setText(tip_text)

    # 切换查询表
    def change_table(self, index):
        # 打印当前索引值用于调试
        print(f"切换表索引: {index}")
        # 更新当前表
        if index == 0:
            self.current_table = "ancienttable1"
        elif index == 1:
            self.current_table = "guangyun"
        elif index == 2:
            self.current_table = "yupianfanqiejiao"

        # 打印当前表值用于调试
        print(f"当前表: {self.current_table}")

        # 更新提示标签
        print(f"切换表索引: {index} -> {self.current_table}")
        self.update_tip_label()

        # 切换表时清空输入框和表格内容
        self.clear_all()  # 新增：调用clear_all方法清空内容

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
            QMessageBox.warning(self, "警告", "僅允許輸入單個漢字！")

    # 查询数据库
    def query_database(self, chara):
        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # 根据选择的表构建不同的查询
                if self.current_table == "ancienttable1":
                    sql = "SELECT * FROM ancienttable1 WHERE 字頭=?"
                elif self.current_table == "guangyun": # 广韵字表
                    sql = "SELECT * FROM guangyun WHERE 廣韻字頭=?"
                elif self.current_table == "yupianfanqiejiao": # 玉篇反切校表
                    sql = "SELECT * FROM yupianfanqiejiao WHERE 玉篇字頭=?"

                cursor.execute(sql, (chara,))
                result = cursor.fetchall()

                if result:
                    # 将Row对象转换为可读格式
                    readable_result = [dict(row) for row in result]
                    print("查询结果:", readable_result)
                    self.display_results(result)
                else:
                    QMessageBox.information(self, "無結果", "未查到相關字")
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

        # 根据当前表设置表头
        if self.current_table == "ancienttable1":
            custom_headers = ["數據\nid", "字 頭", "上古\n聲母", "上古\n韻部", "中古\n聲母",
                              "中古\n韻部", "聲調", "等", "開合", "聲符", "備註"]
            headers = result[0].keys()
        elif self.current_table == "guangyun":  # 广韵字表
            custom_headers = ["字\n序", "字\n頭", "切韻\n擬音", "廣韻\n聲符", "上\n字", "下\n字",
                              "聲\n母", "韻\n部", "開\n合", "等", "調",
                              "頁\n序", "廣韻\n釋義"]
            headers = result[0].keys()
        elif self.current_table == "yupianfanqiejiao":  # 玉篇反切校表
            custom_headers = ["字\n頭",  "聲\n符", "字\n音", "聲\n紐", "呼", "等", "韻\n部",
                              "調", "聲類", "攝", "殘卷\n反切\n上字","上\n字\n音", "殘卷\n反切\n下字","下\n字\n音",
                              "宋本\n反切", "全本\n反切", "裴本\n反切", "廣韻\n反切"]
            headers = result[0].keys()

        self.table_layout.setSpacing(1)  # 设置布局的间距为 1，若為0則是去除单元格之间的间隙

        # 创建表头
        for col, header in enumerate(custom_headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("康熙字典體", 18))

            # 基本样式
            base_style = "border: 1px solid #6C1002; background-color: #FBF0F0; padding: 5px; color: #6C1002;"

            # 只给表头的第一个单元格添加左上角圆角
            if col == 0:
                base_style += "border-top-left-radius: 15px;"
            # 只给表头的最后一个单元格添加右上角圆角
            elif col == len(custom_headers) - 1:
                base_style += "border-top-right-radius: 15px;"

            header_label.setStyleSheet(base_style)
            header_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(header_label, 0, col)

        # 列差异检测（广韵表跳过最后一列）
        column_differences = [False] * len(headers)
        if len(result) > 1:
            skip_last_col = self.current_table == "guangyun"

            for col_num in range(len(headers)):
                # 只跳过最后一列（如果设置），不跳过第0列
                if col_num == 0 or (skip_last_col and col_num == len(headers) - 1):
                    continue  # 跳过最后一列（廣韻釋義）

                first_value = str(result[0][headers[col_num]])
                for row_num in range(1, len(result)):
                    if str(result[row_num][headers[col_num]]) != first_value:
                        column_differences[col_num] = True
                        break

        # 创建表格内容
        for row_num, row_data in enumerate(result):
            # 记录当前行的最大高度
            row_max_height = 0
            for col_num, key in enumerate(headers):
                # 广韵表最后一列特殊处理
                if self.current_table == "guangyun" and col_num == len(headers) - 1:
                    # 创建容器widget作为单元格背景
                    cell_widget = QWidget()

                    # 获取表格总行数和总列数
                    total_rows = len(result)
                    total_cols = len(headers)

                    # 设置单元格基础样式
                    cell_style = "border: 1px solid #8A1A00; background-color: #FFF9F9; padding: 10px;"

                    # 圆角处理
                    if row_num == total_rows - 1 and col_num == total_cols - 1:
                        cell_style += "border-bottom-right-radius: 15px;"

                    cell_widget.setStyleSheet(cell_style)

                    # 创建水平布局
                    cell_layout = QHBoxLayout(cell_widget)
                    cell_layout.setContentsMargins(0, 0, 0, 0)
                    cell_layout.setAlignment(Qt.AlignCenter)

                    # 创建透明按钮
                    btn = QPushButton("點此\n查看")
                    btn.setFont(QFont("康熙字典體", 14))
                    btn.setStyleSheet("""
                                            QPushButton {
                                                background-color: transparent;
                                                border: none;
                                                color: #1a0dab;
                                                text-decoration: underline;
                                                padding: 0;
                                                margin: 0;
                                            }
                                            QPushButton:hover {
                                                color: #681da8;
                                            }
                                        """)
                    btn.setCursor(Qt.PointingHandCursor)

                    # 存储释义数据
                    meaning = str(row_data[key])
                    btn.clicked.connect(lambda _, m=meaning: self.show_meaning(m))

                    # 将按钮添加到布局
                    cell_layout.addWidget(btn)

                    # 添加单元格到表格布局
                    self.table_layout.addWidget(cell_widget, row_num + 1, col_num)

                else:
                    # 正常文本标签
                    value_label = QLabel(str(row_data[key]))
                    value_label.setWordWrap(True)  # 允许自动换行
                    # 优化后的字体设置
                    if self.current_table == "ancienttable1":
                        if col_num == 2:  # 古音表 上古聲用IpaP字體
                            value_label.setFont(QFont("IpaP", 20))
                        elif col_num == 0:  # 古音表 序號的字小一點
                            value_label.setFont(QFont("宋体", 16))
                        else:
                            value_label.setFont(QFont("宋体", 20))
                    elif self.current_table == "guangyun":
                        if col_num == 2:  # 廣韻表 構擬用IpaP
                            value_label.setFont(QFont("IpaP", 20))
                        elif  col_num == 11 or col_num == 0:  # 廣韻表 序號和頁序的字小一點
                            value_label.setFont(QFont("宋体", 16))
                        else:
                            value_label.setFont(QFont("宋体", 20))
                    elif self.current_table == "yupianfanqiejiao":
                        if col_num == 2 or col_num == 11 or col_num == 13:
                            value_label.setFont(QFont("IpaP", 15))
                        elif  col_num == 14 or col_num == 15 or col_num == 16 or col_num == 17:
                            value_label.setFont(QFont("宋体", 15))
                        else:
                            value_label.setFont(QFont("宋体", 18))

                    # 获取表格总行数和总列数
                    total_rows = len(result)
                    total_cols = len(headers)
                    # 设置基础样式
                    base_style = "border: 1px solid #8A1A00; background-color: #FFF9F9; padding: 10px; color: #3C0D00;"
                    # 只在最后一行添加角落圆角
                    if row_num == total_rows - 1:
                        if col_num == 0:  # 左下角单元格
                            base_style += "border-bottom-left-radius: 15px;"
                        elif col_num == total_cols - 1:  # 右下角单元格
                            base_style += "border-bottom-right-radius: 15px;"
                    # 如果该列的值不同，设置不同样式
                    if column_differences[col_num]:
                        base_style = "border: 1px solid #CF3801; background-color: #FFECD4; padding: 10px; color: #D53A00;"
                        # 重新添加圓角樣式（如果需要）
                        if row_num == total_rows - 1:
                            if col_num == 0:  # 左下角单元格
                                base_style += "border-bottom-left-radius: 10px;"
                            elif col_num == total_cols - 1:  # 右下角单元格
                                base_style += "border-bottom-right-radius: 10px;"
                    value_label.setStyleSheet(base_style)
                    value_label.setAlignment(Qt.AlignCenter)
                    value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
                    self.table_layout.addWidget(value_label, row_num + 1, col_num)

    # 新增：显示广韵释义
    def show_meaning(self, meaning):
        meaning_dialog = QDialog(self)
        meaning_dialog.setWindowTitle("賢哉古音 - 查字：廣韻釋義")
        # 移除帮助按钮
        meaning_dialog.setWindowFlags(
            meaning_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        meaning_dialog.setFixedSize(600, 400)

        layout = QVBoxLayout(meaning_dialog)
        layout.setContentsMargins(20, 20, 20, 20)  # 设置布局边距
        # 使用QTextEdit替代QLabel实现可复制文本
        text_edit = QTextEdit()
        text_edit.setPlainText(meaning)  # 设置纯文本内容
        text_edit.setFont(QFont("宋体", 15))
        text_edit.setReadOnly(True)  # 设为只读模式
        text_edit.setFrameShape(QFrame.NoFrame)  # 移除边框
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 按需显示滚动条

        # 设置文本对齐方式（顶部左对齐）
        text_edit.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # 添加到主布局
        layout.addWidget(text_edit)

        def copy_to_clipboard(text):
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "複製成功", "釋義已複製！", QMessageBox.Ok)

        # === 新增按钮代码开始 ===
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        copy_button = QPushButton("複製廣韻釋義")
        copy_button.setFont(QFont("康熙字典體", 12))
        copy_button.setStyleSheet("color: #8B1A1A;")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setFixedHeight(50)
        copy_button.clicked.connect(lambda: copy_to_clipboard(meaning))

        button_layout.addWidget(copy_button)
        layout.addLayout(button_layout)
        # === 新增按钮代码结束 ===

        meaning_dialog.exec_()


# 反切對照窗口———————————————————————————————————————————————————————
class FanqieCompareWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("賢哉古音 - 反切對照")
        self.setGeometry(200, 200, 1500, 800)
        self.setFixedWidth(1500)
        self.setMinimumHeight(800)
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')
        self.initUI()

    def initUI(self):
        # 創建主布局
        FQlayout = QVBoxLayout()
        self.setLayout(FQlayout)

        # 創建輸入框和標籤的布局
        FQinput_layout = QHBoxLayout()
        FQlayout.addLayout(FQinput_layout)

        # 在左側添加伸縮空間
        FQinput_layout.addStretch(1)

        # 標籤
        QIElabel = QLabel("輸入被切字:    ")
        QIElabel.setFont(QFont("康熙字典體", 24))
        QIElabel.setAlignment(Qt.AlignCenter)  # 將標籤居中
        QIElabel.setStyleSheet("color: #662A1D;")  # 設置標籤文字顏色
        QIElabel.setContentsMargins(0, 40, 0, 40)  # 設置上下邊距
        FQinput_layout.addWidget(QIElabel)

        # 輸入框
        self.FQ_entry = QLineEdit()
        self.FQ_entry.setFont(QFont("宋体", 23, QFont.Bold))  # 設置字體為"宋体"，字號為23
        self.FQ_entry.setFixedHeight(60)  # 固定輸入框的高度為60px
        self.FQ_entry.setFixedWidth(300)  # 固定輸入框的寬度為300px
        self.FQ_entry.setAlignment(Qt.AlignCenter)  # 將輸入框中的文本居中
        FQinput_layout.addWidget(self.FQ_entry)

        # 創建查詢按鈕 - 直接添加到input_layout
        FQ_button = QPushButton("一鍵切它！")
        FQ_button.setFont(QFont("康熙字典體", 16))
        FQ_button.setFixedWidth(190)  # 縮小按鈕寬度以適應水平排列
        FQ_button.setFixedHeight(60)  # 設置按鈕高度與輸入框一致
        FQ_button.setStyleSheet(f"color: #B03A2E; padding: 5px;")
        FQ_button.clicked.connect(self.FQcheck_input)
        FQ_button.setCursor(Qt.PointingHandCursor)  # 鼠標懸停時顯示手形光標
        FQinput_layout.addWidget(FQ_button)

        # 清空按鈕 - 直接添加到input_layout
        FQclear_button = QPushButton("重置")
        FQclear_button.setFont(QFont("康熙字典體", 16))
        FQclear_button.setFixedWidth(150)  # 縮小按鈕寬度以適應水平排列
        FQclear_button.setFixedHeight(60)  # 設置按鈕高度與輸入框一致
        FQclear_button.setStyleSheet(f"color: #784212; padding: 5px;")
        FQclear_button.clicked.connect(self.FQclear_all)
        FQclear_button.setCursor(Qt.PointingHandCursor)  # 鼠標懸停時顯示手形光標
        FQinput_layout.addWidget(FQclear_button)

        # 在右側添加伸縮空間
        FQinput_layout.addStretch(1)

        # 添加提示標籤
        FQtip_label = QLabel("*提示：僅支持繁體、單個漢字輸入\n————反切對照表7475條數據：Poem————")
        FQtip_label.setFont(QFont("Ipap", 13))
        FQtip_label.setStyleSheet("color: gray;")
        FQtip_label.setAlignment(Qt.AlignCenter)  # 水平居中
        FQlayout.addWidget(FQtip_label)

        # 連接回車事件
        self.FQ_entry.returnPressed.connect(self.FQcheck_input)

        # 创建一个滚动区域用于包含表格
        FQscroll_area = QScrollArea()
        FQscroll_area.setWidgetResizable(True)
        FQlayout.addWidget(FQscroll_area)

        # 创建一个用于包含表格的子控件
        FQtable_container = QWidget()
        self.FQtable_layout = QGridLayout(FQtable_container)
        self.FQtable_layout.setSpacing(2)  # 设置布局的间距为 2
        FQscroll_area.setWidget(FQtable_container)

    # 清空输入框和表格内容
    def FQclear_all(self):
        self.FQ_entry.clear()
        for i in reversed(range(self.FQtable_layout.count())):
            widget = self.FQtable_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def closeEvent(self, event):
        """在窗口关闭时清空内容"""
        self.FQclear_all()  # 先调用 clear_all 清空输入框和表格内容
        event.accept()  # 允许窗口关闭

    # 检查输入并查询数据库
    def FQcheck_input(self):
        FQchara = self.FQ_entry.text()
        if re.fullmatch(r'^.$', FQchara):  # 正则匹配单个汉字
            print("合法输入")
            self.FQquery_database(FQchara)
        else:
            QMessageBox.warning(self, "警告", "僅允許輸入單個漢字！")

    # 查询数据库
    def FQquery_database(self, FQchara):
        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                sql = "SELECT * FROM fanqieduizhao WHERE 被切字=?"
                cursor.execute(sql, (FQchara,))
                result = cursor.fetchall()
                if result:
                    # 将Row对象转换为可读格式
                    readable_result = [dict(row) for row in result]
                    print("查询结果:", readable_result)
                    self.FQdisplay_results(result)
                else:
                    QMessageBox.information(self, "無結果", "未查到相關字")
            except sqlite3.Error as e:
                print(f"数据库查询失败: {e}")
                QMessageBox.warning(self, "警告", "数据库查询失败")
            finally:
                connection.close()
        else:
            QMessageBox.warning(self, "警告", "数据库连接失败")

    # 显示查询结果
    def FQdisplay_results(self, result):
        # 清空表格布局中的内容
        self.FQclear_all()

        # 自定义的表头字符
        FQcustom_headers = ["字\n序", "被\n切\n字", "音標", "經典釋文\n反切", "原本玉篇\n反切", "宋本玉篇\n反切",
                            "廣韻\n反切"]
        # 数据库列名，用于从查询结果中获取数据
        headers = result[0].keys()  # 这里仍然保留数据库中的列名
        self.FQtable_layout.setSpacing(2)  # 设置布局的间距为 2，若為0則是去除单元格之间的间隙

        # 创建表头
        for col, header in enumerate(FQcustom_headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("康熙字典體", 18))

            # 基本样式
            base_style = "border: 1px solid #6C1002; background-color: #FBF0F0; padding: 5px; color: #6C1002;"

            # 只给表头的第一个单元格添加左上角圆角
            if col == 0:
                base_style += "border-top-left-radius: 15px;"
            # 只给表头的最后一个单元格添加右上角圆角
            elif col == len(FQcustom_headers) - 1:
                base_style += "border-top-right-radius: 15px;"

            header_label.setStyleSheet(base_style)
            header_label.setAlignment(Qt.AlignCenter)
            self.FQtable_layout.addWidget(header_label, 0, col)

        # 比较每列的值，用于标记不同的列
        column_differences = [False] * len(headers)  # 初始化标记，默认为没有差异

        if len(result) > 1:  # 如果行数大于1，说明是多音字
            for col_num in range(len(headers)):
                # 跳過第一列的差異檢測（不標記第一列）
                if col_num == 0:
                    continue

                first_value = str(result[0][headers[col_num]])  # 取第一行的值
                # 检查该列的所有行是否有不同的值
                for row_num in range(1, len(result)):
                    if str(result[row_num][headers[col_num]]) != first_value:
                        column_differences[col_num] = True  # 如果有不同值，标记该列
                        break

        # 创建表格内容
        for row_num, row_data in enumerate(result):
            for col_num, key in enumerate(headers):
                FQvalue_label = QLabel(str(row_data[key]))
                FQvalue_label.setWordWrap(True)  # 允许自动换行

                # 如果是第3列（col_num == 2）且行号大于等于0（即第二行及之后），设置字体为 IpaP
                if col_num == 2 and row_num >= 0:
                    FQvalue_label.setFont(QFont("IpaP", 24))
                else:
                    FQvalue_label.setFont(QFont("宋体", 20))

                # 获取表格总行数和总列数
                total_rows = len(result)
                total_cols = len(headers)

                # 设置基础样式
                base_style = "border: 1px solid #8A1A00; background-color: #FFF9F9; padding: 10px; color: #3C0D00;"

                # 只在最后一行添加角落圆角
                if row_num == total_rows - 1:
                    if col_num == 0:  # 左下角单元格
                        base_style += "border-bottom-left-radius: 15px;"
                    elif col_num == total_cols - 1:  # 右下角单元格
                        base_style += "border-bottom-right-radius: 15px;"

                # 如果该列的值不同，设置不同样式
                if column_differences[col_num]:
                    base_style = "border: 1px solid #CF3801; background-color: #FFECD4; padding: 10px; color: #D53A00;"
                    # 重新添加圓角樣式（如果需要）
                    if row_num == total_rows - 1:
                        if col_num == 0:  # 左下角单元格
                            base_style += "border-bottom-left-radius: 10px;"
                        elif col_num == total_cols - 1:  # 右下角单元格
                            base_style += "border-bottom-right-radius: 10px;"

                FQvalue_label.setStyleSheet(base_style)
                FQvalue_label.setAlignment(Qt.AlignCenter)
                FQvalue_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许鼠标选择文本
                self.FQtable_layout.addWidget(FQvalue_label, row_num + 1, col_num)  # 使用 row_num + 1 使其显示在第二行及以后


# 關於窗口
class UpdateLogWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 开发者模式相关变量初始化
        self.dev_mode_click_count = 0
        self.dev_mode_timer = QTimer()
        self.dev_mode_timer.setSingleShot(True)
        self.dev_mode_timer.timeout.connect(self.reset_dev_mode_counter)

        # 设置窗口标题和大小
        self.setWindowTitle("賢哉古音 - 關於")
        self.setGeometry(400, 300, 1300, 900)

        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')

        # 设置窗口内容
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        # 创建布局
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        aboutTitle_label = QLabel()
        aboutTitle_label.setText("""關於軟件""")
        aboutTitle_label.setFont(QFont("康熙字典體", 20))
        aboutTitle_label.setStyleSheet("color: #8B1A1A;")
        aboutTitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(aboutTitle_label)

        aboutinfo_label = QLabel()
        aboutinfo_label.setText(
            """       賢哉古音是一款按照文科研究思路開發的音韻學電子字典，用更低的操作門檻為語言學研究者提供熟悉的界面。"""
            """軟件的基礎功能无須聯網，无須任何設置，只需要預先安裝幾種ttf字體。"""
            """目前版本的音韻材料來自王弘治老師和Poem，軟件製作和測試由郭宇軒完成。
        """)
        aboutinfo_label.setFont(QFont("Ipap", 16))
        aboutinfo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        aboutinfo_label.setStyleSheet("""
            QWidget {border: 1px solid brown; padding: 5px;}
        """)
        aboutinfo_label.setWordWrap(True)  # 允许自动换行
        layout.addWidget(aboutinfo_label)

        # 将"更新日誌"标签改为隐藏按钮
        self.dev_mode_button = QPushButton()
        self.dev_mode_button.setText("""更新日誌""")
        self.dev_mode_button.setFont(QFont("康熙字典體", 20))
        # 设置为透明无边框样式
        self.dev_mode_button.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: #8B1A1A;
                        text-align: left;
                        padding: 0;
                    }
                """)
        self.dev_mode_button.setFlat(True)  # 移除按钮的3D效果
        self.dev_mode_button.clicked.connect(self.handle_dev_mode_click)
        # 创建水平布局容器实现居中
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.addStretch(1)  # 左侧弹性空间
        button_layout.addWidget(self.dev_mode_button)
        button_layout.addStretch(1)  # 右侧弹性空间
        button_layout.setAlignment(Qt.AlignHCenter)  # 水平居中
        layout.addWidget(button_container)  # 添加到主布局

        # 创建日志内容标签
        log_label = QLabel()
        log_label.setTextFormat(Qt.RichText)  # 设置为富文本模式
        # 更新日志内容↓——————————————————————————————————————————
        log_label.setText("""
            <ul style="font-family: 'IpaP'; font-size: 35px; line-height: 2.0;">
                <li>v1.4.5 【當前版本】<br>
                            ·新增子功能[聲韻匹配試煉場【嘗嘗賢淡】]：匹配聲母或韻部的小遊戲，包括上古韻部、中古韻部、中古聲母同轄字的配合三種模式，並有三个難度等級可選；<br>
                            ·主頁面：新增退出確認；退出時關閉所有子功能窗口；<br>
                            ·[查字]：新增字表“玉篇反切校”，數據來源處新增數據條數；<br>
                            ·[反切對照查詢]：數據來源處新增數據條數；<br>
                            ·[《廣韻》聲符散佈]：新增單元格雙擊提示；<br>
                <li>v1.4.4 <br>
                            ·[聲符分佈和中古聲母]：功能名稱改為“[聲符-中古聲母] 關係”；<br>
                            ·程序：修復桌面圖標顯示錯誤的bug；所有功能窗口不允許重複打開多個；<br>
                            ·新增子功能[《廣韻》聲符散佈]：可查看所有聲符的分佈數據；<br>
                            ·新增子功能[反切對照查詢]：輸入被切字，查看《經典釋文》《玉篇》《廣韻》記載的反切異同；<br>
                            ·[查字]：可切換字表查詢，支持原“古音表”，新增“廣韻字表”；新增數據來源說明。<br>
                            ·[關於]：修改了部分UI；<br>
                            ·新增[開發者窗口]（用戶不可見），更新日誌部分技術性說明移入開發者窗口。<br>
                <li>v1.4.3 <br>
                            ·查中古韻：未選擇韻部時新增功能說明；備註可顯示有無異讀；<br>
                            ·賢哉Bot：接入DeepSeek，填寫API-key可使用智能問答；對話窗口形式更改；新增API-key設置按鈕和相關功能。<br>
                <li>v1.4.2<br>
                            ·首頁：按鈕重新排序；<br>
                            ·更新日誌：新增軟件介紹；<br>
                            ·查中古韻：窗口啟動時設為最大化；字頭顏色改為按上古韻分；上古韻部篩選按鈕依轄字數量排序；
                            支持保持當前韻圖并自定義輸出路徑；表格內字頭可以選中后點擊右鍵-查看備註；<br>
                            ·查字：支持顯示聲符和開合信息；<br>
                            ·新增子功能：聲符分佈，用於查看聲符在中古音中的分佈規律。<br>
                <li>v1.4.1<br>
                            ·查字：修改表格的圓角效果；修改功能按鈕佈局；新增輸入內容提示；<br>
                            ·圖標更新。<br>
                <li>v1.4.0<br>
                            ·查中古韻：以韻圖作為唯一顯示方式，移除原有簡易表格、移除原有韻圖子窗口。<br>
                <li>v1.3.9<br>
                            ·中古音韻部-韻圖顯示：修復韻圖空白單元格邊框、底色消失bug。<br>
                <li>v1.3.8<br>
                            ·中古音韻部-韻圖顯示：修復表格首行排序異常bug。<br>
                <li>v1.3.7<br>
                            ·中古音韻部-韻圖顯示：表格滾動時，首行固定，方便查看；*為配合此改動，首行文字方向改為垂直排列；<br>
                            ·已知問題：韻部字數較多時（仙、支等部），表格可能加載緩慢，待優化。<br>
                <li>v1.3.5<br>
                            ·賢哉bot：修復對話查字閃退bug；修改聊天氣泡大小。<br>
                <li>v1.3.4<br>
                            ·中古音韻部-韻圖顯示：修復左上角選中的韻部提示顯示不全的bug；韻圖首列按照《方言調查字表》的聲母順序重新排布；<br>
                            ·已知問題：使用bot對話查詢時，可能出現閃退，待修復。<br>
                <li>v1.3.3<br>
                            ·查字窗口:允許調整高度、允許表格滾動，以支持顯示讀音較多的字；<br>
                            ·中古音韻部-韻圖顯示：可以篩選上古韻部來源。<br>
                <li>v1.3.0<br>
                            ·各窗口的輸出表格：支持選中單元格内的字符，使用Ctrl+C複制。<br>
                <li>v1.2.9<br>
                            ·賢哉bot：修改對話查字時多音字的呈現方式；增加bot的幫助提示；<br>
                            ·查字：修復了關閉窗口再重新打開時，上一次查詢的結果未被清除的bug；<br>
                            ·更新日誌：修改了"關閉"按鈕的樣式。<br>
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
                            ·中古音韻部：修復了未選中韻部時多次點擊"以韻圖顯示結果"卡死的bug；<br>
                            ·查字：上古音的聲母音標改用國際音標專用字體（IpaP）；<br>
                            ·上古音韻部、中古音韻部查詢：窗口標題的"韻母"改為"韻部"。<br>
                <li>v1.1.9<br>
                            ·中古音韻部-韻圖顯示：加入了篩選維度"等"。<br>
                <li>v1.1.8<br>
                            ·中古音韻部-韻圖顯示：加入上古音聲母的顏色圖例；<br>
                              未選中韻部時，點擊"以韻圖顯示結果"會彈出警告；<br>
                            ·所有頁面的按鈕：鼠標移動到按鈕上時，指針變成手形。<br>
                <li>v1.1.7<br>
                            ·中古音韻部-韻圖顯示：修復1.1.6版本中，顏色重複使用的bug和調整窗口大小導致的表格列寬顯示bug；
                                修復結果中概率出現白色字體bug。<br>
                <li>v1.1.6<br>
                            ·中古音韻部-韻圖顯示：現在可以从"等"、"中古音聲母"、"聲調"、"上古音聲母"四個維度分類顯示中古音韻部的歸屬字；<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>  
                            ·更新日誌：更改了日誌的文本字體。<br>
                            ·[韻圖顯示]已知問題：<br>
                                -①程序隨機選取顏色時可能重複使用某種顏色，待修復 <br>
                                -②在調整窗口大小時，結果表格的寬度顯示bug<br>
                <li>v1.1.5<br>
                            ·中古音韻部-韻圖顯示：現在可以从"等"、"中古音聲母"、"聲調"三個維度分類顯示中古音韻部的歸屬字。<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>           
                <li>v1.1.3<br>
                            ·中古音聲母：增加"雲"母按鈕；<br>
                            ·中古音韻部：增加"以韻圖形式顯示"按鈕，可以在新窗口用韻圖的形式，从"等"和"中古音聲母"兩個維度分類顯示中古音韻部的歸屬字；<br>
                                【測試中，未來版本可能保留、修改呈現形式或移除】<br>                
                            ·中古音韻部：v1.0.9版本加入的篩選按鈕已移除。<br>
                <li>v1.1.1<br>
                            ·數據庫：更正了"𥝖"字的中古音韻部數據，修改了中古音韻部查詢的相關按鈕。<br>
                <li>v1.1.0<br>
                            ·中古音韻部查詢：嘗試標記"等"時，顯示"加载中"提示【測試功能，未來版本可能修改或移除】；<br>
                            ·中古音韻部查詢：優化輸出結果的字間距，使文字顏色變化前後字間距一致；<br>
                            ·更新日誌窗口：更改為倒序排列，最新修改點置頂顯示，方便查閱。<br>
                <li>v1.0.9<br>
                            ·上古音韻部查詢、中古音聲母&韻部查詢：修復了點擊過的按鈕文字變黑的問題；<br>
                            ·中古音韻部查詢：加入多維度標記按鈕【測試中，目前儘能標記"等"】。 <br>              
                <li>v1.0.4 <br>
                            ·中古音聲母查詢窗口：表述改動"中古音的歸屬字"→"該中古音聲母的歸屬字"；<br>
                            ·更新日誌窗口：內容支持滾動；<br>
                            ·上古音聲母&韻部查詢、中古音聲母&韻部查詢窗口：輸出結果時，允許點擊的按鈕保持高亮；<br>
                            ·主窗口只允許同時存在一個，子窗口逐一適配中。 <br>  
                <li>v1.0.3 <br>
                            ·查上古聲母：更新頁面佈局與查詢邏輯；<br>
                            ·查字窗口：支持輸入后按Enter鍵查詢。<br>
                <li>v1.0.2 <br>  
                            ·數據庫條目：修正中古韻部[咸]誤作[鹹]的錯誤；<br>
                            ·查中古韻部：按鈕基於切韻韻系、廣韻韻目重新排序；<br>
                            ·新增子功能：[更新日誌]。<br>                                
                <li>v1.0.1 - UI適配部分高分辨率設備。</li>                          
                <li>v1.0.0 - 初始版本打包。</li>
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

    def handle_dev_mode_click(self):
        """处理开发者模式点击事件"""
        self.dev_mode_click_count += 1

        # 如果是第一次点击，启动5秒计时器
        if self.dev_mode_click_count == 1:
            self.dev_mode_timer.start(5000)  # 5秒后重置计数器

        # 达到8次点击后触发开发者模式
        if self.dev_mode_click_count >= 8:
            self.dev_mode_timer.stop()
            self.open_dev_mode()
            self.reset_dev_mode_counter()

    def reset_dev_mode_counter(self):
        """重置开发者模式计数器"""
        self.dev_mode_click_count = 0

    def open_dev_mode(self):
        """打开开发者模式窗口"""
        dev_dialog = QDialog(self)
        dev_dialog.setWindowTitle("賢哉古音 - 開發者的備註和碎碎念")

        # 移除帮助按钮
        dev_dialog.setWindowFlags(
            dev_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        # 调用函数设置窗口图标
        set_window_icon(self, 'icon.ico')
        dev_dialog.setFixedSize(1200, 900)  # 增大窗口尺寸

        # 主垂直布局
        main_layout = QVBoxLayout(dev_dialog)

        # 开发者标题
        title_label = QLabel("開發者備註")
        title_label.setFont(QFont("康熙字典體", 20))
        title_label.setStyleSheet("""
                    color: #8B1A1A;
                    padding: 5px;
                    text-align: center;
                """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #8B1A1A; height: 2px;")
        main_layout.addWidget(separator)

        # 创建QTextEdit作为开发者信息区域
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)  # 禁止用户编辑内容
        text_edit.setFont(QFont("Aa古典刻本宋", 14))
        text_edit.setStyleSheet("""
                    QTextEdit {
                        background-color: #fcfbf8;
                        border: 1px solid #8B1A1A;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 15px;
                    }
                """)

        # 设置HTML格式的占位内容
        html_content = """
                <h3 style="color: #8B1A1A; font-family: '康熙字典體';">說 明</h3>
                <p style="font-family: 'IpaP'; font-size: 14pt;">
                    此為開發者記錄代碼優化和注意事項的面板。<br>
                </p>

                <h3 style="color: #8B1A1A; font-family: '康熙字典體';">注意事項</h3>
                <ul style="font-family: 'IpaP'; font-size: 15pt;">
                    <li>2025年第一屆“人工智能与音韻學”學術研討會·優秀項目！<br></li>
                    <li>bs4庫（以及任何与BeautifulSoup相關庫）無法被pyinstaller打包！勿調用。<br></li>
                    <li>進行任何沒有把握的修改時，一定先備份原版代碼！<br></li>
                </ul>

                <h3 style="color: #8B1A1A; font-family: '康熙字典體';">代碼優化</h3>
                <p style="font-family: 'IpaP'; font-size: 15pt;">
                    <li>v1.4.4</li>
                        ·[聲符散佈]窗口第一次打開時，从數據庫查詢數據，後續再打開就从緩存里讀數據，速度更快，不用重複加載；<br>
                        ·各種功能窗口終於不會被重複打開了；<br>
                        ·在打包命令的“--windowed”前面插入“-i icon.ico”，就可以讓桌面圖標正確顯示“賢”字標，而非PyInstaller蟒蛇標；<br>
	                    ·數據庫：修改Database的表名：ancienttesttable2 → ancienttable1，加入“廣韻字表”“經典釋文玉篇廣韻反切對照表”（數據來自Poem，郭宇軒整理）。<br>
                    <li>v1.4.2</li>
	                    ·查字：修復控制台結果報錯問題。<br>
                    <li>v1.4.0</li>
	                    ·新圖標測試（1.4.2已合入）。<br>
                    <li>v1.3.7</li>
	                    ·代碼優化：刪除冗餘庫。<br>
                    <li>v1.2.0</li>
	                    ·中古音韻部-韻圖顯示：優化了歸字填入列表時的判斷代碼。<br>
                    <li>v1.1.7</li>
                        ·代碼：優化了窗口圖標的調用方法。<br>
                </p>
                <!-- 居中显示的版权信息 -->
                <div style="color: #592222; text-align: center; margin: 20px 0;">
                    <p style="font-family: '康熙字典體'; font-size: 15pt; margin: 0;">
                        ————版權所有 © 2025 上海師範大學數字人文中心————
                    </p>
                """
        text_edit.setHtml(html_content)
        main_layout.addWidget(text_edit, 1)  # 添加伸缩因子使文本区域占据剩余空间

        # 添加退出按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 20, 20)  # 右下边距

        # 退出开发者窗口按钮
        exit_button = QPushButton("隱藏Dev窗口")
        exit_button.setFont(QFont("康熙字典體", 14))
        exit_button.setStyleSheet("""
                    QPushButton {
                        background-color: #8B1A1A;
                        color: white;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: #a83232;
                        font-weight: bold;
                    }
                """)
        exit_button.setCursor(Qt.PointingHandCursor)
        exit_button.clicked.connect(dev_dialog.accept)

        # 将按钮添加到布局并右对齐
        button_layout.addStretch()  # 添加伸缩空间使按钮靠右
        button_layout.addWidget(exit_button)

        main_layout.addWidget(button_container)

        dev_dialog.exec_()


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
