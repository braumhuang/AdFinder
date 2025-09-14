import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import webbrowser
import imagehash
import shutil
import time
import glob
import json
import sys
import os
import av


class GSObject:
    @classmethod
    def join(cls, *paths):
        return os.path.join(*paths)

    @classmethod
    def parse(cls, path: str) -> (str, str, str, str):
        folder, name = os.path.split(path)
        basename, extension = os.path.splitext(name)
        return folder, name, basename, extension.lower()

    @classmethod
    def glob_all(cls, folder: str):
        search_dir = cls.join(folder, '**')
        return glob.glob(search_dir, recursive=True)

    @classmethod
    def all_file(cls, folder: str):
        return [path.replace('\\', '/') for path in cls.glob_all(folder) if os.path.isfile(path)]

    @classmethod
    def rsc_path(cls, *paths):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, *paths)

    @classmethod
    def app_path(cls, *paths):
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(exe_dir, *paths)

    @classmethod
    def log(cls, text: str, basename):
        path = cls.app_path('log', f'{basename}.txt')
        file_folder, file_name = os.path.split(path)
        if not os.path.exists(file_folder):
            os.makedirs(file_folder)
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write('{}\n'.format(text))
        return path

    @classmethod
    def timestamp(cls):
        return str(int(time.time()))

    @classmethod
    def screenshot(cls, video_path, time_second):
        try:
            container = av.open(video_path)
            container.seek(int(time_second * av.time_base))
            for frame in container.decode(video=0):
                image = frame.to_image()
                return image
                break
            container.close()
        except Exception:
            return None

    @classmethod
    def compare(cls, image1, image2):
        try:
            # 计算感知哈希
            hash1 = imagehash.average_hash(image1)
            hash2 = imagehash.average_hash(image2)
            # 计算汉明距离
            hamming_distance = hash1 - hash2
            # 转换为相似度（假设最大汉明距离为64）
            max_distance = 64  # average_hash 返回 64 位哈希
            similarity = 1 - (hamming_distance / max_distance)
            return similarity
        except Exception as e:
            print(f'错误: {str(e)}')
            return None


class AdFinderConfig:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        default_config = {
            'progress': 5,
            'similarity': 98,
            'format': 'mp4,avi,mkv,wmv,mov,mpg,ts,rmvb'
        }

        # 如果配置文件不存在，初始化默认值并写入
        if not os.path.exists(self.config_file):
            self.save_config(default_config)
            return default_config
        # 读取现有配置文件
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.save_config(default_config)
            return default_config

    def save_config(self, config):
        # 保存配置到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def update_config(self, key, value):
        # 更新配置并保存
        self.config[key] = value
        self.save_config(self.config)

    def get_config(self, key, default=None):
        # 获取配置值
        return self.config.get(key, default)

    def get_extension(self):
        format_value = self.get_config('format').replace('，', ',')
        return [f'.{fmt.strip().lower()}' for fmt in format_value.split(',') if fmt.strip()]

    def get_tip(self):
        return '查找视频文件是否含有相同广告，查找的结果输出在软件目录下的log文件夹中' \
               '\n通过对示例文件某一秒进行截图，逐一对比工作目录下视频文件某一秒的截图是否相似'


