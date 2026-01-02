# GitHub 저장소 설정 가이드

## 1. GitHub에서 저장소 생성

1. https://github.com 에 로그인
2. 우측 상단의 "+" 버튼 클릭 → "New repository" 선택
3. Repository name: `preprocessing-test`
4. Description: "LLM-based preprocessing and validation system for clinical trials data"
5. Public 또는 Private 선택
6. **"Initialize this repository with a README" 체크 해제** (이미 로컬에 파일이 있으므로)
7. "Create repository" 클릭

## 2. 로컬에서 푸시

저장소를 생성한 후 다음 명령어를 실행하세요:

```bash
# 원격 저장소 추가 (이미 추가되어 있으면 생략)
git remote add origin https://github.com/lbs3250/preprocessing-test.git

# 브랜치 이름을 main으로 변경 (이미 되어 있으면 생략)
git branch -M main

# 푸시
git push -u origin main
```

## 3. 인증 문제가 발생하는 경우

### Personal Access Token 사용 (권장)

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 선택: `repo` (전체 권한)
4. 토큰 생성 후 복사
5. 푸시 시 비밀번호 대신 토큰 사용

```bash
git push -u origin main
# Username: lbs3250
# Password: [생성한 토큰 입력]
```

### 또는 SSH 사용

```bash
# SSH 키가 있다면
git remote set-url origin git@github.com:lbs3250/preprocessing-test.git
git push -u origin main
```

## 4. 현재 커밋된 파일

다음 파일들이 커밋되었습니다:

- LLM 전처리 및 검증 스크립트
- 데이터베이스 스키마 (SQL)
- 문서 (docs/)
- 전처리 스크립트 (preprocessing/)
- 분석 스크립트 (analysis/)
- SQL 쿼리 (sql/)

## 5. .gitignore에 포함된 항목 (커밋되지 않음)

- `.env` 파일 (환경 변수)
- `__pycache__/` (Python 캐시)
- 대용량 데이터 파일 (`data/raw.json`, `data/LLM_DATA.csv`)
- 임시 스크립트 (`check_*.py`, `show_*.py`)
- 로그 파일 (`*.txt`, `*.log`)
