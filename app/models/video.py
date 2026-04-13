from datetime import datetime
from app.models import db

class Video(db.Model):
    """
    视频源表
    """
    __tablename__ = 'video'

    video_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='视频id')
    video_name = db.Column(db.String(100), comment='视频源名称')
    video_url = db.Column(db.String(255), nullable=False, comment='视频路径')
    location = db.Column(db.String(100), comment='所在区域')
    format = db.Column(db.String(20), comment='视频格式')
    upload_time = db.Column(db.DateTime, default=datetime.now, comment='上传时间')
    upload_by = db.Column(db.Integer, db.ForeignKey('user.user_id'), comment='上传的管理员ID')
    camera_id = db.Column(db.Integer, comment='当前关联的摄像头ID')
    config_status = db.Column(db.String(50), default='未配置', comment='配置状态')

    # 建立与User表的关联（可选，方便查询上传者信息）
    uploader = db.relationship('User', backref=db.backref('uploaded_videos', lazy=True))

    def to_dict(self):
        return {
            'video_id': self.video_id,
            'video_name': self.video_name,
            'video_url': self.video_url,
            'location': self.location,
            'format': self.format,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S') if self.upload_time else None,
            'upload_by': self.upload_by,
            'camera_id': self.camera_id,
            'config_status': self.config_status
        }