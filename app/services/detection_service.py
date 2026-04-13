import os
import cv2
import torch
from flask import current_app
from app.models.yolo_model import YoloModel
from app.models import db

from datetime import datetime
from app.models.violation_event import ViolationEvent
from app.services.alert_service import AlertService
from app.models.sys_config import SysConfig

class DetectionService:
    _instance = None
    
    # 默认回退的违停阈值（秒）
    DEFAULT_THRESHOLD = 60

    def __new__(cls):
        # 如果还没有创建一个DetectionService实例，就创建一个
        if cls._instance is None:
            # 使用基类的__new__创建一个新实例
            cls._instance = super(DetectionService, cls).__new__(cls)
            # 创建一个字典，用来记录视频中出现的单车目标和时间
            cls._instance.track_history = {} # {camera_id: {track_id: {'start_time': dt, 'last_seen': dt, 'alerted': bool}}}
            # 创建一个字典，用来存放已加载的模型，当然，模型都是使用全局的yolo模型
            cls._instance.models = {} # {camera_id: {'model': model, 'path': path}}
        return cls._instance

    def get_active_model_path(self):
        """获取当前启用的yolo模型的路径"""
        try:
            # 查询状态为启用的模型记录
            model_record = YoloModel.query.filter_by(status='启用').first()
            if not model_record:
                return None

            # 获取到当前项目所在的根路径，也就gp_dev/
            base_dir = current_app.config.get('BASE_DIR') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            # 将查询到的yolo模型的路径拼接上去，得到模型的完整路径
            full_path = os.path.join(base_dir, 'yolo_models', model_record.model_url)
            return full_path
        except Exception as e:
            # 记录异常的日志
            current_app.logger.error(f"Error getting active model: {e}")
            return None

    def load_model(self, camera_id=None):
        """为每个摄像头加载一个yolo模型"""
        try:
            # 导入yolo
            from ultralytics import YOLO
        except ImportError:
            current_app.logger.error("Ultralytics not installed.")
            return None

        # 获取模型路径
        model_path = self.get_active_model_path()
        if not model_path or not os.path.exists(model_path):
            current_app.logger.warning(f"Model path not found: {model_path}")
            return None

        # 如果摄像头ID为空，就设为“default”
        key = camera_id if camera_id is not None else 'default'

        # 看看当前的摄像头是否已经有了一个yolo模型
        if key in self.models:
            # 拿出对应的模型记录
            entry = self.models[key]
            # 如果对应的模型记录的模型跟当前启用的模型路径一致，就返回模型，反之，先加载当前启用的模型给摄像头，再返回模型
            if entry['path'] == model_path:
                return entry['model']
        
        # 加载新yolo模型给摄像头
        try:
            current_app.logger.info(f"Loading YOLO model for {key} from {model_path}...")
            # 加载模型
            model = YOLO(model_path)
            self.models[key] = {'model': model, 'path': model_path}
            current_app.logger.info(f"YOLO model loaded successfully for {key}.")
            return model
        except Exception as e:
            current_app.logger.error(f"Failed to load YOLO model: {e}")
            return None

    def clear_model(self, camera_id):
        """清除一些不需要检测的摄像头的模型，以释放显存"""
        key = camera_id if camera_id is not None else 'default'
        if key in self.models:
            # 清理模型
            del self.models[key]
            current_app.logger.info(f"Cleared YOLO model for {key}.")

    def get_violation_threshold(self):
        """从数据库中获取违停阈值（需要转化为秒）"""
        try:
            config = SysConfig.query.filter_by(config_key='违停判定时间').first()
            if config:
                return float(config.config_value) * 60  # 分转化为秒
        except Exception as e:
            current_app.logger.error(f"Error fetching violation threshold: {e}")
        # 如果在数据库表中查找不到记录，就返回默认值
        return self.DEFAULT_THRESHOLD

    def get_camera_status(self, camera_id):
        """
        获取当前摄像头实时检测的数据
        返回{ 'bicycle_count': int, 'violation_count': int }
        """
        # 查不到摄像头记录，返回零
        if camera_id not in self.track_history:
            return {'bicycle_count': 0, 'violation_count': 0}

        # 获取该摄像头下全部的检测记录
        cam_history = self.track_history[camera_id]
        # 当前时间
        now = datetime.now()
        # 获取违停阈值
        threshold = self.get_violation_threshold()
        
        # 筛选出活跃车辆 (只统计最近5秒内还在画面里出现的车)
        active_tracks = [
            # 如果当前时间和上次出现时间的小于5秒，就算是活跃车辆
            info for info in cam_history.values() 
            if (now - info['last_seen']).total_seconds() <= 5
        ]

        # 计算总车辆数
        bicycle_count = len(active_tracks)
        # 计算发生违停车辆数
        violation_count = sum(
            # 如果当前时间减去开始时间超出了违停阈值就记为1，就算是违停车辆
            1 for info in active_tracks 
            if (now - info['start_time']).total_seconds() > threshold
        )
        
        return {
            'bicycle_count': bicycle_count,
            'violation_count': violation_count
        }

    def process_frame(self, frame, camera_id=None):
        """
        在单帧上运行检测和跟踪
        返回带有绘制检测框的帧（仅检测单车目标）
        """
        model = self.load_model(camera_id)
        if not model:
            # 如果没有模型，就返回原始帧
            return frame

        try:
            # 明确单车目标
            target_classes = None
            # 查看模型的类别名称表
            if hasattr(model, 'names'):
                # 查找到单车目标
                target_ids = [k for k, v in model.names.items() if str(v).lower() in ['bicycle', 'bike', '单车']]
                # 如果有单车目标，就将其赋值给target_classes
                if target_ids:
                    target_classes = target_ids
                # 如果发现其中有目标ID为1的，就检测ID为1的目标
                elif 1 in model.names:
                    # target_classes = [1]
                     pass

            # 运行模型进行目标跟踪（persistent=True对于跨帧跟踪很重要）
            # 还要将单车目标给过滤出来，不然就是全部检测了
            results = model.track(frame, persist=True, verbose=False, classes=target_classes, conf=0.4)
            
            # 复制一份帧
            annotated_frame = frame.copy()
            
            # 如果摄像头ID不为空
            if camera_id is not None:
                # 且摄像头ID不在记录里面
                if camera_id not in self.track_history:
                    # 为这个摄像头创建一个记录
                    self.track_history[camera_id] = {}

                # 找到了该摄像头对应的记录
                cam_history = self.track_history[camera_id]
                now = datetime.now()
                
                # 找出已经离开画面超过5秒钟的单车
                stale_ids = [tid for tid, info in cam_history.items() if (now - info['last_seen']).total_seconds() > 5]
                for tid in stale_ids:
                    # 下面的if是标记违停结束时间的逻辑
                    # 如果发现已经离开监控画面的单车目标中有已经触发违停的
                    if cam_history[tid].get('alerted', False):
                        try:
                            # 先是找到这条记录
                            event = ViolationEvent.query.filter_by(
                                camera_id=camera_id,
                                bicycle_id=tid,
                                end_time=None
                            ).first()

                            # 如果真的在违停时间表中找到了对应的记录，那就记录违停结束时间
                            if event:
                                event.end_time = cam_history[tid]['last_seen']
                                
                                # 将告警记录表对应的告警记录也更新，也就是填上结束时间
                                AlertService.resolve_alerts(event.event_id, cam_history[tid]['last_seen'])
                                
                                db.session.commit()  # 提交更改
                                current_app.logger.info(f"Violation Ended: Camera {camera_id}, Bicycle {tid}")
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"Failed to record violation end: {e}")

                    del cam_history[tid]  # 删除掉已经结束违停的目标

            if results and results[0].boxes:
                boxes = results[0].boxes
                
                for box in boxes:
                    # 检测框边界
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # 跟踪ID
                    track_id = int(box.id[0]) if box.id is not None else 0
                    
                    # 检测框颜色设置为绿色，表示没有违停
                    color = (0, 255, 0)
                    
                    # 违停告警状态（三个变量）
                    # 1、是否触发了违停，默认是否
                    should_alert = False
                    # 是否第一次触发，也是默认否
                    is_first_alert = False
                    # 违停开始时间，默认为空
                    start_time = None
                    
                    # 下面是判断违停和状态更新逻辑
                    if camera_id is not None and track_id != 0:
                        # 先是取出摄像头里面所有的单车目标记录
                        cam_history = self.track_history[camera_id]
                        now = datetime.now()

                        # 如果当前的检测结果的跟踪ID不在字典里面，说明该目标是新的目标，所以新加一条记录
                        if track_id not in cam_history:
                            cam_history[track_id] = {
                                'start_time': now,
                                'last_seen': now,
                                'alerted': False
                            }
                        else:
                            # 如果字典就原本就有，说明是已经检测出来的目标
                            cam_history[track_id]['last_seen'] = now
                            start_time = cam_history[track_id]['start_time']
                            duration = (now - start_time).total_seconds()
                            
                            # 如果当前的单车目标出现的持续时间超过了违停阈值
                            if duration > self.get_violation_threshold():
                                color = (0, 0, 255) # 将检测框的颜色变为红色

                                # 如果发现是第一次触发违停
                                if not cam_history[track_id].get('alerted'):
                                    should_alert = True
                                    is_first_alert = True
                                else:
                                    # 如果之前已经触发了违停告警，那就获取该单车目标下次可告警的时间
                                    next_alert = cam_history[track_id].get('next_alert_at')
                                    # 下次可告警的时间存在且当前时间已经超出了它，那就可以再次触发告警
                                    if next_alert and now >= next_alert:
                                        should_alert = True

                    # 在监控画面上绘制检测框
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

                    # 置信度
                    conf = float(box.conf[0])
                    # 目标类别ID
                    cls_id = int(box.cls[0])
                    # 目标类别名字
                    cls_name = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)
                    # 将上面的信息形成一个标签
                    label = f"ID:{track_id} {cls_name} {conf:.2f}"
                    
                    font_scale = 0.8  # 标签文字大小
                    thickness = 2  # 文字线条长度
                    # 计算标签所需的背景框的大小
                    (w, h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                    # 在监控画面上绘制标签背景的实心矩形框，颜色要和检测框一致，-1表示内部也要填充，而不是仅仅一个矩形线框
                    cv2.rectangle(annotated_frame, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
                    # 将标签文本绘制到画面上
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)

                    # 告警处理
                    if should_alert:
                        try:
                            event_id = None
                            
                            # Capture Screenshot
                            image_path = None
                            try:
                                # 时间戳
                                timestamp = int(datetime.now().timestamp())
                                # 图片名称
                                filename = f"violation_{camera_id}_{track_id}_{timestamp}.jpg"
                                # 将图片保存到gp_dev/illegal_stop_image
                                save_dir = os.path.join(current_app.config['BASE_DIR'], 'illegal_stop_image')
                                if not os.path.exists(save_dir):
                                    os.makedirs(save_dir)
                                image_path = os.path.join(save_dir, filename)
                                # 将当前帧保存到指定目录下面（带检测框的）
                                cv2.imwrite(image_path, annotated_frame)
                            except Exception as img_err:
                                current_app.logger.error(f"Failed to save screenshot: {img_err}")

                            # 如果发现是第一次触发的告警
                            if is_first_alert:
                                # 创建一个违停时间记录
                                event = ViolationEvent(
                                    camera_id=camera_id,
                                    bicycle_id=track_id,
                                    start_time=start_time
                                )
                                db.session.add(event)  # 添加记录到会话中
                                db.session.flush()     # 执行变更
                                
                                event_id = event.event_id  # 获取记录的主键
                                cam_history[track_id]['alerted'] = True
                                cam_history[track_id]['event_id'] = event_id
                                current_app.logger.info(f"Violation Started: Camera {camera_id}, Bicycle {track_id}")
                            else:
                                event_id = cam_history[track_id].get('event_id')

                            # 调用AlertService给用户告警
                            if event_id:  # 如果主键不为空，也就是有记录
                                next_alert_time, count = AlertService.create_alerts(camera_id, event_id, image_path)
                                cam_history[track_id]['next_alert_at'] = next_alert_time
                                
                                db.session.commit()
                                if count > 0:  # 如果给至少一个人发送了告警，那就记录日志
                                    current_app.logger.info(f"Alert Triggered: Camera {camera_id}, Users {count}, Type {'First' if is_first_alert else 'Repeat'}")
                        
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"Failed to record violation/alert: {e}")

            return annotated_frame
        except Exception as e:
            current_app.logger.error(f"Error processing frame: {e}")
            return frame

detection_service = DetectionService()