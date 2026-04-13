from datetime import datetime
from app.models import db

class Camera(db.Model):
    """
    摄像头表
    """
    __tablename__ = 'camera'

    camera_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='摄像头id')
    camera_name = db.Column(db.String(100), comment='摄像头名称')
    video_id = db.Column(db.Integer, comment='视频id')
    created_by = db.Column(db.Integer, db.ForeignKey('user.user_id'), comment='创建人ID') # 用户文档标注为DATETIME，但作为外键应为ID类型
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'camera_id': self.camera_id,
            'camera_name': self.camera_name,
            'video_id': self.video_id,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class UserCameraPermission(db.Model):
    """
    用户摄像头权限表
    """
    __tablename__ = 'user_camera_permission'

    permission_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='权限id')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='用户id')
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.camera_id'), nullable=False, comment='摄像头id')
    granted_at = db.Column(db.DateTime, default=datetime.now, comment='授权时间')

    def to_dict(self):
        return {
            'permission_id': self.permission_id,
            'user_id': self.user_id,
            'camera_id': self.camera_id,
            'granted_at': self.granted_at.strftime('%Y-%m-%d %H:%M:%S') if self.granted_at else None
        }