import sys
import os
import shutil
import ctypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QMessageBox)
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import Qt

# 字体文件夹路径
def get_fonts_dir():
    """获取字体目录的正确路径（支持打包后访问）"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    font_dir = os.path.join(base_path, "fonts")
    if not os.path.exists(font_dir):
        os.makedirs(font_dir, exist_ok=True)
    return font_dir


FONTS_DIR = get_fonts_dir()

class FontInstallerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("字体安装程序")
        # ▼▼▼ 提前初始化字体列表 ▼▼▼
        self.font_list = [
            "康熙字典體.ttf",
            "Aa古典刻本宋.ttf",
            "IpaP.ttf"
        ]
        self.verify_resources()  # 在初始化UI前检查资源
        self.setMinimumSize(500, 400)
        self.setFixedSize(500, 400)  # 固定窗口大小，不允许调整
        self.initUI()

    # ▼▼▼ 新增验证方法 ▼▼▼
    def verify_resources(self):
        """验证所有字体资源是否存在"""
        missing = []
        for font in self.font_list:
            path = os.path.join(FONTS_DIR, font)
            if not os.path.exists(path):
                missing.append(font)

        if missing:
            QMessageBox.critical(
                self, "资源缺失",
                f"以下字体文件未找到：\n" + "\n".join(missing) +
                f"\n\n请确保程序包含fonts目录且包含上述文件"
            )
            sys.exit(1)

    def initUI(self):
        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 标题和检查按钮放在同一行
        title_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("依赖字体安装状态")
        title_font = QFont("等线", 16)  # 使用等线字体
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        
        # 添加检查按钮
        check_button = QPushButton("检查")
        check_button_font = QFont("等线", 12)
        check_button.setFont(check_button_font)
        check_button.setFixedWidth(80)
        check_button.setMinimumHeight(35)
        check_button.clicked.connect(self.update_font_status)
        title_layout.addWidget(check_button)
        
        # 将标题布局添加到主布局
        main_layout.addLayout(title_layout)

        
        # 创建字体状态显示及安装按钮
        self.font_widgets = {}
        button_width = 150  # 设置统一的按钮宽度
        
        for font_name in self.font_list:
            font_layout = QHBoxLayout()
            
            # 字体名称标签
            font_label = QLabel(font_name)
            label_font = QFont("等线", 12)  # 使用等线字体
            font_label.setFont(label_font)
            font_layout.addWidget(font_label)
            
            # 状态标签
            status_label = QLabel()
            status_font = QFont("等线", 14)  # 使用等线字体
            status_label.setFont(status_font)
            font_layout.addWidget(status_label)
            
            # 安装按钮
            install_button = QPushButton("安装该字体")
            button_font = QFont("等线", 12)  # 使用等线字体
            install_button.setFont(button_font)
            install_button.setMinimumHeight(40)  # 增加按钮高度
            install_button.setFixedWidth(button_width)  # 设置固定宽度使所有按钮等宽
            install_button.clicked.connect(lambda checked, name=font_name: self.install_font(name))
            font_layout.addWidget(install_button)
            
            # 保存引用以便更新状态
            self.font_widgets[font_name] = {
                "status_label": status_label,
                "install_button": install_button
            }
            
            # 添加到主布局并设置间距
            main_layout.addLayout(font_layout)
            main_layout.addSpacing(10)  # 添加行间距
        
        # 检查字体状态
        self.update_font_status()

    def update_font_status(self):
        """更新所有字体的安装状态"""
        installed_fonts = []
        not_installed_fonts = []

        # 为调试添加详细日志
        debug_info = "字体检测详细信息：\n\n"

        for font_name in self.font_list:
            # 获取字体安装状态和安装路径
            result = self.is_font_installed(font_name)
            is_installed = result["installed"]
            install_path = result["path"]

            # 添加调试信息
            debug_info += f"字体: {font_name}\n"
            debug_info += f"检测结果: {'已安装' if is_installed else '未安装'}\n"
            if is_installed:
                debug_info += f"安装路径: {install_path}\n"
            debug_info += "\n"

            widgets = self.font_widgets[font_name]

            if is_installed:
                widgets["status_label"].setText("✓")
                widgets["install_button"].setVisible(False)
                installed_fonts.append((font_name, install_path))
            else:
                widgets["status_label"].setText("")
                widgets["install_button"].setVisible(True)
                not_installed_fonts.append(font_name)

        # 构建消息内容
        message = "字体检查完成！\n\n"

        if installed_fonts:
            message += "已安装的字体：\n"
            for font, path in installed_fonts:
                message += f"• {font}：{path}\n"

        if not_installed_fonts:
            if installed_fonts:
                message += "\n"
            message += "未安装的字体：\n"
            for font in not_installed_fonts:
                message += f"• {font}\n"

        # 显示检查结果提示窗
        QMessageBox.information(self, "检查结果", message)

        # 如果检测到问题，显示调试信息
        if len(installed_fonts) < len(self.font_list):
            print(debug_info)  # 在控制台输出调试信息
    
    def is_font_installed(self, font_name):
        """检查字体是否已安装，返回安装状态和路径"""
        # 获取字体文件的纯名称（不含扩展名）
        font_base_name = os.path.splitext(font_name)[0]
        
        # 使用 PyQt 的 QFontDatabase 检查字体是否可用
        font_db = QFontDatabase()
        all_families = font_db.families()
        
        # 检查方法1: 通过QFontDatabase检测
        for family in all_families:
            # 宽松匹配 - 只要字体名包含在家族名中即可
            if font_base_name in family:
                return {"installed": True, "path": f"系统字体数据库中注册为: {family}"}
        
        # 检查方法2: 检查Windows字体目录
        windows_font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
        font_path = os.path.join(windows_font_dir, font_name)
        
        # 直接检查文件是否存在
        if os.path.exists(font_path):
            return {"installed": True, "path": font_path}
        
        # 检查方法3: 用宽松匹配在字体目录中查找
        for filename in os.listdir(windows_font_dir):
            if font_base_name.lower() in filename.lower():
                return {"installed": True, "path": os.path.join(windows_font_dir, filename)}
            
        # 检查方法4: 查找注册表
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                # 枚举所有注册的字体
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        # 宽松匹配 - 只要字体名是注册表值的子串
                        if font_base_name.lower() in name.lower():
                            # 如果注册表中的值是相对路径，需要补全完整路径
                            if not os.path.isabs(value):
                                value = os.path.join(windows_font_dir, value)
                            return {"installed": True, "path": value}
                        i += 1
                    except WindowsError:
                        break
        except Exception as e:
            # 打印错误以便调试
            print(f"检查注册表时出错: {str(e)}")
            
        # 检查方法5: 检查用户字体目录
        user_font_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Microsoft', 'Windows', 'Fonts')
        if os.path.exists(user_font_dir):
            user_font_path = os.path.join(user_font_dir, font_name)
            if os.path.exists(user_font_path):
                return {"installed": True, "path": user_font_path}
            
            # 宽松匹配
            for filename in os.listdir(user_font_dir):
                if font_base_name.lower() in filename.lower():
                    return {"installed": True, "path": os.path.join(user_font_dir, filename)}
                    
        # 如果所有方法都失败，则返回未安装
        return {"installed": False, "path": ""}
    
    def install_font(self, font_name):
        """安装指定的字体"""
        # ▼▼▼ 新增调试信息 ▼▼▼
        print(f"尝试访问字体目录：{FONTS_DIR}")
        print(f"字体列表：{os.listdir(FONTS_DIR)}")
        # ▲▲▲ 新增结束 ▲▲▲

        # 字体源文件路径
        font_src = os.path.join(FONTS_DIR, font_name)
        
        # 检查字体源文件是否存在
        if not os.path.exists(font_src):
            error_msg = (
                f"字体文件 {font_name} 未找到！\n"
                f"当前搜索路径：{font_src}\n"
                f"字体目录内容：{os.listdir(FONTS_DIR)}"
            )
            QMessageBox.critical(self, "路径错误", error_msg)
            return
            
        # Windows字体目录
        font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
        font_dest = os.path.join(font_dir, font_name)
        
        try:
            # 复制字体文件到Windows字体目录
            shutil.copy(font_src, font_dest)
            
            # 注册字体
            # 需要管理员权限
            FONT_ADDED = 0x10
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            flags = FONT_ADDED
            
            # 添加字体到注册表
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, f"{os.path.splitext(font_name)[0]} (TrueType)", 0, winreg.REG_SZ, font_name)
            
            # 通知Windows字体更改
            ctypes.windll.gdi32.AddFontResourceW(font_dest)
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            
            QMessageBox.information(self, "成功", f"字体 {font_name} 已成功安装！")
            
            # 更新状态
            self.update_font_status()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"安装字体时出错：\n{str(e)}\n\n可能需要以管理员权限运行此程序。")

if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    window = FontInstallerApp()
    window.show()
    sys.exit(app.exec_()) 