# Inclusion/Exclusion LLM 검증 스크립트 사용 가이드

생성일시: 2025-01-24

## 목차

1. [개요](#개요)
2. [사전 준비](#사전-준비)
3. [기본 사용법](#기본-사용법)
4. [옵션 설명](#옵션-설명)
5. [검증 이력 관리](#검증-이력-관리)
6. [재검증 방법](#재검증-방법)
7. [예시](#예시)
8. [주의사항](#주의사항)

---

## 개요

`llm_validate_inclusion_exclusion.py`는 LLM으로 전처리된 Inclusion/Exclusion Criteria 성공 항목(SUCCESS)을 검증하는 스크립트입니다.

### 주요 기능

- **다중 검증**: 각 항목을 여러 번 검증하여 일관성 확인 (기본 3회)
- **Majority Voting**: 여러 검증 결과 중 가장 많이 나온 결과를 최종 결과로 선택
- **일관성 점수**: 동일한 결과가 나온 비율을 계산하여 검증 결과의 안정성 측정
- **배치 처리**: 효율적인 처리 및 중단 재개 지원
- **검증 이력 저장**: 모든 검증 실행 결과를 히스토리로 저장

---

## 사전 준비

### 1. 데이터베이스 스키마 적용

검증 이력 테이블 및 컬럼을 추가합니다:

```bash
psql -U postgres -d clinicaltrials -f sql/create_inclusion_exclusion_validation_history.sql
```

### 2. 환경 변수 설정

`.env` 파일에 다음 변수들을 설정합니다:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinicaltrials
DB_USER=postgres
DB_PASSWORD=your_password

GEMINI_API_KEY=your_api_key_1
GEMINI_API_KEY_2=your_api_key_2  # 선택사항: 여러 키 사용 가능
GEMINI_API_KEY_3=your_api_key_3  # 선택사항

GEMINI_MODEL=gemini-1.5-flash
MAX_REQUESTS_PER_MINUTE=15
BATCH_SIZE=100
```

---

## 기본 사용법

### 기본 실행 (모든 옵션 기본값)

```bash
python llm/llm_validate_inclusion_exclusion.py
```

**기본 설정**:

- 검증 횟수: 3회
- 배치 크기: 100개
- 시작 배치: 1번
- 처리 대상: `llm_status = 'SUCCESS'`인 모든 항목

---

## 옵션 설명

### 명령줄 인자 형식

```bash
python llm/llm_validate_inclusion_exclusion.py [limit] [num_validations] [batch_size] [start_batch]
```

### 옵션 상세 설명

#### 1. `limit` (첫 번째 인자)

**설명**: 처리할 항목 수 제한

**기본값**: `None` (전체 처리)

**예시**:

```bash
# 100개만 검증
python llm/llm_validate_inclusion_exclusion.py 100
```

#### 2. `num_validations` (두 번째 인자)

**설명**: 각 항목당 검증 횟수

**기본값**: `3`

**권장값**: 3~5회

**예시**:

```bash
# 각 항목을 5회 검증
python llm/llm_validate_inclusion_exclusion.py 1000 5
```

**주의사항**:

- 검증 횟수가 많을수록 API 호출 비용 증가
- 검증 횟수가 많을수록 처리 시간 증가
- 권장: 3~5회

#### 3. `batch_size` (세 번째 인자)

**설명**: 배치 크기 (한 번에 처리할 항목 수)

**기본값**: `100` (환경변수 `BATCH_SIZE` 또는 코드 기본값)

**예시**:

```bash
# 배치 크기를 50개로 설정
python llm/llm_validate_inclusion_exclusion.py 1000 3 50
```

**주의사항**:

- 배치 크기가 작을수록 더 자주 저장 (중단 시 손실 적음)
- 배치 크기가 클수록 처리 효율 향상
- 권장: 50~100개

#### 4. `start_batch` (네 번째 인자)

**설명**: 시작할 배치 번호 (중단 재개용)

**기본값**: `1`

**예시**:

```bash
# 10번 배치부터 시작 (1~9번 배치 건너뜀)
python llm/llm_validate_inclusion_exclusion.py 1000 3 100 10
```

**사용 시나리오**:

- 중간에 중단된 경우, 마지막 처리된 배치 다음 번호부터 재개
- 특정 배치부터 다시 처리하고 싶은 경우

---

## 검증 이력 관리

### 검증 이력 저장 구조

**검증 3회 수행 시**:

- 1회차 검증 결과 → `validation_run = 1`로 저장
- 2회차 검증 결과 → `validation_run = 2`로 저장
- 3회차 검증 결과 → `validation_run = 3`으로 저장

**재검증 3회 추가 수행 시**:

- 4회차 검증 결과 → `validation_run = 4`로 저장
- 5회차 검증 결과 → `validation_run = 5`로 저장
- 6회차 검증 결과 → `validation_run = 6`으로 저장

### 검증 이력 테이블 구조

```sql
inclusion_exclusion_llm_validation_history
├── id (PK)
├── nct_id (FK → inclusion_exclusion_llm_preprocessed.nct_id)
├── validation_run (검증 실행 횟수: 1, 2, 3, ...)
├── validation_status (VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED)
├── validation_confidence (0.00 ~ 1.00)
├── validation_notes (검증 노트)
└── created_at (생성 시간)
```

### 검증 이력 조회 예시

```sql
-- 특정 nct_id의 모든 검증 이력 조회
SELECT
    validation_run,
    validation_status,
    validation_confidence,
    validation_notes,
    created_at
FROM inclusion_exclusion_llm_validation_history
WHERE nct_id = 'NCT00000171'
ORDER BY validation_run;
```

**결과 예시**:

```
validation_run | validation_status | validation_confidence | created_at
---------------|-------------------|----------------------|-------------------
1              | VERIFIED          | 0.95                 | 2025-01-24 10:00:00
2              | VERIFIED          | 0.92                 | 2025-01-24 10:00:05
3              | UNCERTAIN         | 0.60                 | 2025-01-24 10:00:10
4              | VERIFIED          | 0.90                 | 2025-01-24 11:00:00
5              | VERIFIED          | 0.88                 | 2025-01-24 11:00:05
6              | VERIFIED          | 0.93                 | 2025-01-24 11:00:10
```

### 메인 테이블 컬럼

`inclusion_exclusion_llm_preprocessed` 테이블의 검증 관련 컬럼:

- `llm_validation_status`: 최종 검증 상태 (전체 검증 결과의 Majority Voting 결과)
- `llm_validation_confidence`: 최종 검증 신뢰도 (전체 검증 결과의 평균)
- `validation_consistency_score`: 일관성 점수 (0.00 ~ 1.00)
- `validation_count`: 전체 검증 횟수 (누적)
- `avg_validation_confidence`: 평균 검증 신뢰도
- `needs_manual_review`: 수동 검토 필요 여부

---

## 재검증 방법

### 재검증 동작 방식

재검증 시 **기존 검증 이력과 합쳐서** Majority Voting을 수행합니다.

**예시**:

1. **첫 번째 검증 (3회)**:

   ```
   검증 1회차: VERIFIED (confidence: 0.95)
   검증 2회차: VERIFIED (confidence: 0.92)
   검증 3회차: UNCERTAIN (confidence: 0.60)

   → 최종: VERIFIED (2/3), 일관성: 0.67
   ```

2. **재검증 (3회 더)**:

   ```
   기존 이력: [VERIFIED, VERIFIED, UNCERTAIN] (3회)
   새 검증: [VERIFIED, VERIFIED, VERIFIED] (3회)

   → 전체: [VERIFIED, VERIFIED, UNCERTAIN, VERIFIED, VERIFIED, VERIFIED] (6회)
   → 최종: VERIFIED (5/6), 일관성: 0.83
   ```

### 재검증 실행 방법

#### 방법 1: 이미 검증된 항목도 재검증

기본적으로 `llm_status = 'SUCCESS'`인 모든 항목을 검증합니다. 재검증을 위해서는:

1. **수동으로 검증 상태 초기화**:

   ```sql
   UPDATE inclusion_exclusion_llm_preprocessed
   SET llm_validation_status = NULL
   WHERE nct_id IN ('NCT00000171', 'NCT00000172', 'NCT00000173');
   ```

2. **검증 실행**:
   ```bash
   python llm/llm_validate_inclusion_exclusion.py
   ```

#### 방법 2: 특정 항목만 재검증

```sql
-- 특정 항목의 검증 상태만 초기화
UPDATE inclusion_exclusion_llm_preprocessed
SET
    llm_validation_status = NULL,
    validation_consistency_score = NULL,
    validation_count = 0
WHERE nct_id = 'NCT00000171';
```

그 후 검증 실행:

```bash
python llm/llm_validate_inclusion_exclusion.py
```

**주의**: 검증 이력(`inclusion_exclusion_llm_validation_history`)은 삭제되지 않으며, 재검증 시 기존 이력과 합쳐서 처리됩니다.

---

## 예시

### 예시 1: 소규모 테스트 (10개, 3회 검증)

```bash
python llm/llm_validate_inclusion_exclusion.py 10 3
```

**출력 예시**:

```
[INFO] 처리할 SUCCESS 항목: 10개
[INFO] 다중 검증 횟수: 3회
[STEP 1] LLM 다중 검증 시작 (배치 크기: 100, 항목당 3회 검증)...
  배치 1/1 처리 중: 1~10번째 항목
  배치 1 결과 저장 중... (10개)
```

### 예시 2: 대규모 처리 (1000개, 5회 검증, 배치 크기 50)

```bash
python llm/llm_validate_inclusion_exclusion.py 1000 5 50
```

**출력 예시**:

```
[INFO] 처리할 SUCCESS 항목: 1,000개
[INFO] 다중 검증 횟수: 5회
[INFO] 배치 크기를 50개로 조정했습니다.
[STEP 1] LLM 다중 검증 시작 (배치 크기: 50, 항목당 5회 검증)...
  배치 1/20 처리 중: 1~50번째 항목
  배치 1 결과 저장 중... (50개)
  배치 2/20 처리 중: 51~100번째 항목
  ...
```

### 예시 3: 중단 재개 (배치 10번부터)

```bash
python llm/llm_validate_inclusion_exclusion.py 1000 3 100 10
```

**출력 예시**:

```
[INFO] 배치 10번부터 시작합니다.
[STEP 1] LLM 다중 검증 시작...
  배치 1/10 건너뜀 (start_batch=10)
  배치 2/10 건너뜀 (start_batch=10)
  ...
  배치 10/10 처리 중: 901~1000번째 항목
```

### 예시 4: 전체 처리 (기본 설정)

```bash
python llm/llm_validate_inclusion_exclusion.py
```

**출력 예시**:

```
[INFO] 처리할 SUCCESS 항목: 15,234개
[INFO] 다중 검증 횟수: 3회
[STEP 1] LLM 다중 검증 시작 (배치 크기: 100, 항목당 3회 검증)...
  배치 1/153 처리 중: 1~100번째 항목
  배치 1 결과 저장 중... (100개)
  ...
```

---

## 주의사항

### 1. API 호출 비용

- 검증 횟수가 많을수록 API 호출 비용 증가
- 예: 10,000개 항목 × 3회 검증 = 30,000회 API 호출
- 권장: 테스트 시 `limit` 옵션으로 소규모 테스트 먼저 수행

### 2. 처리 시간

- 검증 횟수와 배치 크기에 따라 처리 시간 결정
- Rate limiting으로 인해 배치 간 대기 시간 발생
- 예상 시간: 항목당 (검증 횟수 × API 호출 시간 + 대기 시간)

### 3. 중단 재개

- 배치마다 DB에 저장하므로 중단되어도 저장된 배치는 유지
- 중단된 지점부터 재개하려면 `start_batch` 옵션 사용
- 마지막 처리된 배치 번호 확인:
  ```sql
  SELECT MAX(validation_run) as last_run
  FROM inclusion_exclusion_llm_validation_history
  WHERE nct_id = 'NCT00000171';
  ```

### 4. 검증 이력 관리

- 검증 이력은 **누적**됩니다 (삭제되지 않음)
- 재검증 시 기존 이력과 합쳐서 처리
- 이력이 많아지면 저장 공간 증가
- 필요시 수동으로 이력 삭제:
  ```sql
  DELETE FROM inclusion_exclusion_llm_validation_history
  WHERE nct_id = 'NCT00000171' AND validation_run > 10;
  ```

### 5. Temperature 설정

- 검증 시 `temperature=0.0`으로 설정하여 변동성 최소화 시도
- API가 지원하지 않으면 기본 호출로 fallback
- 완전한 결정론은 보장되지 않으므로 다중 검증 필수

### 6. 데이터베이스 연결

- 장시간 실행 시 데이터베이스 연결 타임아웃 가능
- 배치마다 저장하므로 연결이 끊어져도 저장된 배치는 유지
- 재연결 후 `start_batch` 옵션으로 재개 가능

---

## 검증 결과 확인

### 1. 검증 상태 확인

```sql
SELECT
    nct_id,
    llm_validation_status,
    llm_validation_confidence,
    validation_consistency_score,
    validation_count,
    needs_manual_review
FROM inclusion_exclusion_llm_preprocessed
WHERE llm_status = 'SUCCESS'
  AND llm_validation_status IS NOT NULL
ORDER BY nct_id
LIMIT 10;
```

### 2. 검증 이력 확인

```sql
SELECT
    h.validation_run,
    h.validation_status,
    h.validation_confidence,
    h.validation_notes,
    h.created_at
FROM inclusion_exclusion_llm_validation_history h
WHERE h.nct_id = 'NCT00000171'
ORDER BY h.validation_run;
```

### 3. 일관성 점수 통계

```sql
SELECT
    AVG(validation_consistency_score) as avg_consistency,
    COUNT(*) FILTER (WHERE validation_consistency_score >= 0.67) as high_consistency,
    COUNT(*) FILTER (WHERE validation_consistency_score < 0.67) as low_consistency,
    COUNT(*) FILTER (WHERE needs_manual_review = TRUE) as manual_review
FROM inclusion_exclusion_llm_preprocessed
WHERE llm_status = 'SUCCESS'
  AND validation_consistency_score IS NOT NULL;
```

### 4. 리포트 생성

검증 완료 후 자동으로 리포트가 생성됩니다:

```
reports/inclusion_exclusion_validation_YYYYMMDD_HHMMSS.md
```

리포트에는 다음 정보가 포함됩니다:

- 전체 통계
- Study별 통계
- 상태별 상세 통계
- 일관성 점수 통계

---

## 검증 상태 설명

### 검증 상태 종류

- **VERIFIED**: Inclusion과 Exclusion 모두 검증 성공
- **UNCERTAIN**: 불확실 (일부 불일치 또는 애매한 경우)
- **INCLUSION_FAILED**: Inclusion 검증 실패
- **EXCLUSION_FAILED**: Exclusion 검증 실패
- **BOTH_FAILED**: Inclusion과 Exclusion 모두 검증 실패

---

## FAQ

### Q1: 검증 3회할 때 1, 2, 3회차를 다 히스토리에 갖고 있나요?

**A**: 네, 맞습니다. 검증 3회를 수행하면:

- 1회차 검증 결과 → `validation_run = 1`로 저장
- 2회차 검증 결과 → `validation_run = 2`로 저장
- 3회차 검증 결과 → `validation_run = 3`으로 저장

모든 검증 실행 결과가 `inclusion_exclusion_llm_validation_history` 테이블에 저장됩니다.

### Q2: 재검증하면 기존 이력과 합쳐지나요?

**A**: 네, 맞습니다. 재검증 시:

1. 기존 검증 이력을 조회
2. 새로운 검증을 수행
3. 기존 이력 + 새 검증 결과를 합쳐서 Majority Voting
4. 새 검증 결과는 기존 이력 다음 번호부터 저장

예: 기존 3회 + 재검증 3회 = 총 6회 검증 결과로 최종 결정

### Q3: 검증 횟수를 늘리면 더 정확한가요?

**A**: 일반적으로 검증 횟수가 많을수록 일관성 있는 결과를 얻을 수 있습니다. 하지만:

- API 호출 비용 증가
- 처리 시간 증가
- 검증 횟수가 많아도 완전한 일관성은 보장되지 않음

권장: 3~5회

### Q4: 중단되어도 저장된 데이터는 유지되나요?

**A**: 네, 배치마다 DB에 저장하므로 중단되어도 저장된 배치는 유지됩니다. `start_batch` 옵션으로 중단된 지점부터 재개할 수 있습니다.

### Q5: 검증 이력을 삭제할 수 있나요?

**A**: 네, 수동으로 삭제할 수 있습니다:

```sql
-- 특정 nct_id의 모든 이력 삭제
DELETE FROM inclusion_exclusion_llm_validation_history
WHERE nct_id = 'NCT00000171';

-- 특정 nct_id의 일부 이력만 삭제 (예: 10회차 이후)
DELETE FROM inclusion_exclusion_llm_validation_history
WHERE nct_id = 'NCT00000171' AND validation_run > 10;
```

---

## 참고 자료

- 상세 레퍼런스: `docs/llm_validation_reference_guide.md`
- Executive Summary: `docs/llm_validation_executive_summary.md`
- 검증 스크립트: `llm/llm_validate_inclusion_exclusion.py`
- 스키마 SQL: `sql/create_inclusion_exclusion_validation_history.sql`
- 테이블 설계: `docs/inclusion_exclusion_table_design.md`
- 구현 계획: `docs/inclusion_exclusion_implementation_plan.md`

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-24
