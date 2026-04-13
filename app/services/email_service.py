import os
import threading
from flask import current_app
from flask_mail import Message
from app.utils.email import send_async_email


class EmailService:
    @staticmethod
    def send_alert_email(to_email, username, area_name, image_path=None):
        """
        发送违停告警邮件
        :param to_email: 收件人邮箱
        :param username: 收件人用户名
        :param area_name: 发生违停的区域名称（摄像头名称）
        :param image_path: 违停截图的绝对路径 (可选)
        """
        subject = "【基于YOLO算法的校园单车违规停放智能检测与告警系统】违停事件告警"
        body = f"{username}，{area_name}发生单车违停行为，麻烦前去处理一下，谢谢！"

        msg = Message(subject, recipients=[to_email], body=body)

        # 添加附件（截图）
        if image_path and os.path.exists(image_path):
            try:
                with current_app.open_resource(image_path) as fp:
                    # 以此读取二进制数据
                    file_data = fp.read()
                    # 获取文件名
                    filename = os.path.basename(image_path)
                    # 猜测MIME类型，通常是 image/jpeg 或 image/png
                    content_type = 'image/jpeg' if filename.lower().endswith('.jpg') or filename.lower().endswith(
                        '.jpeg') else 'image/png'

                    msg.attach(filename, content_type, file_data)
            except Exception as e:
                current_app.logger.error(f"Failed to attach image to email: {e}")

        # 异步发送邮件，避免阻塞主线程
        # 获取真实的 app 对象用于线程中
        app = current_app._get_current_object()
        threading.Thread(target=send_async_email, args=(app, msg)).start()