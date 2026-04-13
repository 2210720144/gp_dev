from flask import Blueprint

# 定义蓝图，设置统一的URL前缀
video_bp = Blueprint('video_bp', __name__, url_prefix='/api/video-source')

# 导入子模块，确保路由被注册
# 注意：这里使用相对导入，避免循环引用问题
from . import upload_video
from . import manage_video