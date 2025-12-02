"""DB 데이터 출력 테스트 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.util import print_all_db

if __name__ == "__main__":
    print_all_db()
