import os
import sys
import re
import threading
import time
from collections import defaultdict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QLabel, QPushButton,
                             QGridLayout, QHBoxLayout, QMessageBox,
                             QLineEdit, QFrame, QSizePolicy, QScrollArea, QTableWidgetItem, QTableWidget, QHeaderView)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
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


# 主页面___________________________________________________________________
class MainWindow(QMainWindow):
    def open_search_chara_window(self):
        print("打开查字窗口")
        self.search_window = SearchCharaWindow()
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

    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小

        self.search_window = None
        self.setWindowTitle("古音查詢 - 首頁")
        self.setGeometry(100, 100, 1700, 1000)
        self.setMinimumSize(1600, 900)  # 设置固定窗口大小，禁止调整尺寸
        #self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)  # 禁止最大化按钮

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))


        # 创建主部件
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        # 使用网格布局
        layout = QGridLayout()
        main_widget.setLayout(layout)

        # 调整整个布局的边距（根据需要调整）
        layout.setContentsMargins(50, 20, 50, 20)

        # 在按钮上方添加弹性空间，使按钮向下移动
        layout.setRowStretch(0, 1)  # 在第一行（按钮上方）设置弹性

        # 创建标题标签
        query_label = QLabel("古 音 查 詢")
        query_label.setFont(QFont("康熙字典體", 64))
        query_label.setStyleSheet(
            """
                QLabel {
                        color: #8B2500;
                        border: 1px solid #57330C; 
                        border-radius: 15px;       
                        padding: 16px;              
                        }
            """)
        query_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(query_label, 0, 0, 1, 5, alignment=Qt.AlignCenter)

        # 按钮文本、样式、颜色和命令
        buttons_texts = ["查字", "查上古音·声母", "查中古音·声母", "查上古音·韵部", "查中古音·韵部"]
        button_fonts = [QFont("Aa古典刻本宋", 18) for _ in buttons_texts]
        button_colors = ["#CA6503", "#3C0D00", "#3C0D00", "#8E4A37", "#8E4A37"]
        button_commands = [self.open_search_chara_window,
                           self.open_shanggusheng_window,
                           self.open_zhonggusheng_window,
                           self.open_shangguyun_window,
                           self.open_zhongguyun_window]

        # 创建按钮并添加到布局
        for i, (text, font, color, command) in enumerate(zip(buttons_texts, button_fonts, button_colors, button_commands)):
            button = QPushButton(text)
            button.setFont(font)
            button.setStyleSheet(f"color: {color}; padding: 20px 5px;")
            # 为每个按钮设置点击事件
            if text == "查字":
                button.clicked.connect(self.open_search_chara_window)  # 点击“查字”按钮时打开窗口
            elif text == "查上古音·声母":
                button.clicked.connect(self.open_shanggusheng_window)
            elif text == "查中古音·声母":
                button.clicked.connect(self.open_zhonggusheng_window)
            elif text == "查上古音·韵部":
                button.clicked.connect(self.open_shangguyun_window)
            elif text =="查中古音·韵部":
                button.clicked.connect(self.open_zhongguyun_window)
            layout.addWidget(button, 1, i)

        # 设置列的伸展比例
        for i in range(len(buttons_texts)):
            layout.setColumnStretch(i, 1)
        # 在按钮下方添加弹性空间，使按钮向上移动
        layout.setRowStretch(2, 1)  # 在第三行（按钮下方）设置弹性

        # 创建更新日志按钮，并设置其外观类似超链接
        log_button = QPushButton("更新日志")
        log_button.setStyleSheet("""
               QPushButton {
                   color: #A0522D;  
                   background-color: transparent;  
                   border: none;  
                   text-decoration: underline;  
                   padding: 5px;
               }
               QPushButton:hover {
                   color: #551A8B;  
               }
           """)
        log_button.setFont(QFont("Aa古典刻本宋", 12))  # 设置字体样式和大小
        log_button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手形光标
        # 按钮点击事件绑定：当点击“更新日志”按钮时，打开更新日志窗口
        log_button.clicked.connect(self.open_update_log_window)
        # 将更新日志按钮添加到布局的底部
        layout.addWidget(log_button, 3, 0, 1, 5, alignment=Qt.AlignCenter)


