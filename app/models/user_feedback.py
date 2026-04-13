from datetime import datetime
from app.models import db


class UserFeedback(db.Model):
    """
    用户反馈表
    """
    __tablename__ = 'user_feedback'

    feedback_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='反馈id')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='用户id')
    title = db.Column(db.String(255), nullable=False, comment='反馈标题')
    content = db.Column(db.Text, nullable=False, comment='反馈内容')
    status = db.Column(db.String(20), default='待处理', nullable=False, comment='处理状态：待处理/已处理')
    attachment_url = db.Column(db.String(255), nullable=True, comment='附件（如图片）路径')
    created_at = db.Column(db.DateTime, default=datetime.now, server_default=db.func.now(), nullable=False,
                           comment='创建时间')

    admin_reply = db.Column(db.Text, nullable=True, comment='管理员回复内容')
    replied_at = db.Column(db.DateTime, nullable=True, comment='管理员回复时间')
    replied_by = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True, comment='回复管理员ID')

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('feedbacks', lazy=True))
    admin = db.relationship('User', foreign_keys=[replied_by], backref=db.backref('replied_feedbacks', lazy=True))

    def to_dict(self):
        return {
            'feedback_id': self.feedback_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'Unknown',
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'attachment_url': self.attachment_url,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'admin_reply': self.admin_reply,
            'replied_at': self.replied_at.strftime('%Y-%m-%d %H:%M:%S') if self.replied_at else None,
            'replied_by': self.replied_by,
            'admin_name': self.admin.username if self.admin else None
        }