import os

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app.models import db
from app.models.user import User, UserRole, UserStatus, VerificationCode
from app.models.alert_record import AlertRecord
from app.models.camera import Camera, UserCameraPermission
from app.models.user_feedback import UserFeedback
from app.models.video import Video
from app.models.yolo_model import YoloModel
import random
from datetime import datetime, timedelta
from app.utils.email import send_verification_email

auth = Blueprint('auth', __name__)


# --- Helper Functions ---
def success_response(data=None, msg="操作成功"):
    return jsonify({"code": 200, "msg": msg, "data": data}), 200


def error_response(msg="操作失败", code=400):
    return jsonify({"code": code, "msg": msg, "data": None}), code


def _delete_feedback_attachments(feedbacks):
    base_dir = current_app.config.get('BASE_DIR')
    if not base_dir:
        return

    for feedback in feedbacks:
        if not feedback.attachment_url:
            continue

        file_path = os.path.join(base_dir, feedback.attachment_url)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as exc:
                current_app.logger.warning("Failed to delete feedback attachment %s: %s", file_path, exc)


# --- View Routes (Frontend) ---
@auth.route('/auth')
def login_page():
    # Render the login/register page
    return render_template('auth.html')


# --- API接口映射，以下是后端逻辑 ---

# --- 普通用户路由 ---

# 发送验证码
@auth.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    email = data.get('email')  # 获取表单中的邮箱
    usage = data.get('usage')  # 用途：register (default), change_password

    if not email:  # 如果用户没有输入邮箱
        return error_response("请输入邮箱")

    # 检查邮箱
    user = User.query.filter_by(email=email).first()
    
    if usage == 'change_password':
        # 修改密码时，要求邮箱必须存在（或者是当前登录用户的邮箱，这里简单校验存在即可）
        # 如果是已登录用户修改密码，通常前端会自动填入当前邮箱
        if not user:
            return error_response("该邮箱未注册")
    else:
        # 默认注册场景，要求邮箱不存在
        if user:
            return error_response("该邮箱已被注册")

    # 生成6位数字
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # 验证时间，设置为5分钟
    expires_at = datetime.now() + timedelta(minutes=5)

    # 清理数据库表该邮箱的旧验证码
    VerificationCode.query.filter_by(email=email).delete()

    # 数据库表中新建验证码记录
    ver_code = VerificationCode(email=email, code=code, expires_at=expires_at)
    db.session.add(ver_code)
    db.session.commit()

    # 发送邮件
    send_verification_email(email, code)

    return success_response(msg="验证码已发送，请查收")


# 注册
@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    code = data.get('code')  # Get verification code

    if not all([username, password, email, code]):
        return error_response("参数不完整")

    # Verify Code
    ver_code = VerificationCode.query.filter_by(email=email, code=code, is_used=False).first()

    if not ver_code:
        return error_response("验证码错误或不存在")

    if datetime.now() > ver_code.expires_at:
        return error_response("验证码已过期，请重新获取")

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return error_response("用户名或邮箱已存在")

    new_user = User(
        username=username,
        password=password,  # Setter will hash it
        email=email,
        role=UserRole.USER,
        status=UserStatus.PENDING  # Default pending
    )

    # Mark code as used
    ver_code.is_used = True

    db.session.add(new_user)
    db.session.commit()

    return success_response(msg="注册申请提交成功，请等待管理员审核")


# 登录
@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    login_id = data.get('login_id')  # 用户名 or 邮箱
    password = data.get('password')

    if not login_id or not password:
        return error_response("请输入用户名/邮箱和密码")

    user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

    if not user or not user.verify_password(password):
        return error_response("账号或密码错误", 401)

    if user.status != UserStatus.ACTIVE:
        return error_response(f"账号状态异常: {user.status.value}", 403)

    # Generate JWT
    access_token = create_access_token(identity=str(user.user_id), additional_claims={"role": user.role.name})

    return success_response(data={
        "token": access_token,
        "user": user.to_dict()
    }, msg="登录成功")


