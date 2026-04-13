from flask import Blueprint

alert_record_bp = Blueprint('alert_record_bp', __name__, url_prefix='/api/alert')

from . import user_alert_record
from . import admin_alert_record