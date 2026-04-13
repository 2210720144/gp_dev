from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models.camera import Camera, UserCameraPermission
from app.models.video import Video
from app.models.user import User, UserRole
from app.models import db
from . import camera_bp


@camera_bp.route('/add', methods=['POST'])
@jwt_required()
def add_camera():
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    data = request.get_json()
    camera_name = data.get('camera_name')
    video_id = data.get('video_id')

    if not camera_name:
        return jsonify({'code': 400, 'msg': '参数不完整'}), 400
        
    # 如果提供了视频源ID，则进行检查
    if video_id:
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'code': 404, 'msg': '视频源不存在'}), 404
            
        if video.camera_id and video.camera_id != 0:
             return jsonify({'code': 400, 'msg': '该视频源已被其他摄像头绑定'}), 400

    current_user_id = get_jwt_identity()
    
    try:
        # 创建摄像头
        new_camera = Camera(
            camera_name=camera_name,
            video_id=str(video_id) if video_id else None,
            created_by=int(current_user_id)
        )
        db.session.add(new_camera)
        db.session.flush() # 获取自增ID
        
        # 如果绑定了视频源，更新视频源状态
        if video_id:
            video = db.session.get(Video, video_id) # 重新获取对象以防脱离会话
            video.camera_id = new_camera.camera_id
            video.config_status = '已配置'
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': '添加成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@camera_bp.route('/list', methods=['GET'])
@jwt_required()
def get_camera_list():
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    cameras = Camera.query.order_by(Camera.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'msg': 'Success',
        'data': [c.to_dict() for c in cameras]
    })


@camera_bp.route('/video-sources/available', methods=['GET'])
@jwt_required()
def get_available_video_sources():
    """获取未绑定的视频源"""
    # 筛选 camera_id 为空 (NULL) 或 0 的视频源
    videos = Video.query.filter((Video.camera_id == None) | (Video.camera_id == 0)).all()

    return jsonify({
        'code': 200,
        'msg': 'Success',
        'data': [{'video_id': v.video_id, 'video_name': v.video_name} for v in videos]
    })


@camera_bp.route('/users/ordinary', methods=['GET'])
@jwt_required()
def get_ordinary_users():
    """获取所有普通用户"""
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    users = User.query.filter_by(role=UserRole.USER).all()
    return jsonify({
        'code': 200,
        'msg': 'Success',
        'data': [{'user_id': u.user_id, 'username': u.username} for u in users]
    })


@camera_bp.route('/update', methods=['POST'])
@jwt_required()
def update_camera():
    """更新摄像头配置"""
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    data = request.get_json()
    camera_id = data.get('camera_id')
    camera_name = data.get('camera_name')
    video_id = data.get('video_id')
    authorized_user_ids = data.get('authorized_user_ids', []) # List of user_ids

    if not camera_id or not camera_name:
        return jsonify({'code': 400, 'msg': '参数不完整'}), 400

    camera = db.session.get(Camera, camera_id)
    if not camera:
        return jsonify({'code': 404, 'msg': '摄像头不存在'}), 404

    try:
        # 1. Update Camera Basic Info
        camera.camera_name = camera_name

        # 2. Update Video Source Binding
        # Check if video_id changed
        old_video_id = str(camera.video_id) if camera.video_id else None
        new_video_id = str(video_id) if video_id else None

        if old_video_id != new_video_id:
            # Unbind old video if exists
            if old_video_id:
                old_video = db.session.get(Video, int(old_video_id))
                if old_video:
                    old_video.camera_id = 0 # Or None, depending on schema, but code uses 0 in some places. Let's use 0 based on add_camera logic check
                    old_video.config_status = '未配置'
            
            # Bind new video if exists
            if new_video_id:
                new_video = db.session.get(Video, int(new_video_id))
                if not new_video:
                     return jsonify({'code': 404, 'msg': '新视频源不存在'}), 404
                
                # Check if new video is already bound to ANOTHER camera (not this one)
                if new_video.camera_id and new_video.camera_id != 0 and new_video.camera_id != camera.camera_id:
                    return jsonify({'code': 400, 'msg': '该视频源已被其他摄像头绑定'}), 400
                
                new_video.camera_id = camera.camera_id
                new_video.config_status = '已配置'
            
            camera.video_id = new_video_id

        # 3. Update Authorized Users
        # Get current permissions
        current_permissions = UserCameraPermission.query.filter_by(camera_id=camera.camera_id).all()
        current_user_ids = {p.user_id for p in current_permissions}
        new_user_ids = set(int(uid) for uid in authorized_user_ids)

        # Users to add
        to_add = new_user_ids - current_user_ids
        for uid in to_add:
            # Verify user exists and is ordinary user (optional but safer)
            user = db.session.get(User, uid)
            if user and user.role == UserRole.USER:
                new_perm = UserCameraPermission(user_id=uid, camera_id=camera.camera_id)
                db.session.add(new_perm)

        # Users to remove
        to_remove = current_user_ids - new_user_ids
        if to_remove:
            UserCameraPermission.query.filter(
                UserCameraPermission.camera_id == camera.camera_id,
                UserCameraPermission.user_id.in_(to_remove)
            ).delete(synchronize_session=False)

        db.session.commit()
        return jsonify({'code': 200, 'msg': '配置更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@camera_bp.route('/<int:camera_id>', methods=['GET'])
@jwt_required()
def get_camera_detail(camera_id):
    """获取摄像头详情"""
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    camera = db.session.get(Camera, camera_id)
    if not camera:
        return jsonify({'code': 404, 'msg': '摄像头不存在'}), 404
    
    # 获取视频源信息
    video_info = "未配置"
    if camera.video_id:
        video = db.session.get(Video, int(camera.video_id))
        if video:
            video_info = f"ID:{video.video_id} - {video.video_name or '未命名'}"
    
    # 获取授权用户
    permissions = db.session.query(User).join(
        UserCameraPermission, User.user_id == UserCameraPermission.user_id
    ).filter(
        UserCameraPermission.camera_id == camera_id
    ).all()
    
    authorized_users_list = [f"{u.username}(ID:{u.user_id})" for u in permissions]
    authorized_users_str = "，".join(authorized_users_list) if authorized_users_list else "未授权"
    authorized_user_ids = [u.user_id for u in permissions]

    data = camera.to_dict()
    data['video_source_info'] = video_info
    data['authorized_users_info'] = authorized_users_str
    data['authorized_user_ids'] = authorized_user_ids
    
    return jsonify({
        'code': 200,
        'msg': 'Success',
        'data': data
    })


@camera_bp.route('/delete/<int:camera_id>', methods=['DELETE'])
@jwt_required()
def delete_camera(camera_id):
    """删除摄像头"""
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': '权限不足'}), 403
    
    camera = db.session.get(Camera, camera_id)
    if not camera:
        return jsonify({'code': 404, 'msg': '摄像头不存在'}), 404
    
    try:
        # 1. 解绑视频源
        if camera.video_id:
             video = db.session.get(Video, int(camera.video_id))
             if video:
                 video.camera_id = 0 
                 video.config_status = '未配置'
        
        # 2. 删除权限记录
        UserCameraPermission.query.filter_by(camera_id=camera_id).delete()
        
        # 3. 删除摄像头
        db.session.delete(camera)
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500