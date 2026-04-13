from flask_mail import Message
from app import mail
from flask import current_app
import threading


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")


def send_verification_email(to_email, code):
    subject = "【基于YOLO算法的校园单车违规停放智能检测与告警系统】注册验证码"
    body = f"""
    您好！

    您的注册验证码是：{code}

    该验证码将在 5 分钟后失效，请尽快完成注册。
    如果这不是您的操作，请忽略此邮件。
    """

    msg = Message(subject, recipients=[to_email], body=body)

    # Use threading to send asynchronously to avoid blocking the response
    app = current_app._get_current_object()
    threading.Thread(target=send_async_email, args=(app, msg)).start()