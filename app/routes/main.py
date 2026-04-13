from flask import Blueprint, render_template, send_from_directory, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.camera import Camera
from app.models.user import User, UserRole, UserStatus
from app.models.violation_event import ViolationEvent
from app.models.alert_record import AlertRecord
from app.models.user_feedback import UserFeedback
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/admin')
def admin_index():
    return render_template('admin/index.html')

@main.route('/admin/create-account')
def admin_create_account():
    return render_template('admin/create_account.html')

@main.route('/admin/account-management')
def admin_account_management():
    return render_template('admin/account_management.html')

@main.route('/admin/profile')
def admin_profile():
    return render_template('admin/profile.html')

@main.route('/admin/video-source/add')
def admin_add_video_source():
    return render_template('admin/add_video_source.html')

@main.route('/admin/video-source/list')
def admin_video_source_list():
    return render_template('admin/video_source_list.html')

@main.route('/admin/camera-management')
def admin_camera_management():
    return render_template('admin/camera_list.html')

@main.route('/user/feedback')
def user_feedback_list():
    return render_template('user/feedback_list.html')

@main.route('/user/alert-list')
def user_alert_list():
    return render_template('user/alert_list.html')

@main.route('/admin/alert-list')
def admin_alert_list():
    return render_template('admin/alert_list.html')

@main.route('/admin/general-settings')
def admin_general_settings():
    return render_template('admin/general_settings.html')

@main.route('/admin/model-management')
def admin_model_management():
    return render_template('admin/model_management.html')

@main.route('/admin/feedback-management')
def admin_feedback_management():
    return render_template('admin/feedback_list.html')

@main.route('/api/user/alert-count', methods=['GET'])
@jwt_required()
def user_alert_count():
    current_user_id = get_jwt_identity()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count alert records for this user created today
    count = AlertRecord.query.filter(
        AlertRecord.user_id == current_user_id,
        AlertRecord.created_at >= today_start
    ).count()
    
    return jsonify({'code': 200, 'msg': 'success', 'data': {'count': count}})

@main.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    # 1. 摄像头统计
    # 配置了视频源(video_id不为空)为在线，否则为离线
    total_cameras = Camera.query.count()
    online_cameras = Camera.query.filter(Camera.video_id != None).count()
    offline_cameras = total_cameras - online_cameras

    # 2. 注册用户统计
    # 仅统计普通用户 (UserRole.USER)
    # 正常和禁用状态为"已审核"，待审核状态为"待审核"
    audited_users = User.query.filter(User.role == UserRole.USER, User.status.in_([UserStatus.ACTIVE, UserStatus.DISABLED])).count()
    pending_users = User.query.filter(User.role == UserRole.USER, User.status == UserStatus.PENDING).count()
    # 这里的 total_users 定义为 已审核 + 待审核
    total_users = audited_users + pending_users

    # 3. 用户反馈统计
    total_feedback = UserFeedback.query.count()
    pending_feedback = UserFeedback.query.filter_by(status='待处理').count()
    processed_feedback = UserFeedback.query.filter_by(status='已处理').count()

    # 4. 违停告警统计
    # 统计今日的违停事件
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_alerts = ViolationEvent.query.filter(ViolationEvent.start_time >= today_start).count()
    processed_alerts = ViolationEvent.query.filter(
        ViolationEvent.start_time >= today_start,
        ViolationEvent.end_time != None
    ).count()
    unprocessed_alerts = total_alerts - processed_alerts

    alert_stats = {
        'total': total_alerts,
        'unprocessed': unprocessed_alerts,
        'processed': processed_alerts
    }

    # 5. 趋势图数据 (近7天)
    trend_data = []
    trend_labels = []
    today = datetime.now().date()
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        count = ViolationEvent.query.filter(
            ViolationEvent.start_time >= start_dt,
            ViolationEvent.start_time <= end_dt
        ).count()
        
        trend_data.append(count)
        trend_labels.append(target_date.strftime('%m/%d'))

    # 6. 摄像头违停占比
    all_cameras = Camera.query.all()
    camera_share_data = []
    camera_share_labels = []
    
    for cam in all_cameras:
        count = ViolationEvent.query.filter(ViolationEvent.camera_id == cam.camera_id).count()
        camera_share_data.append(count)
        camera_share_labels.append(cam.camera_name)

    data = {
        'camera': {
            'total': total_cameras,
            'online': online_cameras,
            'offline': offline_cameras
        },
        'user': {
            'total': total_users,
            'audited': audited_users,
            'pending': pending_users
        },
        'feedback': {
            'total': total_feedback,
            'pending': pending_feedback,
            'processed': processed_feedback
        },
        'alert': alert_stats,
        'trend': {'labels': trend_labels, 'data': trend_data},
        'camera_share': {'labels': camera_share_labels, 'data': camera_share_data}
    }

    return jsonify({'code': 200, 'msg': 'success', 'data': data})

@main.route('/user')
def user_index():
    return render_template('user/index.html')

@main.route('/user/profile')
def user_profile():
    return render_template('user/profile.html')

# 路由：访问上传的视频文件
@main.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
