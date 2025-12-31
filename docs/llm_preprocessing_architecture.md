# LLM 기반 전처리 시스템 개발 문서

## 목차

1. [시스템 개요](#시스템-개요)
2. [아키텍처](#아키텍처)
3. [주요 컴포넌트](#주요-컴포넌트)
4. [데이터 흐름](#데이터-흐름)
5. [프롬프트 구조](#프롬프트-구조)
6. [검증 프로세스](#검증-프로세스)
7. [사용 방법](#사용-방법)
8. [주요 함수 설명](#주요-함수-설명)

---

## 시스템 개요

LLM 기반 전처리 시스템은 `outcome_raw` 테이블의 원본 데이터를 LLM(Gemini)을 사용하여 구조화된 데이터로 변환하는 시스템입니다.

### 주요 기능

- **Measure Code 추출**: `measure_raw`, `description_raw`에서 표준 measure_code 추출
- **Time 정보 추출**: `time_frame_raw`에서 time_value, time_unit, time_points 추출
- **검증**: 추출된 결과를 LLM으로 검증하여 정확성 확인
- **문서화**: 검증 결과를 MD 파일로 리포트 생성

### 기술 스택

- **LLM**: Google Gemini 1.5 Flash
- **데이터베이스**: PostgreSQL
- **언어**: Python 3.x
- **주요 라이브러리**: `psycopg2`, `google-genai`, `python-dotenv`

---

## 아키텍처

```
┌─────────────────┐
│  outcome_raw    │  원본 데이터
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  llm_preprocess_full.py        │  LLM 전처리
│  - 배치 처리                    │
│  - API 키 관리                  │
│  - JSON 파싱 및 복구            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  outcome_llm_preprocessed        │  전처리 결과 저장
│  - llm_measure_code             │
│  - llm_time_value/unit/points   │
│  - llm_status                   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  llm_validate_preprocessed_     │  검증
│  success.py                     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  generate_llm_preprocessed_      │  리포트 생성
│  report.py                     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  reports/*.md                   │  검증 리포트
└─────────────────────────────────┘
```

---

## 주요 컴포넌트

### 1. `llm_config.py`

**역할**: Gemini API 설정 및 관리

**주요 기능**:

- 여러 API 키 관리 (GEMINI_API_KEY, GEMINI_API_KEY_2, ...)
- API 키 자동 전환 (429 에러 시)
- 배치 크기, Rate Limiting 설정

**주요 변수**:

```python
GEMINI_MODEL = 'gemini-1.5-flash'
MAX_REQUESTS_PER_MINUTE = 15
BATCH_SIZE = 100
```

### 2. `llm_prompts.py`

**역할**: LLM 프롬프트 템플릿 관리

**주요 함수**:

- `get_preprocess_initial_prompt()`: 초기 전처리 프롬프트 생성
- `get_validation_prompt()`: 검증 프롬프트 생성
- `load_measure_dict()`: dic.csv에서 measure_code 목록 로드

**프롬프트 구조**:

- dic.csv 기반 measure_code 목록 포함
- 단일/범위 시점 vs 복수 시점 구분 규칙
- JSON 응답 형식 명시

### 3. `llm_preprocess_full.py`

**역할**: 전체 데이터 LLM 전처리

**주요 함수**:

- `call_gemini_api()`: Gemini API 호출 (429 에러 처리, JSON 파싱)
- `preprocess_batch_outcomes()`: 배치 단위 전처리
- `determine_llm_status()`: 처리 상태 결정 (SUCCESS, FAILED 등)
- `insert_llm_results()`: 결과를 DB에 저장

**처리 흐름**:

1. `outcome_raw`에서 데이터 조회
2. 배치 단위로 LLM API 호출
3. JSON 응답 파싱 (잘린 응답 복구 포함)
4. 상태 결정 및 DB 저장

### 4. `llm_validate_preprocessed_success.py`

**역할**: SUCCESS 항목 검증

**주요 함수**:

- `validate_batch_outcomes()`: 배치 단위 검증
- `update_validation_results()`: 검증 결과 DB 저장

**검증 내용**:

- 원본 데이터와 LLM 추출 결과 비교
- Measure Code 일치 여부
- Time 정보 일치 여부

### 5. `generate_llm_preprocessed_report.py`

**역할**: 검증 결과 문서화

**주요 함수**:

- `get_validation_stats()`: 검증 통계 조회
- `get_study_validation_stats()`: Study별 통계
- `generate_report()`: MD 리포트 생성

---

## 데이터 흐름

### 1. 전처리 단계

```
outcome_raw (원본)
    ↓
[llm_preprocess_full.py]
    ├─ 배치 단위로 데이터 읽기
    ├─ 프롬프트 생성 (llm_prompts.py)
    ├─ Gemini API 호출
    ├─ JSON 응답 파싱
    ├─ 상태 결정 (SUCCESS/FAILED)
    └─ outcome_llm_preprocessed에 저장
```

### 2. 검증 단계

```
outcome_llm_preprocessed (llm_status = 'SUCCESS')
    ↓
[llm_validate_preprocessed_success.py]
    ├─ SUCCESS 항목 조회
    ├─ 원본 vs 추출 결과 비교
    ├─ Gemini API로 검증
    └─ llm_validation_status 업데이트
```

### 3. 문서화 단계

```
outcome_llm_preprocessed (검증 완료)
    ↓
[generate_llm_preprocessed_report.py]
    ├─ 통계 조회
    ├─ 리포트 생성
    └─ reports/*.md 저장
```

---

## 프롬프트 구조

### 전처리 프롬프트 (`get_preprocess_initial_prompt`)

**입력 형식**:

```
[outcome_id]|M:[measure_raw]|D:[description_raw]|T:[time_frame_raw]
```

**규칙**:

1. **measure_code 추출**

   - dic.csv 기반 measure_code 목록 제공
   - 약어, canonical_name, keywords 매칭
   - 매칭 우선순위: 괄호 안 약어 > 약어 직접 매칭 > canonical_name > keywords

2. **Time Frame 파싱**
   - 단일/범위 시점: `time_value`, `time_unit`만 추출, `time_points = null`
   - 복수 시점: `time_points` 배열에 모든 시점 포함

**응답 형식**:

```json
[
  {
    "outcome_id": 123,
    "measure_code": "ADAS_COG",
    "time_value": 12,
    "time_unit": "weeks",
    "time_points": null,
    "confidence": 0.95,
    "notes": "Week 12에서 측정"
  }
]
```

### 검증 프롬프트 (`get_validation_prompt`)

**입력 형식**:

```
[outcome_id]|M:[measure_raw]|T:[time_frame_raw]|C:[measure_code]|V:[time_value][unit]|P:[time_points]
```

**검증 규칙**:

- M=원본에 Code 포함 확인
- T=원본 time_frame_raw와 정규화값 일치 확인
- 단일시점=최대값+UNIT 일치 확인
- 복수시점=time_points에 모두 포함 확인

**응답 형식**:

```json
[
  {
    "outcome_id": 123,
    "status": "VERIFIED",
    "confidence": 0.95,
    "notes": "[VERIFIED] 모든 값 일치."
  }
]
```

---

## 검증 프로세스

### 검증 상태 분류

1. **VERIFIED**: 원본과 추출 결과가 완벽하게 일치
2. **UNCERTAIN**: 애매한 경우 또는 불확실한 매칭
3. **MEASURE_FAILED**: Measure Code 불일치
4. **TIMEFRAME_FAILED**: Time 정보 불일치
5. **BOTH_FAILED**: Measure Code와 Time 정보 모두 불일치

### 검증 로직

```python
def determine_llm_status(measure_code, time_value, time_unit, notes):
    has_measure = measure_code is not None and measure_code != ''
    has_time = time_value is not None and time_unit is not None

    if has_measure and has_time:
        return 'SUCCESS', None, formatted_notes
    elif not has_measure and not has_time:
        return 'BOTH_FAILED', 'BOTH_FAILED', formatted_notes
    elif not has_measure:
        return 'MEASURE_FAILED', 'MEASURE_FAILED', formatted_notes
    else:
        return 'TIMEFRAME_FAILED', 'TIMEFRAME_FAILED', formatted_notes
```

---

## 사용 방법

### 1. 환경 설정

`.env` 파일에 API 키 설정:

```
GEMINI_API_KEY=your_api_key_1
GEMINI_API_KEY_2=your_api_key_2
GEMINI_API_KEY_3=your_api_key_3
...
```

### 2. 테이블 생성

```bash
psql -U postgres -d clinicaltrials -f sql/create_outcome_llm_preprocessed.sql
```

### 3. 전처리 실행

```bash
# 전체 데이터 처리
python llm/llm_preprocess_full.py

# 일부만 테스트 (100개, 배치 크기 50)
python llm/llm_preprocess_full.py 100 50
```

### 4. 검증 실행

```bash
# SUCCESS 항목 검증
python llm/llm_validate_preprocessed_success.py

# 일부만 테스트
python llm/llm_validate_preprocessed_success.py 100
```

### 5. 리포트 생성

```bash
python llm/generate_llm_preprocessed_report.py
```

---

## 주요 함수 설명

### `call_gemini_api(prompt: str) -> Optional[Dict]`

**기능**: Gemini API 호출 및 응답 파싱

**특징**:

- 여러 API 키 자동 전환 (429 에러 시)
- JSON 파싱 실패 시 부분 복구 시도
- 코드 블록 자동 제거
- JSON 배열 시작/끝 자동 감지

**에러 처리**:

- 429 에러: 다음 API 키로 자동 전환
- JSON 파싱 실패: 중첩된 JSON 객체 개별 파싱 시도

### `determine_llm_status(measure_code, time_value, time_unit, notes) -> tuple`

**기능**: LLM 처리 결과를 기반으로 상태 결정

**반환값**: `(llm_status, failure_reason, formatted_notes)`

**상태 결정 로직**:

- `SUCCESS`: measure_code와 time 정보 모두 있음
- `MEASURE_FAILED`: measure_code 없음
- `TIMEFRAME_FAILED`: time 정보 없음
- `BOTH_FAILED`: 둘 다 없음

### `preprocess_batch_outcomes(outcomes: List[Dict]) -> List[Dict]`

**기능**: 배치 단위로 outcome들을 LLM으로 전처리

**처리 과정**:

1. 배치 프롬프트 생성
2. Gemini API 호출
3. JSON 응답 파싱
4. 상태 결정 및 결과 반환

### `validate_batch_outcomes(outcomes: List[Dict]) -> List[Dict]`

**기능**: 배치 단위로 outcome들을 LLM으로 검증

**검증 내용**:

- 원본 데이터와 추출 결과 비교
- Measure Code 일치 여부
- Time 정보 일치 여부

---

## 데이터베이스 스키마

### `outcome_llm_preprocessed` 테이블

**원본 데이터**:

- `nct_id`, `outcome_type`, `outcome_order`
- `measure_raw`, `description_raw`, `time_frame_raw`, `phase`

**LLM 전처리 결과**:

- `llm_measure_code`: 추출한 measure_code
- `llm_time_value`: 추출한 time_value
- `llm_time_unit`: 추출한 time_unit
- `llm_time_points`: 복수 시점 JSON 배열

**메타데이터**:

- `llm_confidence`: LLM 신뢰도 (0.00 ~ 1.00)
- `llm_notes`: LLM 처리 노트 (형식: `[CATEGORY] 설명. 상세내용`)
- `llm_status`: 처리 상태 (SUCCESS, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED, API_FAILED, PARTIAL_RECOVERED)
- `failure_reason`: 실패 이유

**검증 결과**:

- `llm_validation_status`: 검증 상태 (VERIFIED, UNCERTAIN, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED)
- `llm_validation_confidence`: 검증 신뢰도
- `llm_validation_notes`: 검증 노트

---

## 에러 처리 및 복구

### 1. API 에러 처리

- **429 에러 (Rate Limit)**: 다음 API 키로 자동 전환
- **기타 에러**: 현재 키에서 실패 처리

### 2. JSON 파싱 실패 복구

- 코드 블록 자동 제거
- JSON 배열 시작/끝 자동 감지
- 중첩된 JSON 객체 개별 파싱 시도
- 부분 복구 성공 시 `PARTIAL_RECOVERED` 상태로 저장

### 3. 배치 크기 조정

- 기본값: 100개
- 환경변수로 조정 가능: `BATCH_SIZE=50`
- 명령줄 인자로도 조정 가능

---

## 성능 최적화

### 1. 배치 처리

- 여러 항목을 한 번에 API 호출하여 효율성 향상
- 배치 크기는 응답 길이 제한 고려

### 2. API 키 관리

- 여러 API 키를 순차적으로 사용하여 Rate Limit 회피
- 429 에러 시 자동으로 다음 키로 전환

### 3. Rate Limiting

- `MAX_REQUESTS_PER_MINUTE` 설정으로 API 호출 제한
- 배치 간 자동 대기

---

## 주의사항

1. **API 키 관리**: 여러 API 키를 설정하여 Rate Limit 회피
2. **배치 크기**: 너무 크면 JSON 응답이 잘릴 수 있음 (권장: 50~100)
3. **검증 순서**: 전처리 → 검증 → 리포트 생성 순서로 실행
4. **데이터 백업**: 대량 처리 전 데이터 백업 권장

---

## 향후 개선 사항

1. **프롬프트 최적화**: 검증 정확도 향상을 위한 프롬프트 개선
2. **에러 복구 강화**: 더 정교한 JSON 파싱 및 복구 로직
3. **병렬 처리**: 여러 배치를 병렬로 처리하여 속도 향상
4. **캐싱**: 동일한 패턴에 대한 결과 캐싱

---

## 참고 파일

- `llm/llm_config.py`: API 설정
- `llm/llm_prompts.py`: 프롬프트 템플릿
- `llm/llm_preprocess_full.py`: 전처리 스크립트
- `llm/llm_validate_preprocessed_success.py`: 검증 스크립트
- `llm/generate_llm_preprocessed_report.py`: 리포트 생성 스크립트
- `sql/create_outcome_llm_preprocessed.sql`: 테이블 생성 SQL
- `data/dic.csv`: measure_code 사전