class AdFinderApp:
    def __init__(self, root):
        self.version = 'V1.0'
        self.root = root
        self.root.title(f'AdFinder {self.version}')
        self.root.geometry('720x405')
        self.root.resizable(False, False)
        self.root.configure(bg='#F0F0F0')
        self.root.iconbitmap(GSObject.rsc_path('icon.ico'))
        self.root.protocol('WM_DELETE_WINDOW', self.close)

        # 初始化配置管理
        self.config = AdFinderConfig()
        self.run = False
        self.brk = False

        # 设置全局字体和颜色
        self.label_ft = ('Helvetica', 12)
        self.label_fg = '#333333'
        self.label_bg = '#F0F0F0'

        self.entry_ft = ('Helvetica', 12)
        self.entry_fg = '#333333'
        self.entry_bg = '#FFFFFF'

        self.button_ft = ('Helvetica', 12, 'bold')
        self.button_fg = '#FFFFFF'
        self.button_bg = '#4CAF50'
        self.button_active_bg = '#45A049'
        self.start_button_bg = '#2196F3'
        self.start_button_active_bg = '#1E88E5'

        # 第一行
        self.label_file = tk.Label(root, text='示例文件', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_file.place(x=20, y=20, width=100, height=30)

        self.entry_file = tk.Entry(root, font=self.entry_ft, bg=self.entry_bg, fg=self.entry_fg)
        self.entry_file.place(x=130, y=20, width=460, height=30)
        self.entry_file.insert(0, self.config.get_config('file', ''))

        self.button_file = tk.Button(root, text='选择文件', font=self.button_ft, bg=self.button_bg,
                                     fg=self.button_fg, activebackground=self.button_active_bg,
                                     command=self.select_file, relief='flat', highlightthickness=0, bd=0)
        self.button_file.place(x=600, y=20, width=100, height=30)

        # 第二行
        self.label_progress = tk.Label(root, text='截图时刻', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_progress.place(x=20, y=70, width=100, height=30)

        self.entry_progress = tk.Entry(root, font=self.entry_ft, bg=self.entry_bg, fg=self.entry_fg,
                                       validate='key', validatecommand=(root.register(self.validate_int), '%P'))
        self.entry_progress.place(x=130, y=70, width=460, height=30)
        self.entry_progress.insert(0, str(self.config.get_config('progress', 5)))

        self.label_seconds = tk.Label(root, text='(单位为秒)', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_seconds.place(x=600, y=70, width=100, height=30)

        # 第三行
        self.label_dir = tk.Label(root, text='工作目录', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_dir.place(x=20, y=120, width=100, height=30)

        self.entry_dir = tk.Entry(root, font=self.entry_ft, bg=self.entry_bg, fg=self.entry_fg)
        self.entry_dir.place(x=130, y=120, width=460, height=30)
        self.entry_dir.insert(0, self.config.get_config('dir', ''))

        self.button_dir = tk.Button(root, text='选择目录', font=self.button_ft, bg=self.button_bg,
                                    fg=self.button_fg, activebackground=self.button_active_bg,
                                    command=self.select_directory, relief='flat', highlightthickness=0, bd=0)
        self.button_dir.place(x=600, y=120, width=100, height=30)

        # 第四行
        self.label_similarity = tk.Label(root, text='相似度', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_similarity.place(x=20, y=170, width=100, height=30)

        self.entry_similarity = tk.Entry(root, font=self.entry_ft, bg=self.entry_bg, fg=self.entry_fg,
                                         validate='key',
                                         validatecommand=(root.register(self.validate_similarity), '%P'))
        self.entry_similarity.place(x=130, y=170, width=460, height=30)
        self.entry_similarity.insert(0, str(self.config.get_config('similarity', 98)))

        self.label_similarity_range = tk.Label(root, text='(0-100)', font=self.label_ft, bg=self.label_bg,
                                               fg=self.label_fg)
        self.label_similarity_range.place(x=600, y=170, width=100, height=30)

        # 第五行
        self.label_format = tk.Label(root, text='扫描格式', font=self.label_ft, bg=self.label_bg, fg=self.label_fg)
        self.label_format.place(x=20, y=220, width=100, height=30)

        self.entry_format = tk.Entry(root, font=self.entry_ft, bg=self.entry_bg, fg=self.entry_fg)
        self.entry_format.place(x=130, y=220, width=460, height=30)
        self.entry_format.insert(0, self.config.get_config('format', 'mp4,.avi,mkv,wmv,mov,mpg,ts,rmvb'))

        # 第六行
        self.tip_var = tk.StringVar()
        self.tip_var.set(self.config.get_tip())
        self.label_thanks = tk.Label(root, textvariable=self.tip_var, font=self.label_ft, bg=self.entry_bg,
                                     fg=self.label_fg)
        self.label_thanks.place(x=20, y=270, width=680, height=65)

        # 第七行
        self.button_clean = tk.Button(root, text='清理日志', font=self.button_ft, bg=self.start_button_bg,
                                      fg=self.button_fg, activebackground=self.start_button_active_bg,
                                      relief='flat', highlightthickness=0, bd=0, command=self.clean)
        self.button_clean.place(x=20, y=355, width=100, height=30)
        self.button_browser = tk.Button(root, text='访问发布页面', command=self.browser, fg='blue',
                                        font=('Arial', 10, 'underline'), bd=0, highlightthickness=0)
        self.button_browser.place(x=250, y=370, width=220, height=20)
        self.button_start = tk.Button(root, text='开始扫描', font=self.button_ft, bg=self.start_button_bg,
                                      fg=self.button_fg, activebackground=self.start_button_active_bg,
                                      relief='flat', highlightthickness=0, bd=0, command=self.start)
        self.button_start.place(x=600, y=355, width=100, height=30)

    def validate_int(self, value):
        if value == '':
            return True
        try:
            return int(value) > 0
        except ValueError:
            return False

    def validate_similarity(self, value):
        if value == '':
            return True
        try:
            val = int(value)
            return 0 <= val <= 100
        except ValueError:
            return False

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, file_path)

    def select_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entry_dir.delete(0, tk.END)
            self.entry_dir.insert(0, dir_path)

    def browser(self):
        webbrowser.open('https://github.com/braumhuang/AdFinder/releases')

    def change_button(self, able):
        self.button_file.config(state='normal' if able else 'disabled')
        self.button_dir.config(state='normal' if able else 'disabled')
        self.button_start.config(state='normal' if able else 'disabled')
        self.button_clean.config(state='normal' if able else 'disabled')
        self.root.update()

    def clean(self):
        path = GSObject.app_path('log')
        if os.path.exists(path):
            shutil.rmtree(path)

    def start(self):
        _, _, _, ext = GSObject.parse(self.entry_file.get())
        if ext not in self.config.get_extension():
            messagebox.showerror('参数错误', '请选择正确的示例文件')
            return
        # 更新配置
        self.config.update_config('file', self.entry_file.get())
        self.config.update_config('progress', int(self.entry_progress.get()))
        self.config.update_config('dir', self.entry_dir.get())
        self.config.update_config('similarity', int(self.entry_similarity.get()))
        self.config.update_config('format', self.entry_format.get().lower())

        self.tip_var.set('开始扫描')
        self.run = True
        self.change_button(False)
        log_basename = GSObject.timestamp()
        log_path = None
        image1 = GSObject.screenshot(self.entry_file.get(), int(self.entry_progress.get()))
        if image1:
            for file in GSObject.all_file(self.entry_dir.get()):
                if self.brk:
                    break
                d, n, b, e = GSObject.parse(file)
                if e in self.config.get_extension():
                    self.tip_var.set(file)
                    self.root.update()
                    image2 = GSObject.screenshot(file, int(self.entry_progress.get()))
                    if image2:
                        result = GSObject.compare(image1, image2)
                        if result is not None and result > int(self.entry_similarity.get()) / 100:
                            log_path = GSObject.log(file, log_basename)
        self.tip_var.set(self.config.get_tip())
        if log_path and not self.brk:
            os.startfile(log_path)
        self.run = False
        self.change_button(True)

    def close(self):
        if self.run:
            if messagebox.askyesno('确认退出', '正在扫描中，确定退出 AdFinder 吗？'):
                self.brk = True
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = AdFinderApp(root)
    root.mainloop()
