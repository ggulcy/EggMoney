from flask import Blueprint

bot_info_bp = Blueprint('bot_info', __name__)
trade_bp = Blueprint('trade', __name__)

from .status_routes import status_bp
from .index_routes import index_bp
from .auth_routes import auth_bp

__all__ = ['bot_info_bp', 'status_bp', 'index_bp', 'trade_bp', 'auth_bp']