#查中古韻母窗口——————————————————————————————————————————————————————————————————————————————
class ZhongguyunWindow(QWidget):
    zhongguyun_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查中古音·韻母")
        self.setGeometry(200, 100, 1900, 1300)
        self.setMinimumSize(1400, 1100)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

        self.initUI()

        # 连接信号到表格更新的槽函数
        self.zhongguyun_loaded_signal.connect(self.update_table)

    def initUI(self):
        # 创建主布局
        self.main_layout = QHBoxLayout(self)

        global zhongguyunchar_select

        # 1. L半部分 - 放置按钮
        button_frame = QFrame(self)
        button_frame.setFixedWidth(600)
        button_layout = QGridLayout(button_frame)

        # 设置按钮之间的间距
        button_layout.setHorizontalSpacing(20)  # 设置按钮左右之间的间距
        button_layout.setVerticalSpacing(20)  # 设置按钮上下之间的间距

        # 字符列表
        zhongguyunchars = ["東", "屋", "冬", "沃", "鍾", "燭", "江", "覺", "支", "脂",
                        "之", "微", "魚", "虞", "模", "齊", "祭", "泰",
                        "佳", "皆", "夬", "灰", "咍", "廢", "真", "質", "臻", "櫛",
                        "文", "物", "殷", "迄", "元", "月", "魂", "沒", "痕", "寒", "曷", "删", "黠", "山", "鎋",
                        "先", "屑", "仙", "薛", "蕭", "宵", "肴", "豪", "歌", "麻",
                        "陽", "藥", "唐", "鐸", "庚", "陌", "耕", "麥", "清", "昔", "青", "錫", "蒸", "職", "登", "德",
                        "尤", "侯", "幽", "侵", "緝", "覃", "合", "談", "盍", "鹽", "葉", "添", "帖",
                        "咸", "洽", "銜", "狎", "嚴", "業", "凡", "乏", "麧"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for zhongguyunchar in zhongguyunchars:
            button = QPushButton(zhongguyunchar, self)
            button.setFont(QFont("康熙字典體", 19))
            # 设置按钮为方形
            button.setFixedSize(70, 70)  # 宽度和高度相同，方形按钮
            # 设置按钮文字颜色
            button.setStyleSheet("color: #540A03;")  # 改变文字颜色

            button.clicked.connect(self.create_click_handler(zhongguyunchar))  # 正确绑定点击事件

            # 将按钮添加到布局
            button_layout.addWidget(button, row, column)
            # 列数加一
            column += 1
            if column == 7:
                row += 1
                column = 0  # 新行从第 0 列开始

        # 将按钮布局放入主布局
        self.main_layout.addWidget(button_frame)

        # 2. R半部分 __________________
        # 创建输入框和标签的布局
        input_layout = QVBoxLayout()
        self.main_layout.addLayout(input_layout)

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

    def create_click_handler(self, zhongguyunchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_zhongguyun_click(zhongguyunchar)

    def on_zhongguyun_click(self, zhongguyunchar):
        print("点击的上古韵母：", zhongguyunchar)
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
                        SELECT 字頭, 上古韻
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
        header1 = QLabel("來自上古音韻部")
        header1.setFont(QFont("康熙字典體", 20))
        header1.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該中古韻部的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
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
            zhongguyun_label.setStyleSheet("border: 1px solid brown; color: #CD3700; background-color: #EEE5DE;")
            zhongguyun_label.setFont(QFont("康熙字典體", 26))
            zhongguyun_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(zhongguyun_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)


#查上古韻母窗口——————————————————————————————————————————————————————————————————————————————
class ShangguyunWindow(QWidget):
    shangguyun_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查上古音·韻母")
        self.setGeometry(200, 100, 1900, 1300)
        self.setMinimumSize(1400, 1100)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

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
            button.setFont(QFont("康熙字典體", 18))
            # 设置按钮为方形
            button.setFixedSize(80, 80)  # 宽度和高度相同，方形按钮
            # 设置按钮文字颜色
            button.setStyleSheet("color: #540A03;")  # 改变文字颜色

            button.clicked.connect(self.create_click_handler(shangguyunchar))  # 正确绑定点击事件

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
        # 创建输入框和标签的布局
        input_layout = QVBoxLayout()
        self.main_layout.addLayout(input_layout)

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

    def create_click_handler(self, shangguyunchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_shangguyun_click(shangguyunchar)

    def on_shangguyun_click(self, shangguyunchar):
        print("点击的上古韵母：", shangguyunchar)
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
        header1.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("該上古韻部的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
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
            shangguyun_label.setStyleSheet("border: 1px solid brown; color: #CD3700; background-color: #EEE5DE;")
            shangguyun_label.setFont(QFont("康熙字典體", 26))
            shangguyun_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(shangguyun_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)

#查中古聲母窗口——————————————————————————————————————————————————————————————————————————————
class ZhonggushengWindow(QWidget):
    # 定义一个信号，传递加载的数据
    zhonggusheng_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查中古音·聲母")
        self.setGeometry(200, 100, 1900, 1200)
        self.setMinimumSize(1400, 900)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

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

        # 字符列表
        zhonggushengchars = ["幫", "滂", "並", "明", "端", "透", "定", "泥",
                             "精", "清", "從", "心", "邪", "莊", "初", "崇", "生",
                             "章", "昌", "船", "書", "禪", "知", "徹", "澄", "娘",
                             "見", "溪", "群", "疑", "影", "以", "曉", "匣",
                             "來", "日"]
        row = 0  # 初始行数
        column = 0  # 初始列数

        for zhonggushengchar in zhonggushengchars:
            button = QPushButton(zhonggushengchar, self)
            button.setFont(QFont("康熙字典體", 20))
            # 设置按钮为方形
            button.setFixedSize(80, 80)  # 宽度和高度相同，方形按钮
            # 设置按钮文字颜色
            button.setStyleSheet("color: #540A03;")  # 改变文字颜色

            button.clicked.connect(self.create_click_handler(zhonggushengchar))  # 正确绑定点击事件

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
        # 创建输入框和标签的布局
        input_layout = QVBoxLayout()
        self.main_layout.addLayout(input_layout)

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

    def create_click_handler(self, zhonggushengchar):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_zhonggusheng_click(zhonggushengchar)

    def on_zhonggusheng_click(self, zhonggushengchar):
        print("点击的中古声母：", zhonggushengchar)
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
        header1.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)

        header2 = QLabel("中古音的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown; color: brown; background-color: #EEE9E9;")
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
            zhonggusheng_label.setStyleSheet("border: 1px solid brown; color: #CD3700; background-color: #EEE5DE;")
            zhonggusheng_label.setFont(QFont("IpaP", 26))
            zhonggusheng_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(zhonggusheng_label, row_num + 1, 1)

            # 字头列
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown;")
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)
            zitou_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            zitou_label.setAlignment(Qt.AlignCenter)

            # 将字头列添加到表格
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)

#查上古声母窗口_______________________________________________________________________________
class ShanggushengWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查上古音·聲母")

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

        self.initUI()

    def initUI(self):

        # 设置主布局为垂直布局
        self.layout = QVBoxLayout()
        # 设置窗口起始位置，例如 (x, y) = (100, 100)
        self.move(1, 1)
        # 1. 上半部分 - 放置音标按钮
        button_frame = QFrame(self)
        button_frame.setFixedHeight(800)  # 固定高度
        #button_frame.setFixedWidth(1500)
        button_layout = QGridLayout(button_frame)


        # 字符列表shanggushengipas
        shanggushengipas = ["b", "bɡˡ", "bɡʳ", "bkʳ", "bˡ", "bl", "b‧l", "bˡʲ",
             "bʳ", "b‧r", "br", "d", "dʲ", "ɢ", "ɡ", "ɢbˡ", "ɡbˡ",
             "ɡbʳ", "ɢʲ", "ɡʲ", "ɢl", "ɡl", "ɡˡ", "ɡ‧l", "ɢˡʲ", "ɡˡʲ",
             "ɢmˡ", "ɢʳ", "ɡr", "ɡʳ", "ɡ‧r", "ɢʷ", "ɡʷ", "ɢʷʲ","ɢʷˡ", "ɡʷˡ",
             "ɢʷʳ", "ɡʷʳ","k", "kʰ","kʰʲ", "kʰl","kʰˡ", "kʰˡʲ", "kʰʳ","kʰr",
             "kʰʷ","kʰʷʲ", "kʰʷʳ","kʲ", "kl","kˡ", "kˡʲ","kpʰ", "klʲ","kpʳ",
                            "kʳ", "kr", "k‧r", "kʷ", "kt", "kʷˡ", "kʷʳ", "kʷʲ", "l", "l̥", "l̥ʰ", "lʲ", "l̥ʲ", "m",
             "m̥","mb", "mbˡ","mblʲ", "mbʳ","mɡl", "mɡˡ", "mɡr","mɡʳ", "mɡlʲ","mɡʷ", "mɡʷˡ","mɡʷʳ", "mɡʷr",
             "m̥ʰ","m̥ʰʳ", "m̥ʰˡ","m̥ʰʲ", "m̥ʰˡʲ","mkʳ", "mˡ","ml", "m̥l","mlʲ", "mˡ̥ʲ",
             "mʳ", "mr", "m‧r","mʳ̥ʰ", "m̥ʳ","n", "n̥","nd", "n̥ʰ",
             "nʲ","n̥ʲ", "ŋ","ŋ̊", "ŋɡ","ŋɡˡ", "ŋɡl", "ŋɡʲe","ŋɡʳ", "ŋɡʷ","ŋɡʷʲ", "ŋɡʷʳ","ŋ̊ʰ", "ŋ̊ʰˡʲ",
             "ŋ̊ʰʷ","ŋ̊ʰʳ", "ŋ̊ʰʷʳ","ŋˡ", "ŋʲ","ŋ̊ʲ", "ŋpʳ","ŋʳ", "ŋr","ŋʷ", "ŋ̊ʳ","ŋʷʳ", "ŋʷʲ",
             "p","pʰ", "pɡʳ","pʰl", "pʰˡ","pʰˡʲ", "pʰʳ",
             "pʰr","pʲ", "pk","pkʰ", "pkʰʳ","pkʰˡ", "pkʳ", "pkˡ","pˡ", "pl","p‧l̥", "p‧l̥ʰ","pˡʲ", "pqʰʳ",
             "pqʰˡ","pqʰʷ", "pʳ","q", "qʰ","qʰl", "qʰˡ","qʰʲ", "qʰˡʲ","qʰʳ", "qʰʷ","qʰʷʲ", "qʰʷʳ", "qʰʷr",
             "qˡ", "qn","qpʰ", "qpʰʳ","qpʰr", "qpʰˡ","qpˡ", "qpʳ","qʳ", "qʷ","qʷʳ",
             "qʷʲ","r", "r̥","rd", "r̥ʲ","rn", "rt", "rtʰ","s", "sb","sbˡ", "sbˡʲ","sbr",
                            "sd", "sɡ", "sɢˡ", "sɢ", "sɡl", "sɡˡ", "sɢˡʲ", "sɡr", "sɢʷ", "sɡʷr", "sʰ", "sʰr", "sʰʳ", "sk", "skʰ",
                            "skʰl", "skʰˡ", "skʰr", "skʰʳ", "skʰʷ", "skˡ", "skl", "skʳ", "skr", "skʷ", "skʷˡ", "skʷr", "skʷʳ", "sˡ",
                            "sl̥", "sm", "smˡ", "sn", "sn̥", "sŋ", "s‧ŋ", "sŋ̊", "sŋʳ", "sŋ̊r", "sp", "spʰ", "spʰr", "spˡ",
                            "spʳ", "sqʰ", "sqʰʷ", "sqʳ", "sqʷʳ", "sʳ", "sr", "st", "t", "tʰ", "tʰʲ", "tʲ", "z", "zr", "zˡ"]
        for i, shanggushengipa in enumerate(shanggushengipas):
            button = QPushButton(shanggushengipa, self)
            button.setFont(QFont("IpaP", 16))
            button.setFixedWidth(90)
            button.setMinimumHeight(60)
            button.clicked.connect(self.create_click_handler(shanggushengipa))  # 正确绑定点击事件
            button_layout.addWidget(button, i // 20, i % 20)  # 每行放置20个按钮

        # 将按钮布局放入主布局
        self.layout.addWidget(button_frame)

        # 2. 下半部分 - 分左右两个部分放置查询结果___________________

        bottom_frame = QFrame(self)
        bottom_frame.setFixedHeight(660)  # 固定底部区域高度
        bottom_layout = QHBoxLayout(bottom_frame)

        # 左侧布局 - 分为上下两个部分__________________________________________________
        left_frame = QFrame(bottom_frame)
        left_layout = QVBoxLayout(left_frame)

        # 左上半部分 - leftUp_frame
        leftUp_frame = QFrame(left_frame)
        leftUp_frame.setFixedHeight(100)  # 固定高度
        leftUp_layout = QVBoxLayout(leftUp_frame)
        result_label_up = QLabel("屬於該上古聲母的字")
        result_label_up.setFont(QFont("康熙字典體", 22))
        result_label_up.setStyleSheet("color: brown;")  # 设置字体颜色为红色
        result_label_up.setAlignment(Qt.AlignCenter)
        leftUp_layout.addWidget(result_label_up)

        # 左下半部分 - 可滚动区域
        scroll_area = QScrollArea(left_frame)
        scroll_area.setWidgetResizable(True)  # 滚动区域自动适应内容大小
        # 设置scroll_area的大小策略，保持宽度不超过父容器
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_area.setFixedHeight(510)  # 固定高度
        # leftDown_frame 是实际显示内容的部分
        leftDown_frame = QFrame()
        leftDown_layout = QVBoxLayout(leftDown_frame)

        # 设置滚动区域中的内容
        self.result_label_1 = QLabel()
        self.result_label_1.setFont(QFont("宋体", 22))
        self.result_label_1.setAlignment(Qt.AlignCenter)
        self.result_label_1.setWordWrap(True)  # 自动换行，防止内容超出边界

        # 为leftDown_frame设置边框
        leftDown_frame.setStyleSheet("border: 1px solid brown;")
        leftDown_layout.addWidget(self.result_label_1)

        # 将 leftDown_frame 设置为 scroll_area 的内容
        scroll_area.setWidget(leftDown_frame)

        # 将上半部分和滚动区域添加到左侧布局
        left_layout.addWidget(leftUp_frame)
        left_layout.addWidget(scroll_area)
        # 设置左侧frame的大小策略，确保其宽度和右侧frame保持一致
        left_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 右侧布局__已移除，不再需要

        # 将frame添加到底部布局
        bottom_layout.addWidget(left_frame)

        # 将底部布局添加到主布局
        self.layout.addWidget(bottom_frame)#______________________

        # 3. 底部 - 新布局（下部分），水平居中放一个按钮，布局高度为80
        bottom_button_frame = QFrame(self)
        bottom_button_frame.setFixedHeight(100)  # 固定高度
        bottom_button_layout = QHBoxLayout(bottom_button_frame)

        # 添加按钮并居R
        bottom_button = QPushButton("用表格显示结果", self)
        bottom_button.setFont(QFont("Aa古典刻本宋", 14))
        bottom_button.clicked.connect(self.on_sheetbutton_click)  # 绑定点击事件
        bottom_button_layout.addWidget(bottom_button)
        bottom_button_layout.setAlignment(Qt.AlignRight)  # 水平居R

        # 将新布局添加到主布局
        self.layout.addWidget(bottom_button_frame)

        # 设置主窗口的布局___________________________________________
        self.setLayout(self.layout)


    def create_click_handler(self, shanggushengipa):
        # 返回lambda以正确处理点击事件
        return lambda: self.on_shanggusheng_click(shanggushengipa)

    def on_shanggusheng_click(self, shanggushengipa):
        print("你点击了: ", shanggushengipa)
        global shanggushengipa_select
        shanggushengipa_select = shanggushengipa
        # 显示"加载中..."直到查询结果加载完
        self.result_label_1.setText("加载中……")

        # 启动后台线程加载数据
        threading.Thread(target=self.load_data, args=(shanggushengipa,)).start()

    def load_data(self, shanggushengipa):
        # 连接数据库并查询
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 查询所有该声母的字及对应的上古声
            sql = """
                SELECT DISTINCT 字頭
                FROM ancienttesttable1 
                WHERE 上古聲 = ?
            """
            cursor.execute(sql, (shanggushengipa,))
            result = cursor.fetchall()

            if result:
                # 提取字头并显示
                字頭_list = [item['字頭'] for item in result]
                self.result_label_1.setText("  ".join(字頭_list))  # 用空格分隔字头
            else:
                self.result_label_1.setText("没有找到匹配结果。")

        except Exception as e:
            self.show_error_message(f"查询出错: {e}")
        finally:
            if connection:
                connection.close()

    def show_error_message(self, message):
        QMessageBox.critical(self, "数据库错误", message)
    def on_sheetbutton_click(self):

        self.sub_window=Subsheet_shanggusheng()
        self.sub_window.show()  # 显示子窗口

#定义上古聲表格视图的子窗口——————————————————————————————————————————————————
class Subsheet_shanggusheng(QWidget):
    update_table_signal = pyqtSignal(list)  # 定义信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查上古音·聲母 - 表格顯示")
        self.setGeometry(100, 100, 1700, 1200)  # 设置窗口大小
        self.setMinimumSize(1300,1000)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

        # 创建主布局
        layout = QVBoxLayout()

        # 创建输入框和标签的布局
        input_layout = QHBoxLayout()
        layout.addLayout(input_layout)
        global shanggushengipa_select

        # 标签
        label = QLabel("刚刚查询的上古音声母: ")
        label.setFont(QFont("Aa古典刻本宋", 26))
        label.setAlignment(Qt.AlignCenter)  # 将标签居中
        label.setFixedHeight(80)
        label.setContentsMargins(300, 40, 0, 40)  # 设置 label 和窗口左边的边距
        label2 = QLabel(shanggushengipa_select)
        label2.setFont(QFont("IpaP", 26))
        label2.setFixedHeight(80)
        input_layout.addWidget(label)
        input_layout.addWidget(label2)


        # 创建表格布局
        self.table_layout = QGridLayout()
        layout.addSpacing(2)  # 上方空白
        # 创建 QScrollArea 并嵌入表格布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许自动调整子窗口大小
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.table_layout)  # 将表格布局设为 QScrollArea 的子窗口
        scroll_area.setWidget(scroll_widget)

        # 将 QScrollArea 添加到主布局中
        layout.addWidget(scroll_area)

        # 设置主窗口布局
        self.setLayout(layout)

        # 连接信号和槽
        self.update_table_signal.connect(self.update_table)


        # 开启线程查询数据库
        self.load_table_data()

    def load_table_data(self):
        """创建一个新线程去查询数据库，以避免阻塞主线程"""
        print("Loading table data...")
        threading.Thread(target=self.query_database).start()

    def query_database(self):
        """查询数据库以获取匹配上古声IPA的结果"""
        connection = None
        try:
            connection = create_db_connection()
            cursor = connection.cursor()

            # 查询所有该声母的字头和中古声
            sql = """
                SELECT 字頭, 中古聲 
                FROM ancienttesttable1
                WHERE 上古聲 = ?
            """
            cursor.execute(sql, (shanggushengipa_select,))
            result = cursor.fetchall()

            # 将相同的“中古声”进行分组
            grouped_data = defaultdict(list)
            for row in result:
                grouped_data[row['中古聲']].append(row['字頭'])

            # 将 defaultdict 转换为标准的 list 类型，例如字典的列表
            grouped_data_list = [{"中古聲": key, "字頭": value} for key, value in grouped_data.items()]

            # 查询完成后，通过信号传递数据回主线程更新表格
            self.update_table_signal.emit(grouped_data_list)

        except Exception as e:
            print(f"查询数据库时出错: {e}")

        finally:
            if connection:
                connection.close()  # 确保数据库连接被关闭


    def update_table(self, data):
        """在主线程中更新UI，填充表格数据"""

        # 清空表格布局的现有内容
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()


        # 表头行
        header1 = QLabel("對應中古音聲母")
        header1.setFont(QFont("康熙字典體", 20))
        header1.setStyleSheet("border: 2px solid brown;"
                              "color: brown; "
                              "background-color: #EEE9E9;")
        header1.setAlignment(Qt.AlignCenter)
        header1.setFixedHeight(80)  # 设置表头的固定高度

        header2 = QLabel("該上古音聲母的歸屬字")
        header2.setFont(QFont("康熙字典體", 20))
        header2.setStyleSheet("border: 2px solid brown;"
                              "color: brown;"
                              "background-color: #EEE9E9")
        header2.setAlignment(Qt.AlignCenter)
        header2.setFixedHeight(80)  # 设置表头的固定高度

        # 将表头添加到表格布局
        self.table_layout.addWidget(header1, 0, 1)
        self.table_layout.addWidget(header2, 0, 0)
        # 去掉布局的间隙
        self.table_layout.setHorizontalSpacing(0)  # 去掉水平间隙
        self.table_layout.setVerticalSpacing(0)  # 去掉垂直间隙
        # 去掉布局的外边距
        self.table_layout.setContentsMargins(0, 0, 0, 0)  # 上下左右的外边距都为0
        # 设置列宽比例
        self.table_layout.setColumnStretch(0, 5)  # 第一列的宽度比例为5
        self.table_layout.setColumnStretch(1, 1)  # 第二列的宽度比例为1

        # 填充新数据到表格中
        for row_num, row_data in enumerate(data):
            # 添加中古声列
            zhonggusheng_label = QLabel(str(row_data["中古聲"]))
            zhonggusheng_label.setStyleSheet("border: 1px solid brown; "
                                             "color: #CD3700; "
                                             "background-color: #EEE5DE;")  # 增加边框
            zhonggusheng_label.setFont(QFont("康熙字典體", 28))
            zhonggusheng_label.setAlignment(Qt.AlignCenter)  # 水平垂直居中
            self.table_layout.addWidget(zhonggusheng_label, row_num + 1, 1)

            # 添加字头列，将相同中古声的字头合并为一个字符串
            zitou_str = "  ".join(row_data["字頭"])
            zitou_label = QLabel(zitou_str)
            zitou_label.setStyleSheet("border: 1px solid brown;")  # 增加边框
            zitou_label.setFont(QFont("宋体", 20))
            zitou_label.setWordWrap(True)  # 允许自动换行
            self.table_layout.addWidget(zitou_label, row_num + 1, 0)

# 查字窗口——————————————————————————————————————————————————————————————————————————————————————
class SearchCharaWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("古音查詢 - 查字")
        self.setGeometry(200, 200, 1500, 700)
        self.setMinimumSize(1400, 700)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

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

        # 创建按钮布局
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # 创建查询按钮
        search_chara_button = QPushButton("查询(暂时只支持繁体)")
        search_chara_button.setFont(QFont("Aa古典刻本宋", 18))
        search_chara_button.setFixedWidth(600)
        search_chara_button.setStyleSheet(f"color: #B03A2E; padding: 20px 5px;")
        search_chara_button.clicked.connect(self.check_input)
        button_layout.addWidget(search_chara_button)

        # 清空按钮
        clear_button = QPushButton("清空内容")
        clear_button.setFont(QFont("Aa古典刻本宋", 18))
        clear_button.setStyleSheet(f"color: #784212; padding: 20px 5px;")
        clear_button.setFixedWidth(300)
        clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_button)

        # 创建表格布局
        self.table_layout = QGridLayout()
        layout.addSpacing(50)  # 上方空白
        layout.addLayout(self.table_layout)
        layout.addSpacing(50)  # 下方空白

    # 清空输入框和表格内容
    def clear_all(self):
        self.search_chara_entry.clear()
        for i in reversed(range(self.table_layout.count())):
            widget = self.table_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

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

        headers = result[0].keys()
        self.table_layout.setSpacing(0)  # 设置布局的间距为 0，去除单元格之间的间隙

        # 创建表头
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("康熙字典體", 20))
            header_label.setStyleSheet("border: 1px solid #6C1002; background-color: #FBF0F0; color: #6C1002;")
            header_label.setAlignment(Qt.AlignCenter)
            self.table_layout.addWidget(header_label, 0, col)

            # 创建表格内容
        for row_num, result in enumerate(result):
            for col_num, key in enumerate(headers):
                value_label = QLabel(str(result[key]))
                value_label.setFont(QFont("宋体", 20))
                value_label.setStyleSheet("border: 1px solid #8A1A00; background-color: #FFF9F9; color: #3C0D00;")
                value_label.setAlignment(Qt.AlignCenter)
                self.table_layout.addWidget(value_label, row_num + 1, col_num)  # 使用 row_num + 1 使其显示在第二行及以后

