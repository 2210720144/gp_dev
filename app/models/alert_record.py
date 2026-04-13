from datetime import datetime
from app.models import db

class AlertRecord(db.Model):
    """
    告警记录表
    """
    __tablename__ = 'alert_record'

    alert_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录id')
    event_id = db.Column(db.Integer, db.ForeignKey('violation_event.event_id'), nullable=False, comment='事件id')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='用户id')
    end_time = db.Column(db.DateTime, nullable=True, comment='违停停止时间')
    next_alert_at = db.Column(db.DateTime, nullable=True, comment='下一次可触发告警的时间')
    created_at = db.Column(db.DateTime, default=datetime.now, server_default=db.func.now(), nullable=False, comment='告警创建时间')

    # Relationships
    event = db.relationship('ViolationEvent', backref=db.backref('alert_records', lazy=True))
    user = db.relationship('User', backref=db.backref('alert_records', lazy=True))

    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'next_alert_at': self.next_alert_at.strftime('%Y-%m-%d %H:%M:%S') if self.next_alert_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }