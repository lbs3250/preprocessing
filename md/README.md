# ClinicalTrials.gov Outcomes 정규화 프로젝트

## 프로젝트 구조

### 핵심 스크립트

1. **수집**: `collect_outcomes.py`

   - ClinicalTrials.gov API에서 데이터 수집
   - outcome_raw, study_party_raw 테이블에 저장

2. **진단**: `diagnose_all.py`

   - 데이터 품질 분석
   - 패턴 분석 및 통계 생성
   - MD 리포트 및 JSON 파일 생성

3. **정규화**: `normalize_phase1.py`

   - 1차 정규화 수행
   - measure 약어 추출 + time_frame 파싱
   - outcome_normalized 테이블에 저장

4. **결과 분리**: `separate_normalized_data.py`
   - 성공/실패 데이터 분리
   - outcome_normalized_success, outcome_normalized_failed 테이블 생성

### 데이터베이스

- `schema.sql`: 초기 테이블 생성
- `update_schema.sql`: 스키마 업데이트 (컬럼 추가 등)
- `query_normalized_results.sql`: 정규화 결과 조회 쿼리

### 지원 모듈

- `normalization_patterns.py`: 정규식 패턴 정의
- `diagnosis_queries.py`: 진단 쿼리 함수
- `generate_excel_report.py`: Excel 리포트 생성

## 사용 방법

### 1. 환경 설정

```bash
# .env 파일 생성
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinical_trials
DB_USER=postgres
DB_PASSWORD=your_password
```

### 2. 데이터베이스 초기화

```bash
# PostgreSQL에서 실행
psql -U postgres -d clinical_trials -f schema.sql
```

### 3. 데이터 수집

```bash
python collect_outcomes.py
```

### 4. 데이터 진단

```bash
python diagnose_all.py
```

### 5. 정규화 실행

```bash
python normalize_phase1.py
```

### 6. 결과 분리

```bash
python separate_normalized_data.py
```

### 7. 결과 조회

```bash
# PostgreSQL에서 실행
psql -U postgres -d clinical_trials -f query_normalized_results.sql
```

## 성공 기준

**1차 정규화 성공 조건:**

- measure 약어 추출 성공 (괄호 안 약어)
- time_frame 추출 성공 (time_value_main + time_unit_main)

둘 다 성공해야 `outcome_normalized_success`에 포함됩니다.

## 테이블 구조

1. `outcome_raw`: 원본 데이터 보존
2. `outcome_normalized`: 정규화된 데이터 (전체)
3. `outcome_normalized_success`: 정규화 성공 데이터
4. `outcome_normalized_failed`: 정규화 실패 데이터
5. `outcome_measure_dict`: Measure 사전 (2차 정규화용)
6. `study_party_raw`: 기관/담당자 정보






