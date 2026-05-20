from flask import Response, current_app, jsonify, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

import cv2
import time

from app.models import db
from app.models.camera import Camera, UserCameraPermission
from app.models.video import Video
from app.models.violation_event import ViolationEvent
from app.services.stream_service import stream_service

from . import camera_bp


def gen_frames(camera_id):
    """持续输出指定摄像头的处理后视频帧。"""
    app = current_app._get_current_object()
    stream = stream_service.start_stream(app, camera_id)
    if not stream:
        return

    while True:
        processed_frame = stream.get_frame()
        if processed_frame is None:
            time.sleep(0.1)
            continue

        ret, buffer = cv2.imencode(".jpg", processed_frame)
        if not ret:
            time.sleep(0.04)
            continue

        frame = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )

        time.sleep(0.04)


@camera_bp.route("/stream/<int:camera_id>")
def video_feed(camera_id):
    """实时视频流接口。"""
    return Response(
        stream_with_context(gen_frames(camera_id)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/my-list", methods=["GET"])
@jwt_required()
def get_my_cameras():
    """获取当前用户有权限查看的摄像头列表。"""
    current_user_id = get_jwt_identity()
    permissions = UserCameraPermission.query.filter_by(user_id=current_user_id).all()
    camera_ids = [permission.camera_id for permission in permissions]

    if not camera_ids:
        return jsonify({"code": 200, "msg": "Success", "data": []})

    cameras = Camera.query.filter(Camera.camera_id.in_(camera_ids)).all()

    result = []
    for camera in cameras:
        camera_data = {
            "camera_id": camera.camera_id,
            "camera_name": camera.camera_name,
            "video_url": "",
            "location": "未知区域",
            "video_name": "",
        }

        if camera.video_id:
            video = db.session.get(Video, int(camera.video_id))
            if video:
                url = video.video_url
                if not url.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                    url = f"/uploads/{url}"

                camera_data["video_url"] = url
                camera_data["location"] = video.location or video.video_name or "未知区域"
                camera_data["video_name"] = video.video_name

        result.append(camera_data)

    return jsonify({"code": 200, "msg": "Success", "data": result})


@camera_bp.route("/status/<int:camera_id>", methods=["GET"])
@jwt_required()
def get_camera_status(camera_id):
    """获取单个摄像头的当前检测状态。"""
    from app.services.detection_service import detection_service

    status = detection_service.get_camera_status(camera_id)
    return jsonify({"code": 200, "msg": "Success", "data": status})


@camera_bp.route("/alerts", methods=["GET"])
@jwt_required()
def get_recent_alerts():
    """获取当前用户可见的违停告警摘要。"""
    current_user_id = get_jwt_identity()
    permissions = UserCameraPermission.query.filter_by(user_id=current_user_id).all()
    camera_ids = [permission.camera_id for permission in permissions]

    if not camera_ids:
        return jsonify({"code": 200, "msg": "Success", "data": []})

    active_events = (
        db.session.query(ViolationEvent, Video)
        .join(Camera, ViolationEvent.camera_id == Camera.camera_id)
        .outerjoin(Video, Camera.video_id == Video.video_id)
        .filter(ViolationEvent.camera_id.in_(camera_ids))
        .filter(ViolationEvent.end_time == None)
        .order_by(ViolationEvent.start_time.desc())
        .all()
    )

    # 每个摄像头只保留一条侧边栏告警。
    # 当同一摄像头出现新的违停时，只更新汇总数量，不再保留旧的逐条事件提示。
    camera_alerts = {}
    for event, video in active_events:
        location = "未知区域"
        if video:
            location = video.location or video.video_name or "未知区域"

        if event.camera_id not in camera_alerts:
            camera_alerts[event.camera_id] = {
                "latest_time": event.start_time,
                "location": location,
                "count": 0,
            }

        camera_alerts[event.camera_id]["count"] += 1

    sorted_alerts = sorted(
        camera_alerts.values(),
        key=lambda item: item["latest_time"],
        reverse=True,
    )

    data = []
    for alert in sorted_alerts[:20]:
        data.append({
            "time": alert["latest_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "location": alert["location"],
            "msg": f"{alert['location']}：发现 {alert['count']} 辆单车违规停放",
        })

    return jsonify({"code": 200, "msg": "Success", "data": data})
