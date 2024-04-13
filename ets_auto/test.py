from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit
import sys
import os
import psutil
import glob
import eyed3
import shutil
from datetime import datetime
import traceback
import ffmpeg
import subprocess


class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowOpacity(0.85)
        QFontDatabase.addApplicationFont('Fonts/MiSans-Light.ttf')

        font_text = QFont('MiSans-Light', 14)
        font_btn = QFont('MiSans-Light', 14)

        self.textEdit = QTextEdit('使用方法：打开e听说之后点击开始并遵循提示即可，有概率出现错误，请及时复制报告反馈')
        self.textEdit.setFont(font_text)
        self.textEdit.setReadOnly(True)

        self.btn1 = QPushButton('开始', self)
        self.btn1.setFont(font_btn)
        self.btn2 = QPushButton('继续', self)
        self.btn2.setFont(font_btn)
        self.btn3 = QPushButton('恢复网络连接', self)
        self.btn3.setFont(font_btn)

        self.btn2.clicked.connect(self.on_continue)
        self.btn1.clicked.connect(self.on_start)
        self.btn3.clicked.connect(self.renew_network)

        vbox = QVBoxLayout()
        vbox.addWidget(self.textEdit)
        vbox.addWidget(self.btn1)
        vbox.addWidget(self.btn2)
        vbox.addWidget(self.btn3)

        self.setLayout(vbox)
        self.setWindowTitle('ETS_auto')
        self.setGeometry(300, 300, 300, 400)
        self.show()



    def check_ets_running(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'Ets.exe':
                return proc.exe()
        return None

    def on_start(self):
        current_text = self.textEdit.toPlainText()

        messages = {
            '暂未运行e听说，请运行后再试': '先打开e听说再来啊啊啊啊啊啊！',
            '先打开e听说再来啊啊啊啊啊啊！': '咋这么不听劝呢！别点了真的没用的！',
            '咋这么不听劝呢！别点了真的没用的！': '别试了，点我也没用',
            '别试了，点我也没用': '网络已恢复连接',
            '网络已恢复连接': '暂未运行e听说，请运行后再试'
        }

        ets_path = self.check_ets_running()
        if ets_path is None:
            self.textEdit.setText(messages.get(current_text, '暂未运行e听说，请运行后再试'))
            return

        appdata_path = os.getenv('APPDATA')
        ets_auto_path = os.path.join(appdata_path, 'ets_auto')
        os.makedirs(ets_auto_path, exist_ok=True)

        self.config_path = os.path.join(ets_auto_path, 'config.txt')
        with open(self.config_path, 'w') as f:
            f.write(f'Ets.exe path: {ets_path}\n')

            record_path = os.path.join(os.path.dirname(ets_path), 'userdata', 'record')
            f.write(f'Record path: {record_path}\n')

        appdata_path = os.getenv('APPDATA')
        self.base_path = os.path.join(appdata_path, '74656D705F74656D705F74656D705F74002')

        folders = [f for f in glob.glob(os.path.join(self.base_path, '*/')) if
                   os.path.basename(os.path.dirname(f)).isdigit()]
        self.latest_folder = max(folders, key=os.path.getmtime)

        with open(self.config_path, 'a') as f:
            f.write(f'Latest folder: {self.latest_folder}\n')

        self.textEdit.setText('即将关闭网络，请点击继续')

    def on_continue(self):
        try:
            appdata_path = os.getenv('APPDATA')
            ets_auto_path = os.path.join(appdata_path, 'ets_auto')

            # 获取当前的提示信息
            current_text = self.textEdit.toPlainText()

            if current_text == '请直到E听说出现提示"评分失败"时点击"继续"并重新评分':
                # 打开网络连接
                #os.system('ipconfig /renew')

                # 更新文本区域的内容
                self.textEdit.setText('一切完成，若有问题请带报告反馈！')

            if current_text == '请当结束录音时点击我':
                # 检测record_file中最新的wav文件是否与当前时间相差不超过1分钟
                wav_files = glob.glob(os.path.join(self.record_file, '*.wav'))
                latest_wav = max(wav_files, key=os.path.getmtime)
                if (datetime.now() - datetime.fromtimestamp(os.path.getmtime(latest_wav))).seconds > 60:
                    self.textEdit.setText('似乎出现了异常，请确定完成录音后再试，已为你恢复网络连接')
                    # 打开网络连接
                    #os.system('ipconfig /renew')
                    return

                # 记录最新的wav文件的名字并删除这个文件
                latest_wav_name = os.path.basename(latest_wav)
                os.remove(latest_wav)

                # 将保存在ets_auto文件夹中的wav文件移动到record_file文件夹，并重命名为刚刚记录的最新的wav文件的名字
                shutil.move(os.path.join(ets_auto_path, 'content.wav'),
                            os.path.join(self.record_file, latest_wav_name))

                # 更新文本区域的内容
                self.textEdit.setText('请直到E听说出现提示"评分失败"时点击"继续"并重新评分')

            elif current_text == '即将关闭网络，请点击继续':
                # 关闭网络连接（这需要管理员权限）
                #os.system('ipconfig /release')

                # 从配置文件中获取lastest_answer和record_file的位置
                with open(self.config_path, 'r') as f:
                    lines = f.readlines()
                    self.latest_folder = lines[-1].split(': ')[1].strip()
                    self.record_file = lines[-2].split(': ')[1].strip()

                # 找到content.mp3文件并转换为wav文件
                content_mp3 = os.path.join(self.latest_folder, 'content00010001', 'material', 'content.mp3')
                content_wav = os.path.join(ets_auto_path, 'content.wav')
                ffmpeg.input(content_mp3).output(content_wav, ar=16000, ac=1).overwrite_output().run()

                # 更新文本区域的内容
                self.textEdit.setText('请当结束录音时点击我')


            # 总有人喜欢都点一点>_<
            elif current_text == '暂未运行e听说，请运行后再试' or current_text == '先打开e听说再来啊啊啊啊啊啊！' or current_text == '咋这么不听劝呢！别点了真的没用的！':

                self.textEdit.setText('别试了，点我也没用')




        except Exception as e:
            # 如果出现错误，将错误信息和错误发生的行数输出到文本框
            tb = traceback.format_exc()
            self.textEdit.setText(str(e) + '\n' + str(tb))

    def renew_network(self):
        # 打开网络连接
        #os.system('ipconfig /renew')

        # 更新文本区域的内容
        self.textEdit.setText('网络已恢复连接')

#运行界面
app = QApplication(sys.argv)
ex = MyApp()
sys.exit(app.exec_())
