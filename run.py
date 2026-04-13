from app import create_app
from app.models import db
from app.models.user import User, UserRole, UserStatus

# 创建一个应用对象，用来处理请求、管理数据库等
app = create_app()

def init_db():
    # 手动创建一个应用上下文对象，为了确保超级管理员账户存在
    with app.app_context():
        # 创建表，但还是手动进行数据库迁移更为精确稳妥
        db.create_all()
        
        # 检查超级管理员账号是否存在
        root_email = "root@system.com"
        # 查询用户表中是否存在超级管理员，不存在就新增一条
        if not User.query.filter_by(role=UserRole.ROOT).first():
            print("Creating default root user...")
            root = User(
                username="root",
                password="root",
                email=root_email,
                role=UserRole.ROOT,
                status=UserStatus.ACTIVE
            )
            # 添加更改
            db.session.add(root)
            # 提交更改
            db.session.commit()
            print(f"Root user created. Email: {root_email}, Password: root")

if __name__ == '__main__':
    # 执行函数
    init_db()
    # app.run(debug=True)
    # 使用下面的运行语句就可以在其他机器上运行链接了
    app.run(host="0.0.0.0", port=5000, debug=True)
