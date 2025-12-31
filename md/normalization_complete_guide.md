# ClinicalTrials.gov Outcome 정규화 완전 가이드

최신 코드 기준 (2025-12-17)

---

## 목차

1. [Measure Code 정규화 플로우](#1-measure-code-정규화-플로우)
2. [Dictionary 구조 및 매칭](#2-dictionary-구조-및-매칭)
3. [정규화된 데이터 구조](#3-정규화된-데이터-구조)
4. [Timeframe 파싱 플로우](#4-timeframe-파싱-플로우)
5. [패턴 코드 시스템](#5-패턴-코드-시스템)
6. [데이터 분리 및 성공/실패 기준](#6-데이터-분리-및-성공실패-기준)

---

## 1. Measure Code 정규화 플로우

### 1.1 전체 플로우 개요

```
measure_raw
  ↓ [텍스트 클리닝]
measure_clean
  ↓ [약어 추출]
measure_abbreviation (후보)
  ↓ [Dictionary 매칭]
measure_code + match_type + match_keyword
```

### 1.2 텍스트 클리닝

**함수:** `clean_text()`

**처리 내용:**
- 공백 정리 (연속 공백 → 단일 공백)
- 오타 교정 (`extention` → `extension`)

**예시:**
- Input: `"Changes  in   CDR (Clinical Dementia Rate)"`
- Output: `"Changes in CDR (Clinical Dementia Rate)"`

### 1.3 약어 추출 규칙

**정규식 패턴:** `\([A-Za-z][A-Za-z0-9\-+\s/]+\)`

#### 케이스 1: 괄호 0개
- **결과:** 약어 없음 (`measure_abbreviation = None`)
- **다음 단계:** `measure_clean` 전체를 Dictionary와 매칭 시도

#### 케이스 2: 괄호 1개
- **처리:**
  1. 괄호 안 텍스트 확인
  2. 괄호 전 마지막 단어 확인
  3. 둘 중 유효한 약어 선택

**세부 규칙:**
- **괄호 안에 "and" 또는 "or"가 있는 경우:**
  - 복수 약어로 분리: `"ADAS-Cog11 and ADAS-Cog12"` → `["ADAS-Cog11", "ADAS-Cog12"]`
  - 각각을 후보로 추가

- **괄호 안이 유효한 약어인 경우:**
  - `measure_abbreviation = "(약어)"` (괄호 포함)

- **괄호 전 마지막 단어가 유효한 약어인 경우:**
  - 후보로 저장: `[괄호 전 약어, 괄호 안 fullname]`
  - Dictionary 매칭 후 결정

**예시:**
- `"CDR (Clinical Dementia Rate)"` → 괄호 전 "CDR"이 약어
- `"Clinical Dementia Rate (CDR)"` → 괄호 안 "CDR"이 약어
- `"ADAS-Cog11 and ADAS-Cog12"` → 두 약어 모두 후보

#### 케이스 3: 괄호 2개 이상
- **처리:**
  1. 모든 괄호 안 텍스트를 후보로 수집
  2. 모두 대문자인 약어를 우선적으로 선택
  3. Dictionary 매칭 시도

**우선순위:**
1. 모두 대문자인 약어 (`all_uppercase_candidates`)
2. 나머지 약어 (`other_candidates`)

**예시:**
- `"Alanine aminotransferase (ALT) (Safety assessments)"`
  - 후보: `["(ALT)", "(Safety assessments)"]`
  - `ALT`가 모두 대문자이므로 우선 선택

### 1.4 유효한 약어 판별

**함수:** `is_valid_abbreviation()`

**필터링 조건 (제외되는 경우):**
1. 단위 패턴: `ml/d`, `ng/ml`, `mg/kg` 등
2. 시간/파트 패턴: `Week 1`, `Part 1`, `Day 1`, `W0` 등
3. Arms/Cohorts 패턴: `Arms 1 and 2`, `Cohorts A and B` 등
4. 숫자만 있는 경우: `(1)`, `(2)` 등
5. 의미없는 패턴:
   - `(screening)`, `(baseline)`, `(participant)`
   - `(post-study)`, `(pre-dose)`, `(safety assessment)`
   - `(safety assessments)`, `(efficacy assessments)`
   - `(end of period)`
6. 너무 짧은 경우 (1-2자, 알파벳만 있는 경우는 허용)

### 1.5 Dictionary 매칭 우선순위

#### 0순위: measure_code 직접 매칭 (가장 강함)
- **대상:** `measure_clean` 전체
- **매칭 방식:** 정규화 후 완전 일치
- **정규화:** 대소문자, 공백, 하이픈 무시
- **match_type:** `MEASURE_CODE`

**예시:**
- `measure_clean`: `"ADAS-Cog"`
- Dictionary `measure_code`: `"ADAS-Cog"`
- → 매칭 성공

#### 1순위: abbreviation 매칭
- **대상:** 추출된 약어 (`measure_abbreviation`)
- **매칭 방식:**
  1. Dictionary `abbreviation` 필드와 완전 일치
  2. Dictionary `keywords` 필드와 완전 일치
- **정규화:** 대소문자, 공백, 하이픈 무시
- **match_type:** `ABBREVIATION` 또는 `KEYWORD`

**약어 후보가 여러 개인 경우:**
- 모두 대문자인 약어를 우선적으로 매칭 시도
- 매칭되는 첫 번째 약어 사용

#### 2순위: canonical_name 매칭
- **대상:** `measure_clean` 전체
- **매칭 방식:**
  1. 완전 일치
  2. 부분 포함 (최소 5자 이상)
- **정규화:** 대소문자, 공백, 하이픈 무시
- **match_type:** `CANONICAL_NAME`

**예시:**
- `measure_clean`: `"Alzheimer's Disease Assessment Scale"`
- Dictionary `canonical_name`: `"Alzheimer Disease Assessment Scale"`
- → 부분 포함 매칭 성공

#### 3순위: keywords 매칭
- **대상:** `measure_clean` 전체
- **매칭 방식:**
  1. 완전 일치
  2. 부분 포함 (최소 3자 이상, 단어 경계 고려)
- **정규화:** 대소문자, 공백, 하이픈 무시
- **match_type:** `KEYWORD`

**단어 경계 고려:**
- `"ESS"`는 `"Epworth Sleepiness Scale"`의 `"ESS"`와 매칭
- `"ESS"`는 `"goodness"`와 매칭 안 됨

#### 4순위: description_raw에서 매칭 시도
- **조건:** 0, 1, 2, 3순위에서 모두 실패한 경우만
- **대상:** `description_raw` (클리닝 후)
- **매칭 순서:**
  1. measure_code 직접 매칭
  2. canonical_name 매칭
  3. keywords 매칭
- **match_type:** `MEASURE_CODE`, `CANONICAL_NAME`, 또는 `KEYWORD`

### 1.6 매칭 실패 처리

**모든 순위에서 매칭 실패한 경우:**
- `measure_code = None`
- `match_type = None`
- `match_keyword = None`
- `failure_reason`에 `MEASURE_CODE_FAILED` 또는 `BOTH_FAILED` 설정

**약어 추출은 성공했지만 Dictionary 매칭 실패:**
- `measure_abbreviation`은 저장됨 (나중에 Dictionary 업데이트 시 활용 가능)
- `measure_code`는 `None`

---

## 2. Dictionary 구조 및 매칭

### 2.1 Dictionary 테이블 구조

**테이블명:** `outcome_measure_dict`

**컬럼:**
- `measure_code` (VARCHAR(50), PRIMARY KEY): 고유 식별자
- `canonical_name` (TEXT, NOT NULL): 정식 명칭
- `abbreviation` (VARCHAR(100)): 약어 (선택적)
- `keywords` (TEXT): 세미콜론(`;`)으로 구분된 키워드 리스트
- `domain` (VARCHAR(100)): 도메인 분류
- `typical_role` (VARCHAR(50)): PRIMARY, SECONDARY, BOTH, SUPPORTIVE 등
- `created_at`, `updated_at`: 타임스탬프

**예시 데이터:**
```sql
measure_code: "ADAS-Cog"
canonical_name: "Alzheimer Disease Assessment Scale-Cognitive Subscale"
abbreviation: "ADAS-Cog"
keywords: "ADAS-Cog;ADAS-Cog11;ADAS-Cog12;ADAS-Cog13;ADAS-Cog14;ADAS-Jcog;ADAS-JCog;ADAS-NonCog;ADAs"
domain: "Cognitive"
typical_role: "PRIMARY"
```

### 2.2 Dictionary 매칭 로직

**정규화 함수:** `normalize_for_matching()`
- 소문자 변환
- 공백, 하이픈, 언더스코어 제거
- 특수문자 제거 (알파벳, 숫자만 남김)

**예시:**
- Input: `"ADAS-Cog 11"`
- Output: `"adascog11"`

**매칭 방식:**
- 정규화된 텍스트끼리 비교
- 완전 일치 또는 부분 포함 체크

---

## 3. 정규화된 데이터 구조

### 3.1 테이블 구조

**테이블명:** `outcome_normalized`

**주요 컬럼:**

#### Measure 관련
- `measure_raw` (TEXT): 원본 measure 텍스트
- `measure_clean` (TEXT): 클리닝된 measure 텍스트
- `measure_abbreviation` (TEXT): 추출된 약어 (괄호 포함)
- `measure_norm` (VARCHAR(200)): Dictionary의 canonical_name
- `measure_code` (VARCHAR(50)): Dictionary의 measure_code (FK)
- `match_type` (VARCHAR(20)): 매칭 타입 (`MEASURE_CODE`, `ABBREVIATION`, `KEYWORD`, `CANONICAL_NAME`)
- `match_keyword` (TEXT): 매칭에 사용된 키워드/텍스트
- `domain` (VARCHAR(100)): Dictionary의 domain

#### Timeframe 관련
- `time_frame_raw` (TEXT): 원본 timeframe 텍스트
- `time_value_main` (NUMERIC): 대표 시점 값
- `time_unit_main` (VARCHAR(20)): 대표 시점 단위 (`day`, `week`, `month`, `year`, `hour`, `minute`)
- `time_points` (JSONB): 복수 시점 배열 `[{"value": 12, "unit": "week"}, ...]`
- `time_phase` (VARCHAR(50)): Phase 태깅 (`double-blind`, `open-label`, `extension`, `follow-up`, `maintenance`)
- `change_from_baseline_flag` (BOOLEAN): Baseline 포함 여부
- `pattern_code` (VARCHAR(20)): Timeframe 정규화 패턴 코드 (`PATTERN1` ~ `PATTERN15`)

#### 기타
- `nct_id` (VARCHAR(20)): Study 식별자
- `outcome_type` (VARCHAR(10)): `PRIMARY` 또는 `SECONDARY`
- `outcome_order` (INTEGER): Outcome 순서
- `phase` (VARCHAR(50)): Study phase (`PHASE1`, `PHASE2`, `PHASE3`, `PHASE4`, `NA`)
- `description_raw` (TEXT): 원본 description 텍스트
- `description_norm` (TEXT): 정규화된 description 텍스트
- `failure_reason` (VARCHAR(50)): 실패 원인 (`MEASURE_FAILED`, `TIMEFRAME_FAILED`, `BOTH_FAILED`, `NULL`=성공)
- `parsing_method` (VARCHAR(20)): 파싱 방법 (`RULE_BASED`, `LLM`)
- `num_arms` (INTEGER): Study의 arm 개수

### 3.2 데이터 분리 테이블

**성공 테이블:** `outcome_normalized_success`
- 조건: `measure_code IS NOT NULL AND failure_reason IS NULL`

**실패 테이블:** `outcome_normalized_failed`
- 조건: `measure_code IS NULL OR failure_reason IS NOT NULL`

---

## 4. Timeframe 파싱 플로우

### 4.1 전체 플로우 개요

```
time_frame_raw
  ↓ [패턴 코드 추출]
pattern_code (PATTERN1~PATTERN15)
  ↓ [단일/복수 시점 판별]
  ├─ 단일 시점 → time_value_main + time_unit_main
  └─ 복수 시점 → time_points (JSONB 배열)
  ↓ [대표값 선정]
time_value_main, time_unit_main
```

### 4.2 단일/복수 시점 판별

**함수:** `is_single_timepoint()`

**단일 시점 판별 기준:**
- 쉼표(`,`) 없음
- "and" 없음 (단, "and"가 단위 뒤에 오는 경우는 복수로 간주)
- 단일 숫자+단위 패턴

**복수 시점 판별 기준:**
- 쉼표로 구분된 숫자들
- "and"로 연결된 숫자들
- 여러 단위가 혼용된 경우

### 4.3 단일 시점 파싱 순서

**함수:** `parse_timeframe()`

**파싱 순서 (우선순위):**

1. **"At Day/Week/Month/Hour/Minute N" 패턴**
   - 정규식: `at\s+(day|days|week|weeks|month|months|hour|hours|min|mins|minute|minutes)\s+(\d+)`
   - 예시: `"At Day 7"`, `"At Week 12"`, `"At Month 6"`

2. **"Day N", "Month N", "Week N" 단독 패턴**
   - 정규식: `\b(day|days|month|months|week|weeks|hour|hours|min|mins|minute|minutes|wk|w)\s*-?\s*(\d+)`
   - 예시: `"Day 14"`, `"Week 24"`, `"Wk 50"`, `"W24"`, `"6th month"`, `"8-weeks"`, `"30 minutes"`

3. **"For N Months/Weeks/Days/Minutes" 패턴**
   - 정규식: `for\s+(\d+)\s+(month|months|week|weeks|day|days|hour|hours|min|mins|minute|minutes)`
   - 예시: `"For 12 weeks"`, `"For 6 months"`, `"For 30 minutes"`

4. **텍스트 숫자 패턴**
   - `"A year"`, `"A minute"` → 1 year/minute
   - `"year three"`, `"month two"` → 3 year, 2 month
   - `"Two years"`, `"eight weeks"`, `"thirty minutes"`

5. **숫자+단위 패턴 (가장 일반적)**
   - 정규식: `(\d+)\s*-?\s*(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes|wk|w)`
   - 예시: `"26 weeks"`, `"96-week"`, `"21-months"`, `"48 hr"`, `"30 minutes"`, `"2 min"`

6. **Year N 패턴**
   - 정규식: `year\s*(\d+)`
   - 예시: `"Year 1"`, `"Year 3.5"`
   - 주의: `year 2006-2008` 같은 년도 범위는 실패 처리

7. **"Up to Day/Week/Month N" 패턴**
   - 정규식: `up\s*to\s+(day|days|week|weeks|month|months|year|years)\s+(\d+)`
   - 예시: `"Up to Day 162"`, `"Upto Week 48"`

8. **"Up to N" 패턴**
   - 정규식: `up\s*to\s+(\d+)\s*(week|weeks|month|months|year|years|day|days|hour|hours)`
   - 예시: `"Up to 12"`

9. **"Through study completion" 패턴**
   - 정규식: `through.*?(?:average\s+of\s+)?(\d+)\s*(week|weeks|month|months|year|years)`
   - 예시: `"Through study completion"`

### 4.4 복수 시점 파싱

**함수:** `parse_multiple_timepoints()`

**파싱 순서 (우선순위):**

1. **단위-first 복수 시점 패턴**
   - 정규식: `\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes|wk|w)\s+\d+(?:\s*\([^)]*\))?(?:\s*,\s*\d+(?:\s*\([^)]*\))?)*(?:\s*,\s*)?\s+and\s+\d+`
   - 예시: `"weeks 9, 17, 25 and 37"`, `"Days 84, 169, 253, 421, 505, 589, and 757"`

2. **N and M unit 패턴**
   - 정규식: `(\d+)\s+and\s+(\d+)\s+(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)`
   - 예시: `"12 and 24 weeks"`, `"6 and 12 months"`

3. **단위 + N-M 범위 패턴**
   - 정규식: `\b(\d+)\s*-\s*(\d+)\s+(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)`
   - 예시: `"Day 1-7"` → 최대값만 추출 (`7`)
   - 예시: `"60-90 minutes"` → 최대값만 추출 (`90 minutes`)

4. **단위 + N 패턴 (단일 시점과 동일)**
   - 예시: `"Day 14"`, `"Week 24"`

5. **N + 단위 패턴 (단일 시점과 동일)**
   - 예시: `"26 weeks"`, `"48 hr"`

6. **N-M + 단위 패턴**
   - 정규식: `(\d+)\s*-\s*(\d+)\s+(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes)`
   - 예시: `"60-90 minutes"` → 최대값만 추출 (`90 minutes`)

7. **숫자 리스트 + 마지막 단위 패턴**
   - 조건: 앞 패턴에서 충분히 추출되지 않았을 때만
   - 조건: 단위 혼용이 없어야 함 (`units_extracted <= 1`)
   - 예시: `"baseline, 5, 30, 60, and 180 min"` → 마지막 단위(`min`)를 모든 숫자에 적용

### 4.5 단위 정규화

**함수:** `normalize_unit()`

**정규화 규칙:**
- 복수형 제거 후 소문자화
- `hr`, `hrs`, `h` → `hour`
- `min`, `mins`, `minute`, `minutes` → `minute`
- `wk`, `w` → `week`

**예시:**
- `weeks` → `week`
- `days` → `day`
- `months` → `month`
- `years` → `year`
- `hr`, `hrs`, `h` → `hour`
- `min`, `mins`, `minutes` → `minute`

### 4.6 최종 처리 로직

#### time_points 정제
1. `value`가 숫자인 것만 유지 (`int`/`float`)
2. `{value, unit}` 중복 제거
3. 정렬: `(value ASC, unit ASC)`
4. 숫자 상한 제한 없음 (예: `8736 hours` = `52 weeks` 가능)
5. 단, `year` 단위에서 `1900` 이상은 "년도"로 간주하여 실패 처리

#### 대표값 선정
- **단일 unit:** `max(value)`
- **혼용 unit:** hour 환산 후 최대값 선택

**단위 변환 가중치 (hour 기준):**
- `minute`: × 1/60
- `hour`: × 1
- `day`: × 24
- `week`: × 168
- `month`: × 730
- `year`: × 8760

**예시:**
- `time_points`: `[{"value": 14, "unit": "day"}, {"value": 24, "unit": "week"}]`
- hour 환산: `14 day = 336 hours`, `24 week = 4032 hours`
- `time_value_main = 24`, `time_unit_main = "week"`

### 4.7 Baseline 처리

**Baseline 감지:**
- 정규식: `\bbaseline\b`
- `change_from_baseline_flag = TRUE` 설정

**Baseline만 있는 경우:**
- 숫자나 단위가 없으면 → `0 day`로 처리
- `time_value_main = 0`, `time_unit_main = "day"`

**Baseline + 숫자 리스트:**
- 예시: `"baseline, 5, 30, 60, and 180 min"`
- `time_points`: `[{"value": 0, "unit": "day"}, {"value": 5, "unit": "minute"}, ...]`

### 4.8 Phase 태깅

**키워드 매핑:**
- `double-blind` → `"double-blind"`
- `open-label` → `"open-label"`
- `extension` → `"extension"`
- `follow-up`, `followup` → `"follow-up"`
- `maintenance` → `"maintenance"`

**예시:**
- `"At Week 12 (double-blind phase)"` → `time_phase = "double-blind"`

### 4.9 필터링 및 실패 처리

**필터링 (제외):**
- 약물 코드: `PF-04447943`, `MK-8931` 등
- Dose: 숫자 뒤 `mg`, `g`, `ml`, `kg`, `mcg`, `μg`, `iu`, `units` 등

**실패 처리:**
- `time_points`가 끝까지 비어있음
- `year` 단위 + `value >= 1900` 포함 (년도 범위)
- 필터링 후 유효 시점이 남지 않음
- `failure_reason = "TIMEFRAME_FAILED"` 또는 `"BOTH_FAILED"`

---

## 5. 패턴 코드 시스템

### 5.1 패턴 코드 개요

**목적:** 어떤 정규식 패턴에 의해 timeframe이 정규화되었는지 추적

**저장 위치:** `outcome_normalized.pattern_code` 컬럼

**값:** `PATTERN1` ~ `PATTERN15` 또는 `NULL`

### 5.2 패턴 코드 목록

| 패턴 코드 | 패턴 타입 | 정규식 | 우선순위 |
|-----------|-----------|--------|----------|
| PATTERN1 | baseline | `\bbaseline\b` | 1 |
| PATTERN2 | at_day_week_month | `\bat\s+(day|days|week|weeks|month|months)\s+\d+` | 2 |
| PATTERN3 | day_month_week_standalone | `\b(day|days|month|months|week|weeks)\s+\d+` | 3 |
| PATTERN4 | day_to_through | `\bday\s+\d+\s+(to|through)\s+(day\s+)?\d+` | 4 |
| PATTERN5 | for_period | `\bfor\s+\d+\s+(month|months|week|weeks|day|days|hour|hours|min|mins|minute|minutes)` | 5 |
| PATTERN6 | at_months_and | `\bat\s+months?\s+\d+\s+and\s+\d+` | 6 |
| PATTERN7 | year | `year\s*\d+` | 7 |
| PATTERN8 | upto_with_unit | `up\s*to\s+(day|days|week|weeks|month|months|year|years)\s+\d+` | 8 |
| PATTERN9 | upto | `up\s*to\s+\d+` | 9 |
| PATTERN10 | multiple_timepoints | `(week|weeks|day|days|month|months)\s+\d+.*?,\s*(week|weeks|day|days|month|months)\s+\d+` | 10 |
| PATTERN11 | through | `through\s+(study|completion|end)` | 11 |
| PATTERN12 | text_number | `\b(one|two|three|...)\s+(week|weeks|month|months|...)\b` | 12 |
| PATTERN13 | period | `\d+\s*-?\s*(week|weeks|month|months|day|days|hour|hours|hr|hrs|min|mins|minute|minutes)` | 13 |
| PATTERN14 | percent | `%\|percent\|percentage` | 14 |
| PATTERN15 | time | `time\s+to\s+(respond|complete|finish)` | 15 |

**자세한 내용:** `md/timeframe_patterns_documentation.md` 참조

### 5.3 패턴 코드 추출

**함수:** `TimeFramePatterns.get_pattern_code()`

**로직:**
1. `classify_timeframe()`으로 패턴 타입 확인
2. 패턴 타입을 패턴 코드로 매핑
3. 매칭 실패 시 `NULL` 반환

---

## 6. 데이터 분리 및 성공/실패 기준

### 6.1 성공 기준

**개별 Outcome 단위:**
- `measure_code IS NOT NULL` (Dictionary 매칭 성공)
- `failure_reason IS NULL` (timeframe 파싱 성공)

**결과:**
- `outcome_normalized_success` 테이블에 저장

### 6.2 실패 기준

**개별 Outcome 단위:**
- `measure_code IS NULL` (Dictionary 매칭 실패)
- 또는 `failure_reason IS NOT NULL` (timeframe 파싱 실패)

**failure_reason 값:**
- `MEASURE_FAILED`: Measure Code 매칭 실패
- `TIMEFRAME_FAILED`: Timeframe 파싱 실패
- `BOTH_FAILED`: 둘 다 실패

**결과:**
- `outcome_normalized_failed` 테이블에 저장

### 6.3 데이터 분리 스크립트

**파일:** `separate_normalized_data.py`

**처리 내용:**
1. `outcome_normalized_success` 테이블 생성 (`LIKE outcome_normalized INCLUDING ALL`)
2. `outcome_normalized_failed` 테이블 생성 (`LIKE outcome_normalized INCLUDING ALL`)
3. 성공한 outcome 분리
4. 실패한 outcome 분리
5. 통계 출력

---

## 부록

### A. 정규화 프로세스 (테이블 흐름)

```
outcome_raw (원본 데이터)
  ↓ [normalize_phase1.py]
outcome_normalized (정규화된 모든 데이터)
  ↓ [separate_normalized_data.py]
  ├─ outcome_normalized_success (성공)
  └─ outcome_normalized_failed (실패)
```

### B. 주요 함수 목록

**Measure 정규화:**
- `clean_text()`: 텍스트 클리닝
- `normalize_for_matching()`: 매칭용 정규화
- `is_valid_abbreviation()`: 유효한 약어 판별

**Timeframe 정규화:**
- `parse_timeframe()`: 단일/복수 시점 파싱
- `parse_multiple_timepoints()`: 복수 시점 파싱
- `is_single_timepoint()`: 단일 시점 판별
- `normalize_unit()`: 단위 정규화
- `TimeFramePatterns.get_pattern_code()`: 패턴 코드 추출

**기타:**
- `check_change_from_baseline()`: Baseline 패턴 확인
- `normalize_batch()`: 배치 정규화 처리

### C. 참고 문서

- `md/timeframe_patterns_documentation.md`: Timeframe 패턴 상세 문서
- `sql/schema.sql`: 데이터베이스 스키마 정의
- `normalize_phase1.py`: 정규화 메인 스크립트
- `normalization_patterns.py`: 정규식 패턴 정의

---

**최종 업데이트:** 2025-12-17







