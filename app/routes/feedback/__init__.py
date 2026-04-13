from flask import Blueprint

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

from . import user_feedback