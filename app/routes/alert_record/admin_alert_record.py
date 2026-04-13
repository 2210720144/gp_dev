from flask import jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.violation_event import ViolationEvent
from app.models.camera import Camera
from app.models.user import User, UserRole
from app.models import db
from sqlalchemy import extract
from . import alert_record_bp
import io
import os
from datetime import datetime


def _check_admin_permission(user_id):
    user = User.query.get(user_id)
    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        return False
    return True


def _get_admin_filtered_alerts_query():
    # 1. 获取所有摄像头
    all_cameras = Camera.query.all()
    camera_map = {c.camera_id: c.camera_name for c in all_cameras}
    camera_list = [{'id': c.camera_id, 'name': c.camera_name} for c in all_cameras]

    # 2. 获取参数
    camera_filter = request.args.get('camera_id')
    year_filter = request.args.get('year')
    month_filter = request.args.get('month')
    show_all = request.args.get('show_all') == 'true'

    # 3. 构建基础查询
    query = ViolationEvent.query

    # 4. 获取可用年份逻辑
    year_query = db.session.query(extract('year', ViolationEvent.start_time))

    if camera_filter and camera_filter != 'all':
        year_query = year_query.filter(ViolationEvent.camera_id == int(camera_filter))

    available_years = [int(y[0]) for y in year_query.distinct().all()]
    available_years.sort(reverse=True)

    # 5. 应用筛选条件
    if not show_all:
        if camera_filter and camera_filter != 'all':
            query = query.filter(ViolationEvent.camera_id == int(camera_filter))

        if year_filter:
            query = query.filter(extract('year', ViolationEvent.start_time) == int(year_filter))

        if month_filter and month_filter != 'all':
            query = query.filter(extract('month', ViolationEvent.start_time) == int(month_filter))

    # 按时间倒序
    alerts = query.order_by(ViolationEvent.start_time.desc()).all()

    return alerts, camera_map, available_years, camera_list


@alert_record_bp.route('/admin/list', methods=['GET'])
@jwt_required()
def get_admin_alert_list():
    current_user_id = int(get_jwt_identity())
    if not _check_admin_permission(current_user_id):
        return jsonify({'code': 403, 'msg': '无权访问'}), 403

    alerts, camera_map, available_years, camera_list = _get_admin_filtered_alerts_query()

    # 格式化返回数据
    alert_list = []
    for alert in alerts:
        cam_name = camera_map.get(alert.camera_id, f"ID:{alert.camera_id}")
        status = '已处理' if alert.end_time else '未处理'

        alert_list.append({
            'event_id': alert.event_id,
            'camera_id': alert.camera_id,
            'camera_name': cam_name,
            'start_time': alert.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': alert.end_time.strftime('%Y-%m-%d %H:%M:%S') if alert.end_time else '-',
            'status': status
        })

    return jsonify({
        'code': 200,
        'msg': 'success',
        'data': {
            'list': alert_list,
            'available_years': available_years,
            'authorized_cameras': camera_list
        }
    })


@alert_record_bp.route('/admin/export/excel', methods=['GET'])
@jwt_required()
def admin_export_excel():
    current_user_id = int(get_jwt_identity())
    if not _check_admin_permission(current_user_id):
        return jsonify({'code': 403, 'msg': '无权访问'}), 403

    alerts, camera_map, _, _ = _get_admin_filtered_alerts_query()

    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment
    except ImportError:
        return jsonify({'code': 500, 'msg': '服务器缺少 openpyxl 库，无法导出Excel'}), 500

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "告警事件记录"

    headers = ['事件ID', '摄像头ID', '摄像头名称', '违停开始时间', '违停结束时间', '状态']
    ws.append(headers)

    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    for alert in alerts:
        cam_name = camera_map.get(alert.camera_id, f"ID:{alert.camera_id}")
        status = '已处理' if alert.end_time else '未处理'
        ws.append([
            alert.event_id,
            alert.camera_id,
            cam_name,
            alert.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            alert.end_time.strftime('%Y-%m-%d %H:%M:%S') if alert.end_time else '-',
            status
        ])

    # Auto-width
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column].width = adjusted_width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"admin_alert_records_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@alert_record_bp.route('/admin/export/pdf', methods=['GET'])
@jwt_required()
def admin_export_pdf():
    current_user_id = int(get_jwt_identity())
    if not _check_admin_permission(current_user_id):
        return jsonify({'code': 403, 'msg': '无权访问'}), 403

    alerts, camera_map, _, _ = _get_admin_filtered_alerts_query()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except ImportError:
        return jsonify({'code': 500, 'msg': '服务器缺少 reportlab 库，无法导出PDF'}), 500

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    elements = []

    # 尝试注册中文字体 (Windows常用路径)
    font_path = "C:\\Windows\\Fonts\\simhei.ttf"
    font_name = 'Helvetica'  # 默认回退字体
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('SimHei', font_path))
            font_name = 'SimHei'
        except:
            pass

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.fontName = font_name
    elements.append(Paragraph("告警事件记录", title_style))
    elements.append(Spacer(1, 20))

    data = [['事件ID', '摄像头', '违停开始时间', '违停结束时间', '状态']]
    for alert in alerts:
        cam_name = camera_map.get(alert.camera_id, f"ID:{alert.camera_id}")
        status = '已处理' if alert.end_time else '未处理'
        data.append([
            str(alert.event_id),
            cam_name,
            alert.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            alert.end_time.strftime('%Y-%m-%d %H:%M:%S') if alert.end_time else '-',
            status
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))

    elements.append(table)
    doc.build(elements)
    output.seek(0)

    filename = f"admin_alert_records_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )