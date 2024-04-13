import shutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtGui import QIcon
import sys
import glob
from edge_tts import Communicate
import ffmpeg
import traceback
import psutil
from datetime import datetime
import time
import asyncio
import os
import json
import subprocess



class MyApp(QWidget):
    def __init__(self):

        super().__init__()
        self.initUI()
        self.stop_thread = False  #控制线程的结束

    exe_name_block = "block_ets.exe"  # 关闭ets联网的文件
    exe_name_open = "open_ets.exe"  # 开启ets联网的文件

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
        self.setWindowIcon(QIcon('a.ico'))


    def get_answers(self):
        # 执行获取部分
        appdata_path = os.getenv('APPDATA')
        base_path = os.path.join(appdata_path, '74656D705F74656D705F74656D705F74002')
        folder_name = ''
        latest_mtime = 0
        for name in os.listdir(base_path):
            if name.isdigit():
                folder_path = os.path.join(base_path, name)
                mtime = os.path.getmtime(folder_path)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    folder_name = name

        titles = ['角色扮演', '故事复述']
        answers_dict = {}
        for i in range(2, len(titles) + 2):
            file_name = f'content0001000{i}'
            file_path = os.path.join(base_path, folder_name, file_name, 'content.json')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'question' in data['info']:
                    questions = data['info']['question']
                    for j, question in enumerate(questions):
                        for k, answer in enumerate(question['std']):
                            answers_dict[f'{titles[i - 2]}_{j + 1}'] = answer["value"]
                            break
                else:
                    for k, answer in enumerate(data['info']['std']):
                        answers_dict[titles[i - 2]] = answer["value"]
                        break
            except Exception as e:
                print("获取错误")
        return answers_dict

    async def save_answers_to_mp3(self):
            answers = self.get_answers()
            total = len(answers)
            # 获取ets_auto的路径
            appdata_path = os.getenv('APPDATA')
            ets_auto_path = os.path.join(appdata_path, 'ets_auto')
            # 如果ets_auto文件夹不存在，则创建它
            if not os.path.exists(ets_auto_path):
                os.makedirs(ets_auto_path)
            # 为每个项目生成一个mp3文件
            for i, (key, value) in enumerate(answers.items(), start=1):
                # 去除字符串中的</p><p>
                value = value.replace('</p><p>', ' ')
                tts = Communicate(text=value, voice='zh-CN-YunyangNeural', rate='-20%')
                mp3_file = f'{key}.mp3'
                await tts.save(mp3_file)

                # 使用ffmpeg将mp3文件转换为wav文件，保存到ets_auto文件夹
                wav_file = os.path.join(ets_auto_path, f'{key}.wav')
                ffmpeg.input(mp3_file).output(wav_file, ar=16000, ac=1).overwrite_output().run()

                # 删除mp3文件
                os.remove(mp3_file)

                # 打印进度
                print(f'已完成 {i}/{total} ({100.0 * i / total:.1f}%)')
            subprocess.run(['start', self.exe_name_block], shell=True)


    def check_ets_running(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'Ets.exe':
                return proc.exe()
        return None

    def on_start(self):
        current_text = self.textEdit.toPlainText()

        messages = {
            '暂未运行e听说，请运行后再试': '先打开e听说再来啊啊啊！',
            '先打开e听说再来啊啊啊！': '咋这么不听劝呢！别点了真的没用的！',
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

    # 定义一个变量用于记录当前替换到第几题
    current_question = 0


    def on_continue(self):
        try:

            appdata_path = os.getenv('APPDATA')
            ets_auto_path = os.path.join(appdata_path, 'ets_auto')

            question_files = ['content', '角色扮演_1', '角色扮演_2', '角色扮演_3', '角色扮演_4', '角色扮演_5', '角色扮演_6', '角色扮演_7', '角色扮演_8', '故事复述']

            # 获取当前的提示信息用于判定
            current_text = self.textEdit.toPlainText()


            if current_text == '请直到E听说出现提示"评分失败"时点击"继续"并重新评分':
                # 打开网络连接
                subprocess.run(['start', self.exe_name_open], shell=True)

                # 更新文本区域的内容
                self.textEdit.setText('一切完成，若有问题请带报告反馈！')
                return

            if current_text == f'当前题目为({question_files[self.current_question]}), 结束录音后点击继续':
                # 检测record_file中最新的wav文件是否与当前时间相差不超过1分钟
                wav_files = glob.glob(os.path.join(self.record_file, '*.wav'))
                latest_wav = max(wav_files, key=os.path.getmtime)
                if (datetime.now() - datetime.fromtimestamp(os.path.getmtime(latest_wav))).seconds > 60:
                    self.textEdit.setText('似乎出现了异常，请确定完成录音后再试，已为你恢复网络连接')
                    #打开E听说网络连接
                    subprocess.run(['start', self.exe_name_open], shell=True)
                    return

                # 记录最新的wav文件的名字并删除这个文件
                latest_wav_name = os.path.basename(latest_wav)
                os.remove(latest_wav)

                # 将保存在ets_auto文件夹中的wav文件移动到record_file文件夹，并重命名为刚刚记录的最新的wav文件的名字
                shutil.move(os.path.join(ets_auto_path, question_files[self.current_question] + '.wav'),
                            os.path.join(self.record_file, latest_wav_name))

                # 更新current_question的值
                self.current_question = self.current_question + 1

                if self.current_question == 10:

                    self.textEdit.setText('请直到E听说出现提示"评分失败"时点击"继续"并重新评分')
                    self.current_question = 114514


                else:
                    if self.current_question < 10:

                        self.textEdit.setText(f'当前题目为({question_files[self.current_question]}), 结束录音后点击继续')



            elif current_text == '即将关闭网络，请点击继续':
                self.textEdit.setText('正在转换中，界面卡住为正常现象')
                # 异步保存答案
                asyncio.run(self.save_answers_to_mp3())


                # 从配置文件中获取lastest_answer和record_file的位置
                with open(self.config_path, 'r') as f:
                    lines = f.readlines()
                    self.latest_folder = lines[-1].split(': ')[1].strip()
                    self.record_file = lines[-2].split(': ')[1].strip()

                # 找到content.mp3文件并转换为wav文件
                content_mp3 = os.path.join(self.latest_folder, 'content00010001', 'material', 'content.mp3')
                content_wav = os.path.join(ets_auto_path, 'content.wav')
                ffmpeg.input(content_mp3).output(content_wav, ar=16000, ac=1).overwrite_output().run()

                question_files2 = ['content', '角色扮演_1', '角色扮演_2', '角色扮演_3', '角色扮演_4', '角色扮演_5',
                                  '角色扮演_6', '角色扮演_7', '角色扮演_8', '故事复述']



                # 更新文本区域的内容
                self.textEdit.setText(f'当前题目为({question_files2[self.current_question]}), 结束录音后点击继续')



            # 总有人喜欢什么都点一点>_<
            elif current_text == '暂未运行e听说，请运行后再试' or current_text == '先打开e听说再来啊啊啊啊啊啊！' or current_text == '咋这么不听劝呢！别点了真的没用的！':

                self.textEdit.setText('别试了，点我也没用')




        except Exception as e:

            # 如果出现错误，将错误信息和错误发生的行数输出到文本框！！！
            tb = traceback.format_exc()
            self.textEdit.setText(str(e) + '\n' + str(tb))

    def renew_network(self):
        self.stop_thread = True  # 停止线程
        # 打开网络连接
        subprocess.run(['start', self.exe_name_open], shell=True)
        self.textEdit.setText('网络已恢复连接')

#运行界面
app = QApplication(sys.argv)
ex = MyApp()
sys.exit(app.exec_())




