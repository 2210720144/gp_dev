from datetime import datetime
from app.models import db

class YoloModel(db.Model):
    """
    YOLO模型表
    记录用户上传的YOLO模型权重文件
    """
    __tablename__ = 'yolo_model'

    model_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='模型ID')
    model_name = db.Column(db.String(100), nullable=False, comment='模型名称')
    model_url = db.Column(db.String(255), nullable=False, comment='模型文件路径')
    status = db.Column(db.String(20), default='启用', comment='状态')
    upload_by = db.Column(db.Integer, db.ForeignKey('user.user_id'), comment='上传人ID')
    upload_at = db.Column(db.DateTime, default=datetime.now, comment='上传时间')

    # 建立与User表的关联
    uploader = db.relationship('User', backref=db.backref('uploaded_models', lazy=True))

    def to_dict(self):
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'model_url': self.model_url,
            'status': self.status,
            'upload_by': self.upload_by,
            'uploader_name': self.uploader.username if self.uploader else 'Unknown',
            'upload_at': self.upload_at.strftime('%Y-%m-%d %H:%M:%S') if self.upload_at else None
        }