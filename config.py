import os
from datetime import timedelta


class Config:
    # flask通用密钥，服务器用的
    SECRET_KEY = 'dev-secret-key'  # 密钥，写死就行，毕设系统不用管安全
    # 身份验证密钥，给用户登录用的
    JWT_SECRET_KEY = os.urandom(24)  # 使用随机密钥，每次重启服务后，之前的Token都会失效，从而强制用户重新登录
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Token 有效期设置为 24 小时
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 关闭“跟踪数据库模型的修改”的功能

    # 数据库连接信息
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/gp_db'

    # 邮箱配置信息（QQ邮箱，SMTP服务）
    MAIL_SERVER = 'smtp.qq.com'  # 服务器地址
    MAIL_PORT = 465  # 服务器的端口号
    MAIL_USE_SSL = True  # 开启SSL加密
    MAIL_USERNAME = '1795123261@qq.com'  # 登录服务器的账号
    MAIL_PASSWORD = 'buekwwdxaxeqbeed'  # QQ邮箱授权码
    MAIL_DEFAULT_SENDER = '1795123261@qq.com'  # 发件人

    # 文件上传配置
    # 获取当前文件所在目录的绝对路径 (即 gp_dev 目录)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # 上传文件存储路径：gp_dev/uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    # 限制上传文件大小为 3GB
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024 * 1024


class DevelopmentConfig(Config):
    # 开发配置
    DEBUG = True


class ProductionConfig(Config):
    # 生产配置
    DEBUG = False
    # You might want to override SECRET_KEY and others here using os.environ.get()


# 指定配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig  # 默认是开发配置
}
