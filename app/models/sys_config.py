from datetime import datetime
from app.models import db


class SysConfig(db.Model):
    """
    系统参数表
    """
    __tablename__ = 'sys_config'

    config_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='参数id')
    config_key = db.Column(db.String(50), unique=True, nullable=False, comment='参数名')
    config_value = db.Column(db.Numeric(10, 2), nullable=False, comment='参数值')
    unit = db.Column(db.String(50), nullable=True, comment='参数单位')
    description = db.Column(db.String(100), nullable=True, comment='参数说明')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='参数更新时间')

    def to_dict(self):
        return {
            'config_id': self.config_id,
            'config_key': self.config_key,
            'config_value': float(self.config_value) if self.config_value is not None else 0.0,
            'unit': self.unit,
            'description': self.description,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }