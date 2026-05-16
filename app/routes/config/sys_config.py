from flask import Blueprint, jsonify, request
from app.models import db
from app.models.sys_config import SysConfig

config_bp = Blueprint('config', __name__)

DEFAULT_CONFIGS = [
    {
        'config_key': '违停判定时间',
        'config_value': 1.0,
        'unit': 'min',
        'description': '当单车在禁停区域停留超过该时间时，系统将判定为违停行为'
    },
    {
        'config_key': '告警刷新时间',
        'config_value': 0.5,
        'unit': 'min',
        'description': '对于同一违停事件，系统再次触发告警的最小时间间隔'
    },
    {
        'config_key': 'YOLO置信度阈值',
        'config_value': 0.4,
        'unit': '0-1',
        'description': 'YOLO检测目标的最低置信度，低于该值的目标将被过滤'
    }
]

def init_default_configs():
    """Ensure default configurations exist in the database."""
    try:
        for config_data in DEFAULT_CONFIGS:
            config = SysConfig.query.filter_by(config_key=config_data['config_key']).first()
            if not config:
                new_config = SysConfig(
                    config_key=config_data['config_key'],
                    config_value=config_data['config_value'],
                    unit=config_data['unit'],
                    description=config_data['description']
                )
                db.session.add(new_config)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing configs: {e}")

@config_bp.route('/api/config', methods=['GET'])
def get_configs():
    """Get all system configurations."""
    init_default_configs()  # Lazy init to ensure data exists
    configs = SysConfig.query.all()
    
    # Convert list to dict for easier frontend access by key
    config_dict = {}
    for c in configs:
        config_dict[c.config_key] = c.to_dict()
        
    return jsonify({
        'code': 200,
        'msg': 'Success',
        'data': config_dict
    })

@config_bp.route('/api/config', methods=['POST'])
def update_configs():
    """Update system configurations."""
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'msg': 'No data provided'}), 400
        
    try:
        init_default_configs()
        # data format expected: {'violation_judgment_time': 1.5, 'alert_refresh_interval': 1.0}
        for key, value in data.items():
            config = SysConfig.query.filter_by(config_key=key).first()
            if config:
                if key == 'YOLO置信度阈值':
                    value = float(value)
                    if value < 0 or value > 1:
                        return jsonify({'code': 400, 'msg': 'YOLO置信度阈值必须在0到1之间'}), 400
                config.config_value = value
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': 'Settings saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
