import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
from threading import Thread, Event
import queue
import time


class RoboticArmApp:
    def __init__(self, master):
        self.master = master
        master.title("机械臂控制终端 v3.0")
        master.geometry("1000x800")

        # 通信配置
        self.serial_port = None
        self.serial_queue = queue.Queue()
        self.cmd_queue = queue.Queue()
        self.running = Event()
        self.running.set()
        self.last_send = 0
        self.send_interval = 0.12  # 120ms

        # 初始化UI
        self.create_widgets()

        # 启动工作线程
        Thread(target=self.read_serial, daemon=True).start()
        Thread(target=self.process_queue, daemon=True).start()

    def create_widgets(self):
        # 串口控制区域
        conn_frame = ttk.LabelFrame(self.master, text="串口连接")
        conn_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(conn_frame, text="端口:").grid(row=0, column=0)
        self.port_combo = ttk.Combobox(conn_frame, width=25)
        self.port_combo.grid(row=0, column=1, padx=5)

        ttk.Button(conn_frame, text="刷新", command=self.refresh_ports).grid(row=0, column=2)
        self.connect_btn = ttk.Button(conn_frame, text="连接", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=5)

        # 机械臂控制区域
        ctrl_frame = ttk.LabelFrame(self.master, text="运动控制")
        ctrl_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.sliders = {}
        joints = [
            ('Base', 90, 0, 180),
            ('Shoulder', 0, 0, 180),
            ('Elbow', 180, 0, 180),
            ('Wrist', 90, 0, 180)
        ]
        for idx, (name, init, minv, maxv) in enumerate(joints):
            ttk.Label(ctrl_frame, text=name).grid(row=idx, column=0, padx=5)
            slider = ttk.Scale(ctrl_frame, from_=minv, to=maxv,
                               orient=tk.HORIZONTAL, length=300,
                               command=lambda v, n=name: self.on_slider_change(n, v))
            slider.set(init)
            slider.grid(row=idx, column=1, pady=2)
            self.sliders[name] = slider

        # 夹爪控制
        self.gripper_var = tk.BooleanVar()
        grip_frame = ttk.Frame(ctrl_frame)
        grip_frame.grid(row=4, columnspan=2, pady=5)
        ttk.Label(grip_frame, text="夹爪:").pack(side=tk.LEFT)
        ttk.Radiobutton(grip_frame, text="打开", variable=self.gripper_var,
                        value=True, command=self.queue_command).pack(side=tk.LEFT)
        ttk.Radiobutton(grip_frame, text="关闭", variable=self.gripper_var,
                        value=False, command=self.queue_command).pack(side=tk.LEFT, padx=10)

        # 系统控制
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=5, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="复位", command=self.reset).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="急停", command=self.emergency_stop).pack(side=tk.LEFT)

        # 日志区域
        log_frame = ttk.LabelFrame(self.master, text="通信日志")
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD,
                                                  height=15, font=('Consolas', 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 布局配置
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(2, weight=1)

        self.refresh_ports()

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port_combo.get(),
                baudrate=115200,
                timeout=1,
                write_timeout=1
            )
            self.connect_btn.config(text="断开")
            self.log("连接成功")
        except Exception as e:
            self.log(f"连接失败: {str(e)}")

    def disconnect(self):
        if self.serial_port:
            self.serial_port.close()
            self.connect_btn.config(text="连接")
            self.log("已断开连接")

    def on_slider_change(self, name, value):
        self.queue_command()

    def queue_command(self):
        angles = [int(round(self.sliders[n].get())) for n in ['Base', 'Shoulder', 'Elbow', 'Wrist']]
        state = 'on' if self.gripper_var.get() else 'off'
        cmd = f"{angles[0]},{angles[1]},{angles[2]},{angles[3]} {state}"
        self.cmd_queue.put(cmd)

    def process_queue(self):
        while self.running.is_set():
            if not self.serial_port or not self.serial_port.is_open:
                time.sleep(0.1)
                continue

            try:
                # 流量控制
                if time.time() - self.last_send < self.send_interval:
                    time.sleep(0.01)
                    continue

                cmd = self.cmd_queue.get_nowait()
                full_cmd = cmd + '\n'
                self.serial_port.write(full_cmd.encode())
                self.last_send = time.time()
                self.log(f">> {cmd}")
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                self.log(f"发送错误: {str(e)}")

    def reset(self):
        for name, val in [('Base', 90), ('Shoulder', 0), ('Elbow', 180), ('Wrist', 90)]:
            self.sliders[name].set(val)
        self.gripper_var.set(False)
        self.queue_command()

    def emergency_stop(self):
        self.cmd_queue.queue.clear()
        self.serial_port.write(b"90,0,180,90 off\n")
        self.reset()
        self.log("! 急停已触发")

    def read_serial(self):
        while self.running.is_set():
            if not self.serial_port or not self.serial_port.is_open:
                time.sleep(0.1)
                continue

            try:
                line = self.serial_port.readline().decode(errors='ignore').strip()
                if line:
                    self.serial_queue.put(line)
                    self.master.after(10, self.update_log)
            except Exception as e:
                self.log(f"读取错误: {str(e)}")

    def update_log(self):
        while not self.serial_queue.empty():
            msg = self.serial_queue.get()
            self.log(f"<< {msg}")

    def log(self, message):
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)

    def on_close(self):
        self.running.clear()
        self.disconnect()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RoboticArmApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()