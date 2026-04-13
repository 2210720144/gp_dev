from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt
from app.models.video import Video
from app.models.camera import Camera
from app.models import db
from . import video_bp
import os


@video_bp.route('/list', methods=['GET'])
@jwt_required()
def get_video_list():
    """
    获取视频源列表
    """
    # 鉴权：检查是否为管理员
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403

    try:
        # 查询所有视频源，按上传时间倒序排列
        videos = Video.query.order_by(Video.upload_time.desc()).all()
        
        # 转换为字典列表
        video_list = [v.to_dict() for v in videos]

        return jsonify({
            'code': 200,
            'msg': 'Success',
            'data': video_list
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500

@video_bp.route('/update/<int:video_id>', methods=['POST'])
@jwt_required()
def update_video(video_id):
    """
    更新视频源信息 (仅限名称和区域)
    """
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
    try:
        video = db.session.get(Video, video_id)
        if not video:
             return jsonify({'code': 404, 'msg': 'Video not found'}), 404
             
        data = request.get_json()
        if 'video_name' in data:
            video.video_name = data['video_name']
        if 'location' in data:
            video.location = data['location']
            
        db.session.commit()
        return jsonify({'code': 200, 'msg': 'Updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500

@video_bp.route('/delete/<int:video_id>', methods=['DELETE'])
@jwt_required()
def delete_video(video_id):
    """
    删除视频源 (同时删除数据库记录和对应的本地文件)
    """
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
    try:
        video = db.session.get(Video, video_id)
        if not video:
             return jsonify({'code': 404, 'msg': 'Video not found'}), 404
             
        # 尝试删除本地文件
        # 注意：只有当 video_url 是文件名且存在于上传目录时才删除
        # 如果是 RTSP/RTMP 等网络流地址，则跳过文件删除
        if video.video_url:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path = os.path.join(upload_folder, video.video_url)
            
            # 判断是否为本地文件（简单判断：不是以协议开头的，且文件存在）
            is_local_file = not (video.video_url.startswith('http') or 
                                 video.video_url.startswith('rtsp') or 
                                 video.video_url.startswith('rtmp'))
                                 
            if is_local_file and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}")
                    # 即使文件删除失败（如权限问题），我们也继续删除数据库记录
                    # 或者您可以选择在这里返回错误，取决于业务需求。
                    # 这里选择继续，以免孤立数据导致无法删除。

        # 解绑关联的摄像头：将关联该视频源的摄像头的 video_id 置空
        # 这样前端页面上该摄像头就会显示“未配置”
        linked_cameras = Camera.query.filter_by(video_id=video_id).all()
        for cam in linked_cameras:
            cam.video_id = None
            
        db.session.delete(video)
        db.session.commit()
        return jsonify({'code': 200, 'msg': 'Deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500