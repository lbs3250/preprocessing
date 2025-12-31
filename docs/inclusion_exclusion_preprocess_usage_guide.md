# Inclusion/Exclusion LLM 전처리 스크립트 사용 가이드

생성일시: 2025-01-24

## 목차

1. [개요](#개요)
2. [사전 준비](#사전-준비)
3. [기본 사용법](#기본-사용법)
4. [옵션 설명](#옵션-설명)
5. [처리 모드](#처리-모드)
6. [예시](#예시)
7. [주의사항](#주의사항)

---

## 개요

`llm_preprocess_inclusion_exclusion.py`는 Inclusion/Exclusion Criteria 원시 데이터를 LLM으로 구조화하여 전처리하는 스크립트입니다.

### 주요 기능

- **배치 처리**: 효율적인 API 호출 및 중단 재개 지원
- **자동 재시도**: API 키 로테이션 및 429 에러 처리
- **부분 복구**: 잘린 JSON 응답에서도 데이터 복구 시도
- **다양한 모드**: 누락/실패/전체 처리 모드 지원

---

## 사전 준비

### 1. 데이터베이스 스키마 적용

전처리 결과 테이블을 생성합니다:

```bash
psql -U postgres -d clinicaltrials -f sql/create_inclusion_exclusion_llm_preprocessed.sql
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

### 3. 원시 데이터 수집

전처리 전에 원시 데이터가 `inclusion_exclusion_raw` 테이블에 있어야 합니다:

```bash
python preprocessing/collect_inclusion_exclusion.py
```

---

## 기본 사용법

### 기본 실행 (누락된 항목만 처리)

```bash
python llm/llm_preprocess_inclusion_exclusion.py
```

**기본 설정**:

- 처리 모드: `--missing-only` (누락된 항목만 처리)
- 배치 크기: 100개
- 시작 배치: 1번
- 처리 대상: `inclusion_exclusion_llm_preprocessed`에 없는 항목

---

## 옵션 설명

### 명령줄 인자 형식

```bash
python llm/llm_preprocess_inclusion_exclusion.py [limit] [batch_size] [start_batch] [--failed-only|--missing-only|--all]
```

### 옵션 상세 설명

#### 1. `limit` (첫 번째 인자)

**설명**: 처리할 항목 수 제한

**기본값**: `None` (전체 처리)

**예시**:

```bash
# 100개만 전처리
python llm/llm_preprocess_inclusion_exclusion.py 100
```

#### 2. `batch_size` (두 번째 인자)

**설명**: 배치 크기 (한 번에 처리할 항목 수)

**기본값**: `100` (환경변수 `BATCH_SIZE` 또는 코드 기본값)

**예시**:

```bash
# 배치 크기를 50개로 설정
python llm/llm_preprocess_inclusion_exclusion.py 1000 50
```

**주의사항**:

- 배치 크기가 작을수록 더 자주 저장 (중단 시 손실 적음)
- 배치 크기가 클수록 처리 효율 향상
- 권장: 50~100개

#### 3. `start_batch` (세 번째 인자)

**설명**: 시작할 배치 번호 (중단 재개용)

**기본값**: `1`

**예시**:

```bash
# 10번 배치부터 시작 (1~9번 배치 건너뜀)
python llm/llm_preprocess_inclusion_exclusion.py 1000 100 10
```

**사용 시나리오**:

- 중간에 중단된 경우, 마지막 처리된 배치 다음 번호부터 재개
- 특정 배치부터 다시 처리하고 싶은 경우

#### 4. 처리 모드 (네 번째 인자, 선택사항)

**설명**: 처리할 항목 선택 모드

**기본값**: `--missing-only` (누락된 항목만 처리)

**옵션**:

- `--missing-only`: 누락된 항목만 처리 (기본값)
- `--failed-only`: 실패한 항목만 재처리
- `--all`: 전체 처리 (기존 SUCCESS 항목은 보호됨)

**예시**:

```bash
# 실패한 항목만 재처리
python llm/llm_preprocess_inclusion_exclusion.py --failed-only

# 전체 처리 (기존 SUCCESS 항목은 보호됨)
python llm/llm_preprocess_inclusion_exclusion.py --all

# 옵션 조합
python llm/llm_preprocess_inclusion_exclusion.py 1000 50 1 --failed-only
```

---

## 처리 모드

### 1. `--missing-only` (기본값)

**설명**: `inclusion_exclusion_llm_preprocessed` 테이블에 없는 항목만 처리

**사용 시나리오**:

- 처음 전처리를 시작할 때
- 새로 수집된 원시 데이터만 처리하고 싶을 때

**SQL 쿼리**:

```sql
SELECT
    ier.nct_id,
    ier.eligibility_criteria_raw,
    ier.phase
FROM inclusion_exclusion_raw ier
LEFT JOIN inclusion_exclusion_llm_preprocessed iep
    ON ier.nct_id = iep.nct_id
WHERE iep.nct_id IS NULL
ORDER BY ier.nct_id
```

### 2. `--failed-only`

**설명**: 이전에 실패한 항목만 재처리 (`llm_status != 'SUCCESS'`)

**사용 시나리오**:

- 이전에 실패한 항목을 다시 시도하고 싶을 때
- API 문제로 일부 항목이 실패했을 때

**SQL 쿼리**:

```sql
SELECT
    ier.nct_id,
    ier.eligibility_criteria_raw,
    ier.phase
FROM inclusion_exclusion_raw ier
INNER JOIN inclusion_exclusion_llm_preprocessed iep
    ON ier.nct_id = iep.nct_id
WHERE iep.llm_status != 'SUCCESS'
ORDER BY ier.nct_id
```

### 3. `--all`

**설명**: 전체 항목 처리 (기존 SUCCESS 항목은 보호됨)

**사용 시나리오**:

- 전체 데이터를 다시 처리하고 싶지만, 기존 SUCCESS 항목은 유지하고 싶을 때
- INSERT 시 CASE 문으로 기존 SUCCESS 항목은 덮어쓰지 않음

**SQL 쿼리**:

```sql
SELECT
    nct_id,
    eligibility_criteria_raw,
    phase
FROM inclusion_exclusion_raw
ORDER BY nct_id
```

**주의**: `--all` 모드에서도 기존 SUCCESS 항목은 INSERT 시 보호되므로, 실패한 항목만 재처리됩니다.

---

## 예시

### 예시 1: 소규모 테스트 (10개)

```bash
python llm/llm_preprocess_inclusion_exclusion.py 10
```

**출력 예시**:

```
[INFO] 처리 모드: 누락된 항목만 처리
[INFO] 처리할 항목: 10개
[STEP 1] LLM 전처리 시작 (배치 크기: 100)...
  배치 1/1 처리 중: 1~10번째 항목
  배치 1 결과 저장 중... (10개)
```

### 예시 2: 대규모 처리 (1000개, 배치 크기 50)

```bash
python llm/llm_preprocess_inclusion_exclusion.py 1000 50
```

**출력 예시**:

```
[INFO] 처리 모드: 누락된 항목만 처리
[INFO] 배치 크기를 50개로 조정했습니다.
[INFO] 처리할 항목: 1,000개
[STEP 1] LLM 전처리 시작 (배치 크기: 50)...
  배치 1/20 처리 중: 1~50번째 항목
  배치 1 결과 저장 중... (50개)
  배치 2/20 처리 중: 51~100번째 항목
  ...
```

### 예시 3: 중단 재개 (배치 10번부터)

```bash
python llm/llm_preprocess_inclusion_exclusion.py 1000 100 10
```

**출력 예시**:

```
[INFO] 배치 10번부터 시작합니다.
[STEP 1] LLM 전처리 시작...
  배치 1/10 건너뜀 (start_batch=10)
  배치 2/10 건너뜀 (start_batch=10)
  ...
  배치 10/10 처리 중: 901~1000번째 항목
```

### 예시 4: 실패한 항목만 재처리

```bash
python llm/llm_preprocess_inclusion_exclusion.py --failed-only
```

**출력 예시**:

```
[INFO] 처리 모드: 실패한 항목만 재처리
[INFO] 처리할 항목: 234개
[STEP 1] LLM 전처리 시작 (배치 크기: 100)...
  배치 1/3 처리 중: 1~100번째 항목
  ...
```

### 예시 5: 전체 처리 (기존 SUCCESS 보호)

```bash
python llm/llm_preprocess_inclusion_exclusion.py --all
```

**출력 예시**:

```
[INFO] 처리 모드: 전체 처리 (기존 SUCCESS 항목은 보호됨)
[INFO] 처리할 항목: 15,234개
[STEP 1] LLM 전처리 시작 (배치 크기: 100)...
  배치 1/153 처리 중: 1~100번째 항목
  ...
```

### 예시 6: 옵션 조합

```bash
# 실패한 항목 500개, 배치 크기 50, 5번 배치부터 시작
python llm/llm_preprocess_inclusion_exclusion.py 500 50 5 --failed-only
```

---

## 주의사항

### 1. API 호출 비용

- 배치 크기와 처리 항목 수에 따라 API 호출 횟수 결정
- 예: 10,000개 항목 ÷ 배치 크기 100 = 100회 API 호출
- 권장: 테스트 시 `limit` 옵션으로 소규모 테스트 먼저 수행

### 2. 처리 시간

- 배치 크기와 Rate limiting에 따라 처리 시간 결정
- Rate limiting으로 인해 배치 간 대기 시간 발생
- 예상 시간: (항목 수 ÷ 배치 크기) × (API 호출 시간 + 대기 시간)

### 3. 중단 재개

- 배치마다 DB에 저장하므로 중단되어도 저장된 배치는 유지
- 중단된 지점부터 재개하려면 `start_batch` 옵션 사용
- 마지막 처리된 배치 번호 확인:
  ```sql
  SELECT COUNT(*) / 100 as last_batch
  FROM inclusion_exclusion_llm_preprocessed;
  ```

### 4. API 키 관리

- 여러 API 키를 설정하면 자동으로 로테이션
- 429 에러 발생 시 다음 키로 자동 전환
- 모든 키가 소진되면 처리 중단

### 5. 부분 복구

- 잘린 JSON 응답에서도 완전한 객체를 추출 시도
- 부분 복구된 항목은 `llm_notes`에 `[PARTIAL_RECOVERED]` 태그 추가
- 부분 복구는 성공으로 간주되지 않음 (재처리 권장)

### 6. 데이터베이스 연결

- 장시간 실행 시 데이터베이스 연결 타임아웃 가능
- 배치마다 저장하므로 연결이 끊어져도 저장된 배치는 유지
- 재연결 후 `start_batch` 옵션으로 재개 가능

### 7. 처리 모드 주의사항

- `--missing-only`: 처음 전처리 시 사용 권장
- `--failed-only`: 실패한 항목만 재처리할 때 사용
- `--all`: 기존 SUCCESS 항목은 보호되지만, 실패한 항목은 재처리됨

---

## 처리 결과 확인

### 1. 상태별 통계 확인

```sql
SELECT
    llm_status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM inclusion_exclusion_llm_preprocessed
GROUP BY llm_status
ORDER BY count DESC;
```

### 2. 추출 통계 확인

```sql
SELECT
    COUNT(*) as total,
    COUNT(inclusion_criteria) as with_inclusion,
    COUNT(exclusion_criteria) as with_exclusion,
    COUNT(CASE WHEN inclusion_criteria IS NOT NULL AND exclusion_criteria IS NOT NULL THEN 1 END) as complete
FROM inclusion_exclusion_llm_preprocessed;
```

### 3. 실패 항목 확인

```sql
SELECT
    nct_id,
    llm_status,
    failure_reason,
    llm_notes
FROM inclusion_exclusion_llm_preprocessed
WHERE llm_status != 'SUCCESS'
ORDER BY nct_id
LIMIT 10;
```

### 4. 부분 복구 항목 확인

```sql
SELECT
    nct_id,
    llm_status,
    llm_notes
FROM inclusion_exclusion_llm_preprocessed
WHERE llm_notes LIKE '%PARTIAL_RECOVERED%'
ORDER BY nct_id;
```

---

## 처리 상태 설명

### 처리 상태 종류

- **SUCCESS**: Inclusion과 Exclusion 모두 구조화 성공
- **INCLUSION_FAILED**: Inclusion 구조화 실패
- **EXCLUSION_FAILED**: Exclusion 구조화 실패
- **BOTH_FAILED**: Inclusion과 Exclusion 모두 구조화 실패
- **API_FAILED**: API 호출 실패

---

## FAQ

### Q1: 중단되어도 저장된 데이터는 유지되나요?

**A**: 네, 배치마다 DB에 저장하므로 중단되어도 저장된 배치는 유지됩니다. `start_batch` 옵션으로 중단된 지점부터 재개할 수 있습니다.

### Q2: 실패한 항목을 다시 처리하려면?

**A**: `--failed-only` 모드를 사용하세요:

```bash
python llm/llm_preprocess_inclusion_exclusion.py --failed-only
```

### Q3: 기존 SUCCESS 항목을 덮어쓰고 싶어요

**A**: `--all` 모드를 사용하되, INSERT 로직에서 기존 SUCCESS 항목은 보호됩니다. 완전히 덮어쓰려면 수동으로 삭제 후 재처리하세요:

```sql
DELETE FROM inclusion_exclusion_llm_preprocessed WHERE nct_id = 'NCT00000171';
```

그 후:

```bash
python llm/llm_preprocess_inclusion_exclusion.py --missing-only
```

### Q4: 부분 복구된 항목은 어떻게 처리하나요?

**A**: 부분 복구된 항목은 `llm_notes`에 `[PARTIAL_RECOVERED]` 태그가 있습니다. 재처리를 권장합니다:

```sql
-- 부분 복구 항목을 실패 상태로 변경
UPDATE inclusion_exclusion_llm_preprocessed
SET llm_status = 'BOTH_FAILED'
WHERE llm_notes LIKE '%PARTIAL_RECOVERED%';
```

그 후 `--failed-only` 모드로 재처리:

```bash
python llm/llm_preprocess_inclusion_exclusion.py --failed-only
```

### Q5: 배치 크기를 어떻게 결정하나요?

**A**:

- **작은 배치 (50개)**: 중단 시 손실 적음, 더 자주 저장
- **큰 배치 (100개)**: 처리 효율 향상, 중단 시 손실 큼
- 권장: 50~100개

### Q6: API 키가 모두 소진되면?

**A**: 처리가 중단됩니다. 새로운 API 키를 추가하거나 기존 키의 할당량이 리셋될 때까지 대기하세요.

---

## 참고 자료

- 테이블 설계: `docs/inclusion_exclusion_table_design.md`
- 구현 계획: `docs/inclusion_exclusion_implementation_plan.md`
- 전처리 스크립트: `llm/llm_preprocess_inclusion_exclusion.py`
- 스키마 SQL: `sql/create_inclusion_exclusion_llm_preprocessed.sql`
- 데이터 수집 스크립트: `preprocessing/collect_inclusion_exclusion.py`

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-24
