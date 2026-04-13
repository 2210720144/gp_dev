from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.feedback_service import FeedbackService

admin_feedback_bp = Blueprint('admin_feedback', __name__, url_prefix='/api/admin/feedback')

@admin_feedback_bp.route('/list', methods=['GET'])
@jwt_required()
def get_admin_feedback_list():
    """
    获取所有用户反馈列表接口（管理员）
    参数:
    - year: 年份 (可选)
    - month: 月份 (可选, 'all' 或 '01'-'12')
    - show_all: 是否显示全部 (可选, 'true'/'false')
    """
    try:
        # 获取查询参数
        year = request.args.get('year')
        month = request.args.get('month')
        show_all_param = request.args.get('show_all', 'false').lower()
        show_all = show_all_param == 'true'

        # 获取所有可用年份 (用于前端下拉框)
        available_years = FeedbackService.get_all_available_years()
        
        # 如果没有指定年份且没有勾选显示全部，默认使用最近的年份
        # 如果没有任何反馈，available_years 为空，则 year 保持 None
        if not show_all and not year and available_years:
            year = available_years[0]

        # 获取反馈列表
        feedbacks = FeedbackService.get_all_feedback_list(year, month, show_all)

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
        print(f"Error getting admin feedback list: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@admin_feedback_bp.route('/reply', methods=['POST'])
@jwt_required()
def reply_feedback():
    """
    管理员回复反馈接口
    参数:
    - feedback_id: 反馈ID
    - reply_content: 回复内容
    """
    try:
        admin_id = int(get_jwt_identity())
        data = request.get_json()
        
        feedback_id = data.get('feedback_id')
        reply_content = data.get('reply_content')

        if not feedback_id or not reply_content:
            return jsonify({'code': 400, 'msg': '参数不完整'}), 400

        feedback = FeedbackService.reply_feedback(feedback_id, admin_id, reply_content)
        
        if not feedback:
            return jsonify({'code': 404, 'msg': '反馈记录不存在'}), 404

        return jsonify({
            'code': 200,
            'msg': '回复成功',
            'data': feedback.to_dict()
        })
    except Exception as e:
        print(f"Error replying feedback: {e}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500