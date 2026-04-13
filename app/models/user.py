from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db

# 角色枚举
class UserRole(Enum):
    USER = '普通用户'
    ADMIN = '管理员用户'
    ROOT = '超级管理员'

# 账户状态枚举
class UserStatus(Enum):
    PENDING = '待审核'
    ACTIVE = '正常'
    DISABLED = '禁用'
    DELETED = '已注销'

# 用户表
class User(db.Model):
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column('password', db.String(255), nullable=False) # Store hash
    email = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# 验证码数据模型
class VerificationCode(db.Model):
    __tablename__ = 'verification_code'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(50), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