# 修改密码
@auth.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)

    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    code = data.get('code')

    # 方式1：使用旧密码验证
    if old_password:
        if not user.verify_password(old_password):
            return error_response("旧密码错误")
            
    # 方式2：使用验证码验证
    elif code:
        ver_code = VerificationCode.query.filter_by(email=user.email, code=code, is_used=False).first()
        if not ver_code:
            return error_response("验证码错误或不存在")
        if datetime.now() > ver_code.expires_at:
            return error_response("验证码已过期，请重新获取")
        # 验证通过，标记为已使用
        ver_code.is_used = True
        
    else:
        return error_response("缺少验证凭据（旧密码或验证码）")

    user.password = new_password
    db.session.commit()
    return success_response(msg="密码修改成功")


# 获取当前登录用户信息（用于验证Token有效性）
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return error_response("用户不存在", 404)
    
    return success_response(data=user.to_dict())


# --- 管理员路由 ---

@auth.route('/admin/user/delete/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    claims = get_jwt()
    current_role_name = claims.get('role')
    
    # Check if user exists
    user = db.session.get(User, user_id)
    if not user:
        return error_response("用户不存在", 404)

    # Permission Logic
    if current_role_name == UserRole.ROOT.name:
        # Root can delete anyone
        pass
    elif current_role_name == UserRole.ADMIN.name:
        if user.role != UserRole.USER:
             return error_response("权限不足：管理员只能注销普通用户", 403)
    else:
        return error_response("权限不足", 403)

    try:
        # 删除权限
        user_feedbacks = UserFeedback.query.filter_by(user_id=user_id).all()
        _delete_feedback_attachments(user_feedbacks)

        VerificationCode.query.filter_by(email=user.email).delete()
        UserCameraPermission.query.filter_by(user_id=user_id).delete()

        AlertRecord.query.filter_by(user_id=user_id).delete()
        UserFeedback.query.filter_by(user_id=user_id).delete()

        UserFeedback.query.filter_by(replied_by=user_id).update(
            {UserFeedback.replied_by: None},
            synchronize_session=False
        )
        Camera.query.filter_by(created_by=user_id).update(
            {Camera.created_by: None},
            synchronize_session=False
        )
        Video.query.filter_by(upload_by=user_id).update(
            {Video.upload_by: None},
            synchronize_session=False
        )
        YoloModel.query.filter_by(upload_by=user_id).update(
            {YoloModel.upload_by: None},
            synchronize_session=False
        )
        
        db.session.flush()
        db.session.delete(user)
        db.session.commit()
        return success_response(msg="用户已注销")
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# 审核用户（通过/拒绝）
@auth.route('/admin/audit', methods=['POST'])
@jwt_required()
def audit_user():
    claims = get_jwt()
    if claims['role'] not in [UserRole.ADMIN.name, UserRole.ROOT.name]:
        return error_response("权限不足", 403)

    data = request.get_json()
    target_user_id = data.get('user_id')
    action = data.get('action')  # 'approve' or 'reject'

    user = db.session.get(User, target_user_id)
    if not user:
        return error_response("用户不存在", 404)

    if user.status != UserStatus.PENDING:
        return error_response("该用户无需审核")

    if action == 'approve':
        user.status = UserStatus.ACTIVE
        msg = "审核通过"
    elif action == 'reject':
        user.status = UserStatus.DELETED  # Or some other status for rejected
        msg = "审核驳回"
    else:
        return error_response("无效的操作")

    db.session.commit()
    return success_response(msg=msg)


# 获取用户列表
@auth.route('/admin/user-list', methods=['GET'])
@jwt_required()
def get_user_list():
    claims = get_jwt()
    if claims['role'] not in [UserRole.ADMIN.name, UserRole.ROOT.name]:
        return error_response("权限不足", 403)
    
    users = User.query.order_by(User.created_at.desc()).all()
    return success_response(data=[user.to_dict() for user in users])


# 管理普通用户
@auth.route('/admin/manage-user', methods=['POST'])
@jwt_required()
def manage_user():
    claims = get_jwt()
    if claims['role'] not in [UserRole.ADMIN.name, UserRole.ROOT.name]:
        return error_response("权限不足", 403)

    data = request.get_json()
    target_user_id = data.get('user_id')
    action = data.get('action')  # 'disable', 'enable', 'delete'

    user = db.session.get(User, target_user_id)
    if not user:
        return error_response("用户不存在", 404)

    # Prevent admin from modifying other admins (unless root)
    if user.role in [UserRole.ADMIN, UserRole.ROOT] and claims['role'] != UserRole.ROOT.name:
        return error_response("无法操作该级别的用户", 403)

    if action == 'disable':
        user.status = UserStatus.DISABLED
    elif action == 'enable':
        user.status = UserStatus.ACTIVE
    elif action == 'delete':
        user.status = UserStatus.DELETED
    else:
        return error_response("无效的操作")

    db.session.commit()
    return success_response(msg="操作成功")


# 分配摄像头权限
@auth.route('/admin/assign-camera', methods=['POST'])
@jwt_required()
def assign_camera():
    claims = get_jwt()
    if claims['role'] not in [UserRole.ADMIN.name, UserRole.ROOT.name]:
        return error_response("权限不足", 403)

    data = request.get_json()
    user_id = data.get('user_id')
    camera_ids = data.get('camera_ids')  # List of int

    if not isinstance(camera_ids, list):
        return error_response("摄像头ID列表格式错误")

    # Clear existing permissions? Or add? Assuming replace or add. Let's append unique.
    # Simple strategy: Add if not exists
    for cam_id in camera_ids:
        exists = UserCameraPermission.query.filter_by(user_id=user_id, camera_id=cam_id).first()
        if not exists:
            perm = UserCameraPermission(user_id=user_id, camera_id=cam_id)
            db.session.add(perm)

    db.session.commit()
    return success_response(msg="权限分配成功")


# --- 超级管理员路由 ---

# 管理员创建账号（通用接口）
@auth.route('/admin/create-account', methods=['POST'])
@jwt_required()
def admin_create_account_api():
    claims = get_jwt()
    current_role = claims['role']
    
    if current_role not in [UserRole.ADMIN.name, UserRole.ROOT.name]:
        return error_response("权限不足", 403)

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    is_admin = data.get('is_admin') # 'yes' or 'no'

    if not all([username, password, email]):
        return error_response("参数不完整")

    # Determine target role
    target_role = UserRole.USER
    if is_admin == 'yes':
        if current_role != UserRole.ROOT.name:
            return error_response("仅超级管理员可创建管理员账号", 403)
        target_role = UserRole.ADMIN
    
    # Check duplicates
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return error_response("用户名或邮箱已存在")

    new_user = User(
        username=username,
        password=password,
        email=email,
        role=target_role,
        status=UserStatus.ACTIVE # Admin created accounts are active by default
    )
    db.session.add(new_user)
    db.session.commit()
    
    role_str = "管理员" if target_role == UserRole.ADMIN else "普通用户"
    return success_response(msg=f"{role_str}账号创建成功")

# 创建管理员 (Legacy, kept for reference or specific root usage)
@auth.route('/root/create-admin', methods=['POST'])
@jwt_required()
def create_admin():
    claims = get_jwt()
    if claims['role'] != UserRole.ROOT.name:
        return error_response("仅超级管理员可操作", 403)

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return error_response("管理员用户名或邮箱已存在")

    new_admin = User(
        username=username,
        password=password,
        email=email,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db.session.add(new_admin)
    db.session.commit()
    return success_response(msg="管理员创建成功")
