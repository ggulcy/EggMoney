from flask import Blueprint

bot_info_bp = Blueprint('bot_info', __name__)
trade_bp = Blueprint('trade', __name__)

from .status_routes import status_bp
from .index_routes import index_bp
from .auth_routes import auth_bp
from .history_routes import history_bp
from .external_routes import external_bp
from . import bot_info_routes  # bot_info 라우트 등록
from . import trade_routes  # trade 라우트 등록

__all__ = ['bot_info_bp', 'status_bp', 'index_bp', 'trade_bp', 'auth_bp', 'history_bp', 'external_bp']
