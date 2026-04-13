from datetime import datetime
from app.models import db

class ViolationEvent(db.Model):
    """
    违停事件表
    """
    __tablename__ = 'violation_event'

    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='事件id')
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.camera_id'), nullable=False, comment='摄像头id')
    bicycle_id = db.Column(db.Integer, nullable=False, comment='单车目标id')
    start_time = db.Column(db.DateTime, default=datetime.now, nullable=False, comment='违停开始时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='违停停止时间')

    # Optional: Relationship to Camera model for easier access
    camera = db.relationship('Camera', backref=db.backref('violation_events', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'event_id': self.event_id,
            'camera_id': self.camera_id,
            'bicycle_id': self.bicycle_id,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None
        }