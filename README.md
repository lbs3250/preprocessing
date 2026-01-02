# Clinical Trials LLM Preprocessing and Validation System

LLM 기반 임상시험 데이터 전처리 및 검증 시스템

## 주요 기능

### 1. Outcome 데이터 처리

- LLM 기반 Outcome 전처리
- 다중 검증 (Multi-run validation) 및 Majority Voting
- 일관성 점수 및 신뢰도 기반 필터링

### 2. Inclusion/Exclusion Criteria 처리

- Eligibility Criteria 수집
- LLM 기반 구조화 (Feature-Operator-Value 패턴)
- 범위 조건 자동 분리 처리

### 3. 검증 시스템

- 다중 검증 (기본 3회)
- Majority Voting
- 일관성 점수 계산
- Confidence + Consistency 기반 자동 수용/수동 검토 분류

## 프로젝트 구조

```
preprocessing-test/
├── llm/                    # LLM 전처리 및 검증 스크립트
│   ├── llm_preprocess_full.py
│   ├── llm_validate_preprocessed_success.py
│   ├── llm_preprocess_inclusion_exclusion.py
│   ├── llm_validate_inclusion_exclusion.py
│   └── llm_prompts.py
├── preprocessing/           # 데이터 수집 및 전처리
│   ├── collect_outcomes.py
│   └── collect_inclusion_exclusion.py
├── sql/                     # 데이터베이스 스키마
├── docs/                    # 문서
└── reports/                 # 리포트
```

## 설치 및 설정

### 1. 환경 변수 설정

`.env` 파일 생성:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinicaltrials
DB_USER=postgres
DB_PASSWORD=your_password

GEMINI_API_KEY=your_api_key_1
GEMINI_API_KEY_2=your_api_key_2
GEMINI_MODEL=gemini-1.5-flash
MAX_REQUESTS_PER_MINUTE=15
BATCH_SIZE=100
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 스키마 적용

```bash
psql -U postgres -d clinicaltrials -f sql/create_outcome_llm_preprocessed.sql
psql -U postgres -d clinicaltrials -f sql/add_multi_validation_schema.sql
psql -U postgres -d clinicaltrials -f sql/create_inclusion_exclusion_raw.sql
psql -U postgres -d clinicaltrials -f sql/create_inclusion_exclusion_llm_preprocessed.sql
psql -U postgres -d clinicaltrials -f sql/create_inclusion_exclusion_validation_history.sql
```

## 사용법

### Outcome 검증

```bash
# 기본 실행 (전체, 3회 검증, 배치 100개)
python llm/llm_validate_preprocessed_success.py

# 배치 크기 20개로 줄이기
python llm/llm_validate_preprocessed_success.py 999999 3 20
```

### Inclusion/Exclusion 검증

```bash
# 기본 실행
python llm/llm_validate_inclusion_exclusion.py

# 배치 크기 20개로 줄이기
python llm/llm_validate_inclusion_exclusion.py 999999 3 20
```

## 통계

### Outcome 처리 결과

- 전처리 시도: 9,030개
- 전처리 성공: 8,912개 (98.69%)
- VERIFIED: 8,414개 (94.41%)
- 자동 수용 가능: 7,382개 (82.83%)

### Inclusion/Exclusion 처리 결과

- 전처리 성공: 1,270개 (96.21%)
- 평균 Inclusion Criteria: 10.8개
- 평균 Exclusion Criteria: 15.6개

## 문서

- [LLM 검증 사용 가이드](docs/llm_validation_usage_guide.md)
- [Inclusion/Exclusion 전처리 가이드](docs/inclusion_exclusion_preprocess_usage_guide.md)
- [Inclusion/Exclusion 검증 가이드](docs/inclusion_exclusion_validation_usage_guide.md)
- [전처리 리포트](docs/inclusion_exclusion_preprocessing_report.md)

## 라이선스

MIT
