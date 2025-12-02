"""
Index Routes - 메인 페이지

Clean Architecture Pattern:
- GET / - 메인 페이지 (메뉴 네비게이션)
"""
from flask import Blueprint, render_template

from config import item

index_bp = Blueprint('index', __name__)


@index_bp.route('/', methods=['GET'])
def index():
    """메인 페이지"""
    return render_template(
        'index.html',
        title='EggMoney Trading Bot',
        admin=item.admin.value
    )
