import threading
import cv2
import time
import os
from flask import current_app
from app.models import db
from app.models.camera import Camera
from app.models.video import Video
from app.services.detection_service import detection_service


class CameraStream(threading.Thread):
    # 继承threading模块中的Thread 类

    def __init__(self, camera_id, video_path, app):
        super().__init__()
        self.camera_id = camera_id
        self.video_path = video_path
        self.app = app        # flask的app应用实例
        self.running = False  # 线程运行状态
        self.lock = threading.Lock()  # 线程锁
        self.frame = None     # 保存帧
        self.last_frame_time = 0      # 上一帧的时间戳
        self.daemon = True    # 将当前进程设置为守护进程，这样我们手动停止代码运行时，这个子进程也会跟着停止

    def run(self):
        # 线程启动
        self.running = True  # 修改线程运行标志
        cap = cv2.VideoCapture(self.video_path)  # 使用OpenCV的VideoCapture类打开指定的视频流

        # 获取视频文件的元数据，得到其中的视频帧率
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 60: fps = 25  # 如果元数据获取异常，或者帧率过大过小，那我们就强制设置为25
        frame_interval = 1.0 / fps  # 计算完一帧后，应该停留多少秒

        while self.running:
            start_time = time.time()  # 记录开始时间
            success, frame = cap.read()  # 读取下一帧

            if not success:  # 如果没有下一帧了，那我们就重头开始播放
                # 重置文件指针，实现循环播放
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # 调用app/services/detection_service.py里面的process_frame对每帧进行检测
            with self.app.app_context():
                # 手动创建一个应用上下文，这样process_frame才能对数据库表进行操作
                try:
                    processed_frame = detection_service.process_frame(frame, camera_id=self.camera_id)
                except Exception as e:
                    print(f"[StreamService] Error processing frame for Camera {self.camera_id}: {e}")
                    processed_frame = frame

            with self.lock:  # 申请锁
                self.frame = processed_frame        # 保存处理后的帧
                self.last_frame_time = time.time()  # 更新时间戳

            # 睡眠以匹配帧率，当然如果播放速率由GPU处理控制，那么下面的代码不起作用
            process_time = time.time() - start_time  # 计算当前帧所需时间
            sleep_time = max(0, frame_interval - process_time)  # <0，说明处理过慢；>0，说明处理过快
            time.sleep(sleep_time)

        cap.release()  # 关闭文件，释放文件句柄
        
        # 删除摄像头，释放模型占用的资源
        with self.app.app_context():
            detection_service.clear_model(self.camera_id)

    def get_frame(self):
        # 获取当前保存的帧
        with self.lock:
            return self.frame

    def stop(self):
        # 停止线程
        self.running = False
        self.join()  # 阻塞线程，保证子线程真正结束


class StreamManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StreamManager, cls).__new__(cls)
            cls._instance.streams = {}
            cls._instance.lock = threading.Lock()
        return cls._instance

    def start_stream(self, app, camera_id):
        with self.lock:  # 申请锁
            if camera_id in self.streams:  # 如果当前摄像头已经开了一个线程
                stream = self.streams[camera_id]
                if stream.is_alive():  # 当前摄像头的线程正在跑
                    return stream      # 那就不用为该摄像头创建线程了，直接用原来的即可
                else:
                    # 线程结束，清除字典中对应的记录
                    del self.streams[camera_id]

            # 获取视频文件路径
            with app.app_context():
                camera = db.session.get(Camera, camera_id)  # 查询摄像头记录
                if not camera or not camera.video_id:
                    return None
                video = db.session.get(Video, int(camera.video_id))  # 找到摄像头绑定的视频
                if not video:
                    return None

                video_url = video.video_url
                if not video_url.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):  # 如果视频不是网络流媒体
                    base_dir = app.config.get('BASE_DIR') or os.path.abspath(os.getcwd())    # 那就说明是本地视频文件
                    upload_folder = os.path.join(base_dir, 'uploads')
                    video_path = os.path.join(upload_folder, os.path.basename(video_url))
                else:
                    video_path = video_url

            stream = CameraStream(camera_id, video_path, app)
            stream.start()  # start()是threading.Thread提供的
            self.streams[camera_id] = stream
            return stream

    def get_frame(self, camera_id):
        if camera_id in self.streams:
            return self.streams[camera_id].get_frame()
        return None

    def stop_all(self):
        with self.lock:
            # 申请锁，将每个摄像头的线程都结束掉
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()  # 清空字典


stream_service = StreamManager()