from flask import Blueprint

model_bp = Blueprint('model_bp', __name__, url_prefix='/api/model')

from . import manage_model