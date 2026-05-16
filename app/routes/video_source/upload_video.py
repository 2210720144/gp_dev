import os
import uuid
from urllib.parse import urlparse

import cv2
from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.models import db
from app.models.video import Video

from . import video_bp


ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'flv', 'mkv', 'wmv'}
SUPPORTED_STREAM_SCHEMES = {'rtsp', 'rtmp', 'http', 'https'}
STREAM_OPEN_TIMEOUT_MS = 5000
STREAM_READ_TIMEOUT_MS = 5000


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_supported_stream_url(video_url):
    parsed = urlparse(video_url)
    return parsed.scheme.lower() in SUPPORTED_STREAM_SCHEMES


def guess_stream_format(video_url):
    url_lower = video_url.lower()
    if url_lower.startswith('rtsp://'):
        return 'RTSP'
    if url_lower.startswith('rtmp://'):
        return 'RTMP'
    if '.m3u8' in url_lower:
        return 'HLS'
    if '.flv' in url_lower:
        return 'FLV'
    return 'STREAM'


def open_stream_capture(video_url):
    params = [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, STREAM_OPEN_TIMEOUT_MS,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC, STREAM_READ_TIMEOUT_MS,
    ]

    for backend in (cv2.CAP_FFMPEG, cv2.CAP_ANY):
        capture = None
        try:
            capture = cv2.VideoCapture(video_url, backend, params)
        except TypeError:
            capture = cv2.VideoCapture(video_url, backend)
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, STREAM_OPEN_TIMEOUT_MS)
            capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, STREAM_READ_TIMEOUT_MS)
        except Exception:
            capture = cv2.VideoCapture(video_url)
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, STREAM_OPEN_TIMEOUT_MS)
            capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, STREAM_READ_TIMEOUT_MS)

        if capture is not None and capture.isOpened():
            return capture

        if capture is not None:
            capture.release()

    return cv2.VideoCapture()


def probe_stream(video_url):
    capture = None
    try:
        capture = open_stream_capture(video_url)
        if capture is None or not capture.isOpened():
            return {
                'success': False,
                'msg': '无法打开视频流，请检查地址、账号密码或网络连通性'
            }

        frame = None
        read_ok = False
        for _ in range(3):
            read_ok, frame = capture.read()
            if read_ok and frame is not None:
                break

        if not read_ok or frame is None:
            return {
                'success': False,
                'msg': '已连接到视频流，但未读取到有效画面'
            }

        fps = capture.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or fps > 240:
            fps = None

        height, width = frame.shape[:2]
        return {
            'success': True,
            'msg': '视频流连接成功',
            'data': {
                'format': guess_stream_format(video_url),
                'width': int(width),
                'height': int(height),
                'fps': round(float(fps), 2) if fps else None,
            }
        }
    except Exception as exc:
        current_app.logger.exception('Failed to probe stream: %s', video_url)
        return {
            'success': False,
            'msg': f'测试失败：{exc}'
        }
    finally:
        if capture is not None:
            capture.release()


@video_bp.route('/test', methods=['POST'])
@jwt_required()
def test_video_source():
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403

    data = request.get_json(silent=True) or {}
    video_url = (data.get('url') or '').strip()
    if not video_url:
        return jsonify({'code': 400, 'msg': '请输入视频流地址'}), 400

    if not is_supported_stream_url(video_url):
        return jsonify({
            'code': 400,
            'msg': '仅支持 RTSP、RTMP、HTTP、HTTPS 视频流地址'
        }), 400

    result = probe_stream(video_url)
    if result['success']:
        return jsonify({
            'code': 200,
            'msg': result['msg'],
            'data': result.get('data', {})
        })

    return jsonify({'code': 400, 'msg': result['msg']}), 400


@video_bp.route('/add', methods=['POST'])
@jwt_required()
def add_video_source():
    """
    添加视频源接口
    支持两种模式：
    1. 视频流 URL
    2. 本地文件上传
    """
    claims = get_jwt()
    if claims.get('role') not in ['ADMIN', 'ROOT']:
        return jsonify({'code': 403, 'msg': 'Permission denied'}), 403

    current_user_id = get_jwt_identity()

    source_type = request.form.get('source_type')
    video_url = request.form.get('url')
    area = request.form.get('area')
    name = request.form.get('name')

    if not source_type:
        return jsonify({'code': 400, 'msg': 'Missing source type'}), 400

    video_format = 'UNKNOWN'
    final_video_url = ''

    if source_type == 'stream':
        if not video_url:
            return jsonify({'code': 400, 'msg': 'Video URL is required for stream type'}), 400

        final_video_url = video_url
        video_format = guess_stream_format(video_url)

    elif source_type == 'file':
        if 'video_file' not in request.files:
            return jsonify({'code': 400, 'msg': 'No file part'}), 400

        file = request.files['video_file']

        if file.filename == '':
            return jsonify({'code': 400, 'msg': 'No selected file'}), 400

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            unique_filename = f'{uuid.uuid4().hex}.{file_ext}'

            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            final_video_url = unique_filename
            video_format = file_ext.upper()
        else:
            return jsonify({'code': 400, 'msg': 'File type not allowed'}), 400

    else:
        return jsonify({'code': 400, 'msg': 'Invalid source type'}), 400

    try:
        new_video = Video(
            video_name=name,
            video_url=final_video_url,
            location=area,
            format=video_format,
            upload_by=current_user_id,
            config_status='未配置'
        )

        db.session.add(new_video)
        db.session.commit()

        return jsonify({
            'code': 200,
            'msg': 'Video source added successfully',
            'data': new_video.to_dict()
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(exc)}), 500
