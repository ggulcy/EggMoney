# EggMoney 웹 통합 작업 계획

## 현황
- 현재: EC2 3~5대 (계정별 독립 실행)
- 목표: 단일 웹 서버로 통합 (멀티 유저)

## 인프라 구조

### 권장 구성
```
EC2 t3.small (월 $15) - 1인당 $3~5
├─ FastAPI/Flask (웹 앱)
├─ PostgreSQL (로컬 설치)
├─ APScheduler (멀티 유저 스케줄러)
└─ Nginx
```

### 프리티어 옵션
```
EC2 t2.micro (1년 무료)
└─ 5~10명까지 가능
└─ 순차 처리로 충분 (부하 낮음)
```

## 작업 목록

### 1. 유저 인증/관리 시스템
- [ ] User 모델 설계
  - users (id, username, password_hash, email, created_at)
  - user_credentials (API 키 암호화 저장)
- [ ] 로그인/회원가입 API
- [ ] JWT/세션 인증
- [ ] 기존 key_store.json → DB 마이그레이션

### 2. 기존 DB 통합 (user_id 추가)
- [ ] 모든 테이블에 `user_id` 컬럼 추가
  ```python
  # 예시
  class Trade(Base):
      user_id = Column(Integer, ForeignKey('users.id'))
  ```
- [ ] 각 EC2의 로컬 DB 데이터 추출
- [ ] user_id 매핑 후 통합 DB에 삽입
- [ ] 마이그레이션 스크립트 작성

### 3. DB 연결 변경
- [ ] PostgreSQL 설치 (EC2 로컬 또는 RDS)
- [ ] 환경변수 설정
  ```python
  DATABASE_URL = "postgresql://user:pass@host:5432/eggmoney"
  ```
- [ ] `psycopg2-binary` 설치
- [ ] 연결 테스트

### 4. 스케줄러 멀티 유저 대응
- [ ] 유저별 스케줄 설정 테이블 생성
- [ ] DB에서 활성 유저 목록 로드
- [ ] 유저별 거래 로직 실행
  ```python
  def start():
      users = get_all_active_users()  # DB 조회
      for user in users:
          trade(user)
  ```
- [ ] 현재 순차 처리 유지 (비동기 불필요)

### 5. API 키 보안
- [ ] Fernet 암호화 적용
- [ ] 환경변수로 SECRET_KEY 관리
- [ ] API 키 CRUD API 구현

### 6. 프론트엔드 (선택)
- [ ] 로그인/회원가입 페이지
- [ ] 대시보드 (거래 내역)
- [ ] 설정 페이지 (API 키, 스케줄)

### 7. 권한 관리
- [ ] 본인 데이터만 조회 가능
  ```python
  @router.get("/trades")
  def get_trades(current_user: User = Depends(auth)):
      return Trade.filter_by(user_id=current_user.id)
  ```

## 작업 우선순위

### Phase 1: DB 통합 (필수)
1. User 모델 설계
2. 기존 모델에 user_id 추가
3. 데이터 마이그레이션
4. DB 연결 변경

### Phase 2: 스케줄러 개선 (필수)
1. 멀티 유저 스케줄러 구현
2. DB 기반 유저 로딩
3. 테스트

### Phase 3: 인증 시스템 (필수)
1. 회원가입/로그인
2. API 키 관리
3. 권한 체크

### Phase 4: 프론트엔드 (선택)
1. 기본 UI
2. 대시보드
3. 설정 페이지

## 예상 작업 기간
- Phase 1~3: 핵심 기능 (필수)
- Phase 4: UI 개선 (선택)

## 참고 사항
- 현재 순차 처리로 충분 (비동기 불필요)
- t2.micro 프리티어로 5~10명 가능
- 20명 이상 시 t3.small 고려
- SQLAlchemy 그대로 사용 (DB만 변경)
- PostgreSQL 권장 (MySQL 불필요)

## 주요 변경 파일
```
egg/
├─ models/user.py (신규)
├─ models/trade.py (user_id 추가)
├─ main.py (DB 연결 변경)
├─ trade_module.py (멀티 유저 대응)
└─ config.py (환경변수)
```

## 마이그레이션 예시
```python
# 1. 기존 DB 백업
# 2. 유저 생성
user1 = User(username="chan", ...)
user2 = User(username="choe", ...)

# 3. 기존 데이터 마이그레이션
old_trades = sqlite_session.query(Trade).all()
for trade in old_trades:
    trade.user_id = user1.id  # 매핑
    new_session.add(trade)
```
