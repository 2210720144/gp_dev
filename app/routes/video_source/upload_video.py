import os
import uuid
from flask import request, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from app.models import db
from app.models.video import Video
# 从当前包导入蓝图对象
from . import video_bp

# 允许上传的视频扩展名
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'flv', 'mkv', 'wmv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@video_bp.route('/add', methods=['POST'])
@jwt_required()
def add_video_source():
    """
    添加视频源接口
    支持两种模式：
    1. 视频流URL (stream)
    2. 本地文件上传 (file)
    """
    # 鉴权：检查是否为管理员
    claims = get_jwt()
    # JWT中存储的role是枚举名称（大写）：ADMIN, ROOT
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403

    current_user_id = get_jwt_identity()

    # 获取表单数据
    source_type = request.form.get('source_type')
    video_url = request.form.get('url')
    area = request.form.get('area')
    name = request.form.get('name')  # 获取视频源名称

    if not source_type:
        return jsonify({'code': 400, 'msg': 'Missing source type'}), 400

    video_format = 'UNKNOWN'
    final_video_url = ''

    if source_type == 'stream':
        if not video_url:
            return jsonify({'code': 400, 'msg': 'Video URL is required for stream type'}), 400

        final_video_url = video_url

        # 简单推断格式
        if 'rtsp://' in video_url:
            video_format = 'RTSP'
        elif 'rtmp://' in video_url:
            video_format = 'RTMP'
        elif '.m3u8' in video_url:
            video_format = 'HLS'
        elif '.flv' in video_url:
            video_format = 'FLV'
        else:
            video_format = 'STREAM'

    elif source_type == 'file':
        if 'video_file' not in request.files:
            return jsonify({'code': 400, 'msg': 'No file part'}), 400

        file = request.files['video_file']

        if file.filename == '':
            return jsonify({'code': 400, 'msg': 'No selected file'}), 400

        if file and allowed_file(file.filename):
            # 生成安全的文件名，防止重名
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"

            # 确保上传目录存在
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # 保存文件
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            # 存储文件名，前端可通过静态文件服务访问
            final_video_url = unique_filename
            video_format = file_ext.upper()
        else:
            return jsonify({'code': 400, 'msg': 'File type not allowed'}), 400

    else:
        return jsonify({'code': 400, 'msg': 'Invalid source type'}), 400

 # 创建数据库记录
    try:
        new_video = Video(
            video_name=name,
            video_url=final_video_url,
            location=area,
            format=video_format,
            upload_by=current_user_id,
            config_status='未配置'
        )
        # 如果有name字段，虽然Model定义里没写，但如果后续加了字段可以使用
        # 目前根据您提供的Model代码，Video表似乎没有name字段？
        # 如果需要存储名称，建议在Video模型中添加 name 字段。
        # 暂时只存现有字段。

        db.session.add(new_video)
        db.session.commit()

        return jsonify({
            'code': 200,
            'msg': 'Video source added successfully',
            'data': new_video.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500