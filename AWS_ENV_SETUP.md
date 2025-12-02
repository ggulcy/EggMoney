# AWS 환경변수 설정 가이드

EggMoney 프로젝트를 AWS에서 실행할 때 환경변수를 설정하는 방법입니다.

## 📋 필요한 환경변수

```bash
EGGMONEY_ADMIN=chan  # 또는 choe, sk
# 또는
BOT_ADMIN=chan       # EGGMONEY_ADMIN이 없을 때 사용됨
```

---

## 1️⃣ AWS EC2 (Amazon Linux 2 / Ubuntu)

### 방법 1: 시스템 전역 환경변수 설정

#### 1.1 `/etc/environment` 수정 (권장)

```bash
# EC2 인스턴스에 SSH 접속
ssh -i your-key.pem ec2-user@your-ec2-ip

# /etc/environment 파일 편집 (sudo 필요)
sudo vim /etc/environment

# 다음 내용 추가
EGGMONEY_ADMIN=chan

# 저장 후 재부팅 또는 source로 적용
source /etc/environment
```

#### 1.2 `/etc/profile.d/` 사용

```bash
# 프로필 스크립트 생성
sudo vim /etc/profile.d/eggmoney.sh

# 다음 내용 추가
export EGGMONEY_ADMIN=chan

# 실행 권한 부여
sudo chmod +x /etc/profile.d/eggmoney.sh

# 적용
source /etc/profile.d/eggmoney.sh
```

### 방법 2: systemd 서비스 환경변수 설정

EggMoney를 systemd 서비스로 실행하는 경우:

```bash
# 서비스 파일 생성/수정
sudo vim /etc/systemd/system/eggmoney.service
```

```ini
[Unit]
Description=EggMoney Trading Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/EggMoney
Environment="EGGMONEY_ADMIN=chan"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ec2-user/EggMoney/venv/bin/python main_egg.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 재로드 및 재시작
sudo systemctl daemon-reload
sudo systemctl restart eggmoney
sudo systemctl status eggmoney

# 로그 확인
sudo journalctl -u eggmoney -f
```

### 방법 3: Screen/Tmux 세션에서 실행

```bash
# 환경변수와 함께 실행
export EGGMONEY_ADMIN=chan
cd /home/ec2-user/EggMoney
source venv/bin/activate
python main_egg.py
```

---

## 2️⃣ AWS ECS (Elastic Container Service)

### Docker Compose 방식

#### docker-compose.yml

```yaml
version: '3.8'

services:
  eggmoney:
    image: your-ecr-repo/eggmoney:latest
    container_name: eggmoney
    environment:
      - EGGMONEY_ADMIN=chan
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data:/app/data
    restart: always
```