#更新日誌窗口
class UpdateLogWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("古音查詢 - 更新日誌")
        self.setGeometry(400, 300, 1300, 900)

        # 检查程序是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # PyInstaller解压后的临时目录
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 使用相对路径查找图标文件
        icon_path = os.path.join(base_dir, 'icon.ico')

        # 设置窗口图标
        self.setWindowIcon(QIcon(icon_path))

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
            <ul style="font-family: '宋体'; font-size: 35px;">
                <li>v1.0.0 - 初始版本打包發佈</li>
                <li>v1.0.1 - 修復了不同分辨率屏幕的UI適配問題</li>
                <li>v1.0.2 <br>  
                                ·更新數據庫條目：修正中古韻部【咸】誤作【鹹】的錯誤；<br>
                                ·中古音韻部查詢按鈕：基於切韻韻系、廣韻韻目重新排序；<br>
                                ·增加【更新日誌】查看功能。</li>
            </ul>
        """)        #這屬於html代碼↑
        font = QFont("Aa古典刻本宋", 20)  # 设置字体和字号
        log_label.setFont(font)
        log_label.setAlignment(Qt.AlignTop)
        log_label.setWordWrap(True)  # 允许自动换行
        layout.addWidget(log_label)

        # 添加一个关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

#————————————————————————————————————————————————————————————————————————————————————————————
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
