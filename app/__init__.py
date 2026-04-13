from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_mail import Mail
from app.models import db
from config import config

# 初始化数据库迁移工具
migrate = Migrate()
mail = Mail()


def create_app(config_name='default'):
    # 创建flask应用对象
    app = Flask(__name__)  
    # 加载配置（包括数据库URI）
    app.config.from_object(config[config_name])

    #  将Flask应用与SQLAlchemy实例绑定
    db.init_app(app)

    # 初始化数据库迁移工具（关联app和db）
    migrate.init_app(app, db)

    # 初始化邮件插件
    mail.init_app(app)

    # 初始化JWT认证扩展（关联Flask应用）
    JWTManager(app)

    #  注册蓝图（把路由挂载到应用上）
    from app.routes.main import main
    from app.routes.auth.auth import auth
    from app.routes.video_source import video_bp
    from app.routes.camera import camera_bp
    from app.routes.model import model_bp
    from app.routes.feedback import feedback_bp
    from app.routes.feedback.admin_feedback import admin_feedback_bp
    from app.routes.config import config_bp
    from app.routes.alert_record import alert_record_bp
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(video_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(admin_feedback_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(alert_record_bp)

    # 确保上传目录存在
    import os
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except Exception as e:
        print(f"Error creating upload folder: {e}")

    return app