```bash
# Docker Compose 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### ECS Task Definition (Fargate/EC2)

AWS ECS 콘솔에서 Task Definition 수정:

```json
{
  "family": "eggmoney-task",
  "containerDefinitions": [
    {
      "name": "eggmoney",
      "image": "your-ecr-repo/eggmoney:latest",
      "memory": 512,
      "cpu": 256,
      "essential": true,
      "environment": [
        {
          "name": "EGGMONEY_ADMIN",
          "value": "chan"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/eggmoney",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512"
}
```

또는 AWS CLI로 업데이트:

```bash
# Task Definition 등록
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# 서비스 업데이트
aws ecs update-service \
  --cluster eggmoney-cluster \
  --service eggmoney-service \
  --task-definition eggmoney-task:latest \
  --force-new-deployment
```

---

## 3️⃣ AWS Lambda (선택 사항)

Lambda Function에서 실행하는 경우:

### Lambda 콘솔에서 설정

1. Lambda 함수 선택
2. **Configuration** → **Environment variables** 클릭
3. **Edit** 클릭
4. **Add environment variable** 클릭
   - Key: `EGGMONEY_ADMIN`
   - Value: `chan`
5. **Save** 클릭

### AWS CLI로 설정

```bash
aws lambda update-function-configuration \
  --function-name eggmoney-function \
  --environment "Variables={EGGMONEY_ADMIN=chan}"
```

---

## 4️⃣ AWS Systems Manager Parameter Store (보안 강화)

민감한 정보를 Parameter Store에 저장하고 애플리케이션에서 읽기:

### Parameter Store에 저장

```bash
# SecureString으로 저장
aws ssm put-parameter \
  --name "/eggmoney/admin" \
  --value "chan" \
  --type "String" \
  --description "EggMoney Admin User"

# 조회 테스트
aws ssm get-parameter \
  --name "/eggmoney/admin" \
  --query "Parameter.Value" \
  --output text
```

### Python 코드에서 읽기 (선택 사항)

`config/item.py`를 수정하여 Parameter Store에서 읽을 수도 있습니다:

```python
import boto3

def _get_admin_from_ssm():
    """AWS Systems Manager Parameter Store에서 admin 값 읽기"""
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        response = ssm.get_parameter(Name='/eggmoney/admin', WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"⚠️ SSM Parameter 읽기 실패: {e}")
        return None
```

---

## 5️⃣ 로컬 개발 환경 (.env 파일)

로컬에서 개발할 때는 `.env` 파일 사용:

### .env 파일 생성

```bash
# EggMoney/.env
EGGMONEY_ADMIN=chan
```

### python-dotenv 설치

```bash
pip install python-dotenv
```

### config/item.py에서 .env 읽기

```python
from dotenv import load_dotenv
import os

# .env 파일 로드 (로컬 개발용)
load_dotenv()

admin_value = os.getenv('EGGMONEY_ADMIN')
```

---

## 6️⃣ 확인 방법

### Python으로 환경변수 확인

```python
import os
print(f"EGGMONEY_ADMIN: {os.getenv('EGGMONEY_ADMIN')}")
print(f"BOT_ADMIN: {os.getenv('BOT_ADMIN')}")
```

### Bash로 확인

```bash
# 현재 세션에서 확인
echo $EGGMONEY_ADMIN

# 모든 환경변수 확인
env | grep EGGMONEY
```

### EggMoney 실행 로그 확인

프로그램 시작 시 다음 로그가 출력되어야 합니다:

```
✅ Admin 설정: chan (환경변수에서 읽음)
```

---

## 📌 주의사항

1. **환경변수 우선순위**: `EGGMONEY_ADMIN` > `BOT_ADMIN` > 기본값(`chan`)

2. **대소문자**: 환경변수 값은 자동으로 소문자로 변환됨 (`Chan` → `chan`)

3. **유효한 값**: `chan`, `choe`, `sk` 만 허용 (그 외 값은 기본값 `chan` 사용)

4. **재시작 필요**: 환경변수 변경 후에는 애플리케이션 재시작 필수

5. **보안**:
   - `.env` 파일은 `.gitignore`에 추가 필수
   - Parameter Store 사용 시 IAM 권한 필요

---

## 🚀 권장 설정

### 프로덕션 (AWS EC2/ECS)
- **방법 1**: systemd 서비스 환경변수 (EC2)
- **방법 2**: ECS Task Definition 환경변수 (ECS)

### 개발 환경
- **방법**: `.env` 파일 + python-dotenv

### 보안 민감 정보
- **방법**: AWS Systems Manager Parameter Store

---

## 🔧 트러블슈팅

### 환경변수가 적용되지 않을 때

```bash
# 1. 환경변수 확인
echo $EGGMONEY_ADMIN

# 2. Python에서 확인
python3 -c "import os; print(os.getenv('EGGMONEY_ADMIN'))"

# 3. 프로세스 환경변수 확인 (프로세스 실행 중일 때)
cat /proc/$(pgrep -f main_egg.py)/environ | tr '\0' '\n' | grep EGGMONEY

# 4. 로그 확인
tail -f /var/log/eggmoney.log
# 또는
sudo journalctl -u eggmoney -f
```

### systemd 서비스에서 환경변수 안 읽힐 때

```bash
# 서비스 파일에 Environment 추가 확인
systemctl cat eggmoney

# 서비스 재로드
sudo systemctl daemon-reload
sudo systemctl restart eggmoney
```

---

## 📚 참고 링크

- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [AWS ECS Task Definition Parameters](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
