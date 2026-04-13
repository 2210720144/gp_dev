from flask import Blueprint

camera_bp = Blueprint('camera', __name__, url_prefix='/api/camera')

from . import manage_camera
from . import monitor