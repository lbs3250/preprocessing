# Git 커밋 요약

## 현재 커밋 상태

총 5개 커밋이 준비되어 있습니다:

1. `4facbd9` - Add README.md (lbs3250)
2. `cecd24a` - Update .gitignore (lbs3250)
3. `ea55444` - Add GitHub setup guide (lbs3250)
4. `9074547` - Add all project files: LLM preprocessing and validation system (oprimed04)
5. `0a08f36` - Initial commit: LLM preprocessing and validation system (oprimed04)

## Git 설정

- **로컬 사용자**: lbs3250 <lbs3250@gmail.com>
- **원격 저장소**: https://github.com/lbs3250/preprocessing-test.git
- **브랜치**: main

## 커밋된 주요 파일

### LLM 스크립트
- `llm/llm_preprocess_full.py` - Outcome 전처리
- `llm/llm_validate_preprocessed_success.py` - Outcome 검증
- `llm/llm_preprocess_inclusion_exclusion.py` - Inclusion/Exclusion 전처리
- `llm/llm_validate_inclusion_exclusion.py` - Inclusion/Exclusion 검증
- `llm/llm_prompts.py` - 프롬프트 정의
- `llm/llm_config.py` - API 설정

### 전처리 스크립트
- `preprocessing/collect_outcomes.py`
- `preprocessing/collect_inclusion_exclusion.py`
- `preprocessing/normalize_phase1.py`

### 데이터베이스 스키마
- `sql/create_outcome_llm_preprocessed.sql`
- `sql/add_multi_validation_schema.sql`
- `sql/create_inclusion_exclusion_raw.sql`
- `sql/create_inclusion_exclusion_llm_preprocessed.sql`
- `sql/create_inclusion_exclusion_validation_history.sql`

### 문서
- `docs/llm_validation_usage_guide.md`
- `docs/inclusion_exclusion_preprocess_usage_guide.md`
- `docs/inclusion_exclusion_validation_usage_guide.md`
- `docs/inclusion_exclusion_preprocessing_report.md`
- `docs/daily_summary_20250124.md`

### 기타
- `README.md`
- `requirements.txt`
- `.gitignore`

## 수동 업로드 방법

### 방법 1: GitHub 웹에서 직접 업로드

1. https://github.com/lbs3250/preprocessing-test 접속
2. "Add file" → "Upload files" 클릭
3. 파일 드래그 앤 드롭 또는 선택
4. "Commit changes" 클릭

### 방법 2: Git 명령어 사용 (인증 후)

```bash
# Personal Access Token 생성 후
git push -u origin main
```

### 방법 3: ZIP 파일로 업로드

```bash
# 커밋된 파일만 압축
git archive -o preprocessing-test.zip HEAD
```

그 다음 GitHub에서 ZIP 파일을 업로드하고 압축 해제

## 제외된 파일 (.gitignore)

다음 파일들은 커밋되지 않았습니다:
- `.env` (환경 변수)
- `data/raw.json` (대용량 데이터)
- `data/LLM_DATA.csv` (대용량 데이터)
- `check_*.py` (임시 스크립트)
- `show_*.py` (임시 스크립트)
- `*.png` (시각화 파일)
- `*.txt`, `*.log` (로그 파일)

