from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.feedback import feedback_bp
from app.services.feedback_service import FeedbackService

@feedback_bp.route('/list', methods=['GET'])
@jwt_required()
def get_feedback_list():
    """
    获取用户反馈列表接口
    参数:
    - year: 年份 (可选)
    - month: 月份 (可选, 'all' 或 '01'-'12')
    - show_all: 是否显示全部 (可选, 'true'/'false')
    """
    try:
        user_id = int(get_jwt_identity())
        
        # 获取查询参数
        year = request.args.get('year')
        month = request.args.get('month')
        show_all_param = request.args.get('show_all', 'false').lower()
        show_all = show_all_param == 'true'

        # 获取可用年份 (用于前端下拉框)
        available_years = FeedbackService.get_available_years(user_id)
        
        # 如果没有指定年份且没有勾选显示全部，默认使用最近的年份
        # 如果用户没有任何反馈，available_years 为空，则 year 保持 None
        if not show_all and not year and available_years:
            year = available_years[0]

        # 获取反馈列表
        feedbacks = FeedbackService.get_user_feedback_list(user_id, year, month, show_all)

        # 转换为字典列表
        feedback_list = [f.to_dict() for f in feedbacks]

        return jsonify({
            'code': 200,
            'msg': '获取成功',
            'data': {
                'list': feedback_list,
                'available_years': available_years,
                'current_filters': {
                    'year': year,
                    'month': month,
                    'show_all': show_all
                }
            }
        })
    except Exception as e:
        print(f"Error getting feedback list: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

from flask import request, jsonify, send_from_directory, current_app
import os

# ... existing code ...

@feedback_bp.route('/image/<path:filename>', methods=['GET'])
def get_feedback_image(filename):
    """
    获取反馈图片接口
    """
    try:
        base_dir = current_app.config['BASE_DIR']
        directory = os.path.join(base_dir, 'feedback_image')
        return send_from_directory(directory, filename)
    except Exception as e:
        print(f"Error serving image: {e}")
        return jsonify({'code': 404, 'msg': '图片不存在'}), 404

@feedback_bp.route('/add', methods=['POST'])
@jwt_required()
def add_feedback():
    """
    添加用户反馈接口
    """
    try:
        user_id = int(get_jwt_identity())
        
        # 获取表单数据
        title = request.form.get('title')
        content = request.form.get('content')
        image_file = request.files.get('image')

        # 校验必填项
        if not title or not content:
            return jsonify({'code': 400, 'msg': '标题和内容不能为空'}), 400

        # 调用服务层处理
        feedback = FeedbackService.create_feedback(user_id, title, content, image_file)

        return jsonify({
            'code': 200, 
            'msg': '反馈提交成功', 
            'data': feedback.to_dict()
        })
    except Exception as e:
        print(f"Error adding feedback: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@feedback_bp.route('/delete/<int:feedback_id>', methods=['POST'])
@jwt_required()
def delete_feedback(feedback_id):
    """
    撤销用户反馈接口
    """
    try:
        user_id = int(get_jwt_identity())
        success, msg = FeedbackService.delete_feedback(user_id, feedback_id)
        
        if success:
            return jsonify({'code': 200, 'msg': msg})
        else:
            return jsonify({'code': 400, 'msg': msg})
    except Exception as e:
        print(f"Error deleting feedback: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500