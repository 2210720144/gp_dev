from datetime import datetime, timedelta
from flask import current_app
from app.models import db
from app.models.camera import UserCameraPermission, Camera
from app.models.video import Video
from app.models.user import User
from app.models.alert_record import AlertRecord
from app.services.email_service import EmailService
from app.models.sys_config import SysConfig


class AlertService:
    # 默认回退的告警刷新时间（如果无法查询不到数据库里面告警刷新时间的话）
    DEFAULT_REFRESH_TIME = 30

    @staticmethod
    def get_refresh_time():
        """从数据库中获取告警刷新时间"""
        try:
            config = SysConfig.query.filter_by(config_key='告警刷新时间').first()
            if config:
                return float(config.config_value) * 60  # 返回时间且分转秒
        except Exception as e:
            current_app.logger.error(f"Error fetching alert refresh time: {e}")
        return AlertService.DEFAULT_REFRESH_TIME

    @classmethod
    def create_alerts(cls, camera_id, event_id, image_path=None):
        """
        为指定摄像头的违停事件创建告警记录并发送邮件。
        逻辑：
        1. 查找该摄像头的所有授权用户。
        2. 为每位用户创建一条告警记录。
        3. 发送告警邮件。
        4. 计算下一次告警时间。
        
        返回: (next_alert_time, count)
        """
        try:
            # 1. 获取授权用户
            permissions = UserCameraPermission.query.filter_by(camera_id=camera_id).all()
            
            if not permissions:
                return None, 0

            # 获取区域名称（摄像头名称）
            camera = Camera.query.get(camera_id)
            # area_name = camera.camera_name if camera else "未知区域"
            area_name = "未知区域"
            if camera:
                if camera.video_id:
                    video = Video.query.get(camera.video_id)
                    if video:
                        # 优先取视频源对应的location
                        area_name = video.location
                    else:
                        # 如果查询不到视频源对应的localtion，那我们就将摄像头的名称发送给用户
                        area_name = camera.camera_name
                else:
                    area_name = camera.camera_name

            # 2. 计算下一次告警时间
            now = datetime.now()
            refresh_time = cls.get_refresh_time()  # 间隔时间
            next_alert_time = now + timedelta(seconds=refresh_time)
            
            # 3. 为每个用户创建告警记录并发送邮件
            count = 0
            for perm in permissions:
                # 记录告警
                alert = AlertRecord(
                    event_id=event_id,
                    user_id=perm.user_id,
                    end_time=None,
                    next_alert_at=next_alert_time
                )
                db.session.add(alert)
                count += 1

                # 发送邮件
                user = User.query.get(perm.user_id)
                if user and user.email:
                    EmailService.send_alert_email(
                        to_email=user.email,
                        username=user.username,
                        area_name=area_name,
                        image_path=image_path
                    )
            
            # 注意：此处不执行 commit，交由调用方（DetectionService）在事务中统一提交
            
            return next_alert_time, count
        except Exception as e:
            current_app.logger.error(f"Error creating alerts: {e}")
            raise e

    @staticmethod
    def resolve_alerts(event_id, end_time):
        """
        结束违停事件对应的所有未处理告警记录。
        逻辑：将该事件下所有 end_time 为空的记录更新为当前结束时间。
        """
        try:
            AlertRecord.query.filter_by(
                event_id=event_id,
                end_time=None
            ).update({'end_time': end_time})
            # 同样交由调用方提交
        except Exception as e:
            current_app.logger.error(f"Error resolving alerts: {e}")
            raise e