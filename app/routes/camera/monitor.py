from flask import jsonify, Response, stream_with_context, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.camera import Camera, UserCameraPermission
from app.models.video import Video
from app.models.violation_event import ViolationEvent
from app.models import db
from sqlalchemy import or_
from . import camera_bp
import cv2
import os
import time
from app.services.stream_service import stream_service

# -------------------------------------------------------------------------
# 监控与查看相关路由
# -------------------------------------------------------------------------
# 这里的路由主要面向普通用户或监控大屏，专注于数据的"读取"与"展示"。
# YOLO 目标检测的实时流、告警推送、轨迹跟踪等接口都在此扩展。
# -------------------------------------------------------------------------

def gen_frames(camera_id):
    """调用app/services/stream_service.py里面stream_service实例"""
    # 获取真实app对象传给线程
    app = current_app._get_current_object()
    
    # 启动或获取后台流
    stream = stream_service.start_stream(app, camera_id)
    if not stream:
        return

    while True:
        # 获取最新处理过的帧
        processed_frame = stream.get_frame()
        
        if processed_frame is None:
            # 等待流初始化
            time.sleep(0.1)
            continue
            
        # 将处理后的帧转化为可播放的格式，ret为bool类型，标记编码是否成功，buffer才是压缩编码后的数据
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame = buffer.tobytes()  # 转为二进制

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # 控制发送给客户端的帧率 (防止循环过快)
        # 这里的休眠只影响HTTP传输频率，不影响后台检测逻辑
        time.sleep(0.04) # 约 25 FPS

@camera_bp.route('/stream/<int:camera_id>')
def video_feed(camera_id):
    """视频流路由"""
    return Response(stream_with_context(gen_frames(camera_id)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@camera_bp.route('/my-list', methods=['GET'])
@jwt_required()
def get_my_cameras():
    """获取当前用户授权的摄像头列表"""
    current_user_id = get_jwt_identity()
    
    # 查当前用户的摄像头权限
    permissions = UserCameraPermission.query.filter_by(user_id=current_user_id).all()
    camera_ids = [p.camera_id for p in permissions]
    
    if not camera_ids:
        return jsonify({'code': 200, 'msg': 'Success', 'data': []})
        
    # 查摄像头
    cameras = Camera.query.filter(Camera.camera_id.in_(camera_ids)).all()
    
    result = []
    for cam in cameras:
        cam_data = {
            'camera_id': cam.camera_id,
            'camera_name': cam.camera_name,
            'video_url': '',
            'location': '未知区域',
            'video_name': ''
        }
        
        if cam.video_id:
            video = db.session.get(Video, int(cam.video_id))
            if video:
                # 处理视频URL
                # 如果是网络流地址（http/rtsp/rtmp等），直接使用
                # 如果是本地文件名，则拼接上传目录路径
                url = video.video_url
                if not url.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
                    url = f"/uploads/{url}"
                
                cam_data['video_url'] = url
                cam_data['location'] = video.location if video.location else (video.video_name or '未知区域')
                cam_data['video_name'] = video.video_name
        
        result.append(cam_data)
        
    return jsonify({'code': 200, 'msg': 'Success', 'data': result})


@camera_bp.route('/status/<int:camera_id>', methods=['GET'])
@jwt_required()
def get_camera_status(camera_id):
    """获取摄像头当前的检测状态（单车数量、违停数量）"""
    from app.services.detection_service import detection_service
    status = detection_service.get_camera_status(camera_id)
    return jsonify({'code': 200, 'msg': 'Success', 'data': status})


@camera_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_recent_alerts():
    """获取最新的违停告警记录"""
    current_user_id = get_jwt_identity()
    
    # 1. 获取用户权限内的摄像头
    permissions = UserCameraPermission.query.filter_by(user_id=current_user_id).all()
    camera_ids = [p.camera_id for p in permissions]
    
    if not camera_ids:
        return jsonify({'code': 200, 'msg': 'Success', 'data': []})

    # 2. 查询最近的违停事件（关联查询区域信息）
    # Limit 20
    results = (db.session.query(ViolationEvent, Video)
               .join(Camera, ViolationEvent.camera_id == Camera.camera_id)
               .outerjoin(Video, Camera.video_id == Video.video_id)
               .filter(ViolationEvent.camera_id.in_(camera_ids))
               .filter(ViolationEvent.end_time == None) # 仅显示未结束的违停
               .order_by(ViolationEvent.start_time.desc())
               .limit(20)
               .all())
    
    data = []
    seen_keys = set() # 用集合的特性删除重复的跟踪

    for event, video in results:
        # 将时间格式转化为字符串
        time_str = event.start_time.strftime('%Y-%m-%d %H:%M:%S')

        # 根据时间+摄像头ID（位置）进行重复数据删除
        # 如果同一台相机在同一秒有多个事件，则只显示一个
        key = (time_str, event.camera_id)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        # 统计该时刻（start_time）同摄像头下的正在违停车辆数
        # 条件：开始时间 <= 当前事件时间 且 (结束时间为空 或 结束时间 > 当前事件时间)
        active_count = db.session.query(ViolationEvent).filter(
            ViolationEvent.camera_id == event.camera_id,
            ViolationEvent.start_time <= event.start_time,
            or_(ViolationEvent.end_time == None, ViolationEvent.end_time > event.start_time)
        ).count()

        location = "未知区域"
        if video:
            location = video.location if video.location else (video.video_name or "未知区域")
            
        data.append({
            'time': event.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'location': location,
            'msg': f"{location}：发现{active_count}辆单车违停"
        })
        
    return jsonify({'code': 200, 'msg': 'Success', 'data': data})


