from flask_sqlalchemy import SQLAlchemy

# 初始化数据库操作核心对象
db = SQLAlchemy()

# 导入模型以便迁移工具能够识别
from app.models.user import User, UserRole, UserStatus, VerificationCode
from app.models.video import Video
from app.models.camera import Camera, UserCameraPermission
from app.models.yolo_model import YoloModel
from app.models.violation_event import ViolationEvent
from app.models.alert_record import AlertRecord
from app.models.user_feedback import UserFeedback
from app.models.sys_config import SysConfig
