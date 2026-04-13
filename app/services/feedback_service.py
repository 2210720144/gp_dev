import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import db
from app.models.user_feedback import UserFeedback

from sqlalchemy import extract, desc

class FeedbackService:
    @staticmethod
    def get_user_feedback_list(user_id, year=None, month=None, show_all=False):
        """
        获取用户反馈列表
        :param user_id: 用户ID
        :param year: 年份 (int or str)
        :param month: 月份 (str, '01'-'12' or 'all')
        :param show_all: 是否显示全部 (bool)
        :return: list of UserFeedback
        """
        query = UserFeedback.query.filter_by(user_id=user_id)

        if not show_all:
            # 如果不是显示全部，则应用年份和月份过滤
            if year:
                query = query.filter(extract('year', UserFeedback.created_at) == int(year))
            
            if month and month != 'all':
                query = query.filter(extract('month', UserFeedback.created_at) == int(month))

        # 按创建时间倒序排列
        feedbacks = query.order_by(desc(UserFeedback.created_at)).all()
        return feedbacks

    @staticmethod
    def get_available_years(user_id):
        """
        获取用户反馈存在的年份列表
        :param user_id: 用户ID
        :return: list of years [2026, 2025]
        """
        years_query = db.session.query(extract('year', UserFeedback.created_at))\
            .filter(UserFeedback.user_id == user_id)\
            .distinct()\
            .order_by(desc(extract('year', UserFeedback.created_at)))\
            .all()
        
        # years_query result is like [(2026,), (2025,)]
        years = [int(y[0]) for y in years_query]
        return years

    @staticmethod
    def get_all_feedback_list(year=None, month=None, show_all=False):
        """
        获取所有用户的反馈列表（管理员端）
        :param year: 年份 (int or str)
        :param month: 月份 (str, '01'-'12' or 'all')
        :param show_all: 是否显示全部 (bool)
        :return: list of UserFeedback
        """
        query = UserFeedback.query

        if not show_all:
            # 如果不是显示全部，则应用年份和月份过滤
            if year:
                query = query.filter(extract('year', UserFeedback.created_at) == int(year))
            
            if month and month != 'all':
                query = query.filter(extract('month', UserFeedback.created_at) == int(month))

        # 按创建时间倒序排列
        feedbacks = query.order_by(desc(UserFeedback.created_at)).all()
        return feedbacks

    @staticmethod
    def get_all_available_years():
        """
        获取所有反馈存在的年份列表（管理员端）
        :return: list of years [2026, 2025]
        """
        years_query = db.session.query(extract('year', UserFeedback.created_at))\
            .distinct()\
            .order_by(desc(extract('year', UserFeedback.created_at)))\
            .all()
        
        years = [int(y[0]) for y in years_query]
        return years

    @staticmethod
    def reply_feedback(feedback_id, admin_id, reply_content):
        """
        管理员回复反馈
        :param feedback_id: 反馈ID
        :param admin_id: 管理员ID
        :param reply_content: 回复内容
        :return: UserFeedback object or None
        """
        feedback = UserFeedback.query.get(feedback_id)
        if not feedback:
            return None
        
        feedback.admin_reply = reply_content
        feedback.replied_at = datetime.now()
        feedback.replied_by = admin_id
        feedback.status = '已处理'
        
        db.session.commit()
        return feedback

        """
        创建用户反馈
        :param user_id: 用户ID
        :param title: 反馈标题
        :param content: 反馈内容
        :param image_file: 上传的图片文件对象 (FileStorage)
        :return: UserFeedback 对象
        """
        attachment_url = None

        # 处理图片上传
        if image_file:
            # 获取项目根目录下的 feedback_image 目录
            base_dir = current_app.config['BASE_DIR']
            upload_dir = os.path.join(base_dir, 'feedback_image')
            
            # 确保目录存在
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # 生成安全的文件名 (使用 UUID 防止重名)
            original_filename = secure_filename(image_file.filename)
            file_ext = os.path.splitext(original_filename)[1]
            if not file_ext:
                file_ext = '.jpg' # 默认后缀
                
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # 保存文件
            image_file.save(file_path)
            
            # 保存相对路径或绝对路径？
            # 这里的 attachment_url 用于后续访问，如果只是为了记录路径，可以用绝对路径
            # 如果是用于前端访问，可能需要配置静态资源路由。
            # 题目要求“保存到gp_dev/feedback_image目录下面”，这里存储相对路径比较灵活
            # 存储格式： feedback_image/filename
            attachment_url = f"feedback_image/{unique_filename}"

        # 创建反馈记录
        feedback = UserFeedback(
            user_id=user_id,
            title=title,
            content=content,
            status='待处理', # 默认为待处理
            attachment_url=attachment_url
        )

        db.session.add(feedback)
        db.session.commit()

        return feedback

    @staticmethod
    def delete_feedback(user_id, feedback_id):
        """
        删除用户反馈
        :param user_id: 用户ID
        :param feedback_id: 反馈ID
        :return: bool, message
        """
        feedback = UserFeedback.query.get(feedback_id)
        
        if not feedback:
            return False, "反馈记录不存在"
            
        if feedback.user_id != user_id:
            return False, "无权操作此记录"
            
        if feedback.status != '待处理':
            return False, "只能撤销待处理的反馈"
            
        # 删除关联的图片文件
        if feedback.attachment_url:
             try:
                base_dir = current_app.config['BASE_DIR']
                # attachment_url 格式如 "feedback_image/filename"
                file_path = os.path.join(base_dir, feedback.attachment_url)
                if os.path.exists(file_path):
                    os.remove(file_path)
             except Exception as e:
                 print(f"Error deleting file: {e}")

        db.session.delete(feedback)
        db.session.commit()
        
        return True, "撤销成功"