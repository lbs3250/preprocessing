# Inclusion/Exclusion 데이터 수집 및 LLM 전처리 구현 계획

## 1. 전체 프로세스 개요

```
[Step 1] 데이터 수집
  └─ preprocessing/collect_inclusion_exclusion.py
     └─ ClinicalTrials.gov API에서 eligibilityCriteria 추출
     └─ inclusion_exclusion_raw 테이블에 저장
     └─ 배치 처리: outcome과 동일한 방식

[Step 2] LLM 전처리
  └─ llm/llm_preprocess_inclusion_exclusion.py
     └─ inclusion_exclusion_raw에서 데이터 읽기
     └─ LLM으로 Inclusion/Exclusion 구조화 (Feature-Operator-Value)
     └─ inclusion_exclusion_llm_preprocessed 테이블에 저장
     └─ 배치 처리: outcome과 동일한 방식
     └─ API 키 로테이션, 재시도 로직 포함

[Step 3] LLM 검증 (다중 검증)
  └─ llm/llm_validate_inclusion_exclusion.py
     └─ 다중 검증 (기본 3회)
     └─ Majority Voting
     └─ Consistency Score 계산
     └─ Confidence + Consistency 기반 필터링
     └─ outcome과 동일한 검증 로직
```

## 2. 데이터 수집 (Step 1)

### 2.1 스크립트: `preprocessing/collect_inclusion_exclusion.py`

**기능:**
- ClinicalTrials.gov API에서 `eligibilityModule.eligibilityCriteria` 추출
- `inclusion_exclusion_raw` 테이블에 저장
- Outcome 수집과 동일한 패턴

**주요 함수:**
```python
def extract_eligibility_criteria(study: Dict) -> Optional[str]:
    """Study JSON에서 eligibilityCriteria 추출"""
    eligibility_module = study.get('protocolSection', {}).get('eligibilityModule', {})
    return eligibility_module.get('eligibilityCriteria')

def extract_phase(study: Dict) -> str:
    """Phase 정보 추출 (outcome과 동일)"""

def insert_eligibility_criteria(conn, studies: List[Dict]):
    """배치로 eligibilityCriteria 저장"""
```

**배치 처리:**
- API 호출: 페이지 단위 (500개씩)
- DB 저장: 배치 단위 (`execute_batch` 사용)
- Outcome 수집과 동일한 구조

### 2.2 테이블: `inclusion_exclusion_raw`

```sql
CREATE TABLE inclusion_exclusion_raw (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,  -- 전체 eligibilityCriteria 텍스트
    phase VARCHAR(50),
    source_version VARCHAR(50),
    raw_json JSONB,  -- 원본 study JSON
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_inclusion_exclusion_raw UNIQUE (nct_id)
);
```

## 3. LLM 전처리 (Step 2)

### 3.1 스크립트: `llm/llm_preprocess_inclusion_exclusion.py`

**기능:**
- `inclusion_exclusion_raw` 테이블에서 데이터 읽기
- LLM으로 Inclusion/Exclusion 구조화
- `inclusion_exclusion_llm_preprocessed` 테이블에 저장
- Outcome 전처리와 동일한 구조

**주요 함수:**
```python
def preprocess_batch_eligibility(eligibility_list: List[Dict]) -> List[Dict]:
    """배치 단위로 eligibilityCriteria를 LLM으로 전처리"""
    # 배치 내 모든 항목을 한 번에 프롬프트로 만들어서 API 호출
    # Outcome의 preprocess_batch_outcomes와 동일한 패턴

def determine_llm_status(inclusion_result, exclusion_result) -> tuple:
    """LLM 처리 상태 결정"""
    # SUCCESS: Inclusion과 Exclusion 모두 성공
    # INCLUSION_FAILED: Inclusion만 실패
    # EXCLUSION_FAILED: Exclusion만 실패
    # BOTH_FAILED: 둘 다 실패
    # API_FAILED: API 호출 실패

def insert_llm_results(conn, eligibility_list: List[Dict], results: List[Dict]):
    """LLM 전처리 결과를 inclusion_exclusion_llm_preprocessed 테이블에 삽입"""
    # execute_batch 사용 (배치 단위 저장)
```

**배치 처리:**
- 배치 크기: `BATCH_SIZE` (기본 100개)
- 배치 단위로 프롬프트 생성 → 한 번의 API 호출
- 배치 단위로 DB 저장
- Outcome 전처리와 동일한 방식

**재시작 기능:**
- `start_batch` 인자로 중단 지점부터 재시작 가능
- Outcome 전처리와 동일

### 3.2 프롬프트: `llm/llm_prompts.py`

**함수 추가:**
```python
def get_inclusion_exclusion_preprocess_prompt(items_text: str) -> str:
    """Inclusion/Exclusion 전처리 프롬프트 생성"""
    # items_text: 여러 eligibilityCriteria를 줄바꿈으로 구분
    # 각 항목을 Feature-Operator-Value 구조로 변환 요청
    # Inclusion/Exclusion 분리
    # AND/OR 논리 연산자 처리
```

**프롬프트 구조:**
```
다음 Inclusion/Exclusion Criteria를 구조화하세요:

[항목1]
[항목2]
...

응답 형식:
[
  {
    "nct_id": "첫번째 숫자",
    "inclusion_criteria": [
      {
        "criterion_id": 1,
        "original_text": "...",
        "feature": "AGE|CONDITION|LAB_VALUE|...",
        "operator": ">=|<|BETWEEN|PRESENT|...",
        "value": 숫자|문자열|배열|null,
        "unit": "years|g/dL|...",
        "logic_operator": "AND|OR" (복합 조건인 경우),
        "conditions": [...] (복합 조건인 경우),
        "confidence": 0.0~1.0,
        "notes": "..."
      }
    ],
    "exclusion_criteria": [...]
  },
  ...
]
```

### 3.3 테이블: `inclusion_exclusion_llm_preprocessed`

```sql
CREATE TABLE inclusion_exclusion_llm_preprocessed (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,
    phase VARCHAR(50),
    
    -- LLM 전처리 결과
    inclusion_criteria JSONB,  -- Inclusion 항목 배열
    exclusion_criteria JSONB,  -- Exclusion 항목 배열
    
    -- 메타데이터
    llm_confidence NUMERIC(3,2),
    llm_notes TEXT,
    parsing_method VARCHAR(20) DEFAULT 'LLM',
    llm_status VARCHAR(20),  -- SUCCESS, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED, API_FAILED
    failure_reason VARCHAR(50),
    
    -- 검증 결과 (Step 3에서 추가)
    llm_validation_status VARCHAR(20),
    llm_validation_confidence NUMERIC(3,2),
    llm_validation_notes TEXT,
    validation_consistency_score NUMERIC(3,2),
    validation_count INTEGER,
    needs_manual_review BOOLEAN,
    avg_validation_confidence NUMERIC(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_inclusion_exclusion_llm UNIQUE (nct_id)
);
```

## 4. LLM 검증 (Step 3)

### 4.1 스크립트: `llm/llm_validate_inclusion_exclusion.py`

**기능:**
- `inclusion_exclusion_llm_preprocessed` 테이블에서 `llm_status = 'SUCCESS'`인 항목 조회
- 다중 검증 (기본 3회)
- Majority Voting
- Consistency Score 계산
- Confidence + Consistency 기반 필터링
- Outcome 검증과 동일한 로직

**주요 함수:**
```python
def validate_batch_single_run(eligibility_list: List[Dict]) -> Dict[int, Dict]:
    """배치 단위로 eligibilityCriteria를 LLM으로 검증 (1회 실행)"""
    # 배치 내 모든 항목을 한 번에 프롬프트로 만들어서 API 호출
    # Outcome의 validate_batch_single_run과 동일한 패턴

def validate_with_multi_run_for_eligibility(
    eligibility: Dict,
    validation_results_by_run: Dict[int, Dict],
    existing_results: List[Dict]
) -> Dict:
    """단일 eligibility에 대해 다중 검증 결과를 처리"""
    # Outcome의 validate_with_multi_run_for_outcome과 동일한 로직

def validate_batch_eligibility(eligibility_list: List[Dict], num_validations: int = 3, conn=None) -> tuple:
    """배치 단위로 eligibilityCriteria들을 다중 검증"""
    # Outcome의 validate_batch_outcomes와 동일한 구조

def majority_voting(validation_results: List[Dict]) -> Dict:
    """Majority Voting (outcome과 동일)"""

def calculate_consistency_score(validation_results: List[Dict]) -> float:
    """일관성 점수 계산 (outcome과 동일)"""

def apply_confidence_consistency_filtering(...) -> Dict:
    """Confidence + Consistency 기반 필터링 (outcome과 동일)"""
```

**검증 상태:**
- `VERIFIED`: Inclusion과 Exclusion 모두 검증 성공
- `UNCERTAIN`: 불확실
- `INCLUSION_FAILED`: Inclusion 검증 실패
- `EXCLUSION_FAILED`: Exclusion 검증 실패
- `BOTH_FAILED`: 둘 다 검증 실패

**배치 처리:**
- 배치 단위로 검증 (outcome과 동일)
- 배치 단위로 DB 저장
- 재시작 기능 (`start_batch` 인자)

### 4.2 검증 이력 테이블

```sql
CREATE TABLE inclusion_exclusion_llm_validation_history (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    validation_run INTEGER NOT NULL,
    validation_status VARCHAR(20),  -- VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED
    validation_confidence NUMERIC(3,2),
    validation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_validation_history UNIQUE (nct_id, validation_run)
);
```

### 4.3 프롬프트: `llm/llm_prompts.py`

**함수 추가:**
```python
def get_inclusion_exclusion_validation_prompt(item_text: str) -> str:
    """Inclusion/Exclusion 검증 프롬프트 생성"""
    # 원본 eligibilityCriteria와 LLM 전처리 결과를 비교
    # Inclusion/Exclusion 각각 검증
    # 검증 상태, 신뢰도, 노트 반환
```

## 5. 구현 순서

### Phase 1: SQL 스키마 생성
1. `sql/create_inclusion_exclusion_raw.sql`
2. `sql/create_inclusion_exclusion_llm_preprocessed.sql`
3. `sql/create_inclusion_exclusion_validation_history.sql`

### Phase 2: 데이터 수집
1. `preprocessing/collect_inclusion_exclusion.py` 생성
   - Outcome 수집 스크립트를 참고하여 동일한 구조로 구현
   - 배치 처리 포함

### Phase 3: LLM 프롬프트 설계
1. `llm/llm_prompts.py`에 함수 추가
   - `get_inclusion_exclusion_preprocess_prompt()`
   - `get_inclusion_exclusion_validation_prompt()`

### Phase 4: LLM 전처리
1. `llm/llm_preprocess_inclusion_exclusion.py` 생성
   - `llm_preprocess_full.py`를 참고하여 동일한 구조로 구현
   - 배치 처리, API 키 로테이션, 재시도 로직 포함
   - 재시작 기능 (`start_batch`)

### Phase 5: LLM 검증
1. `llm/llm_validate_inclusion_exclusion.py` 생성
   - `llm_validate_preprocessed_success.py`를 참고하여 동일한 구조로 구현
   - 다중 검증, Majority Voting, Consistency Score
   - 배치 처리, 재시작 기능 포함

## 6. Outcome과의 차이점

### 6.1 데이터 구조
- **Outcome**: measure_code, time_value, time_unit (단순 구조)
- **Inclusion/Exclusion**: Feature-Operator-Value + 논리 연산자 (복잡한 구조)

### 6.2 검증 상태
- **Outcome**: VERIFIED, UNCERTAIN, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED
- **Inclusion/Exclusion**: VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED

### 6.3 공통점
- 배치 처리 방식 동일
- API 키 로테이션 동일
- 재시도 로직 동일
- 다중 검증 로직 동일
- Majority Voting 동일
- Consistency Score 계산 동일
- Confidence + Consistency 필터링 동일

## 7. 실행 명령어

### 데이터 수집
```bash
python preprocessing/collect_inclusion_exclusion.py
```

### LLM 전처리
```bash
# 전체 처리
python llm/llm_preprocess_inclusion_exclusion.py

# 제한된 개수만 처리
python llm/llm_preprocess_inclusion_exclusion.py 1000

# 배치 크기 조정
python llm/llm_preprocess_inclusion_exclusion.py 1000 50

# 특정 배치부터 시작 (재시작)
python llm/llm_preprocess_inclusion_exclusion.py 1000 50 10
```

### LLM 검증
```bash
# 전체 검증 (기본 3회)
python llm/llm_validate_inclusion_exclusion.py

# 제한된 개수만 검증
python llm/llm_validate_inclusion_exclusion.py 1000

# 검증 횟수 조정
python llm/llm_validate_inclusion_exclusion.py 1000 5

# 배치 크기 조정
python llm/llm_validate_inclusion_exclusion.py 1000 5 50

# 특정 배치부터 시작 (재시작)
python llm/llm_validate_inclusion_exclusion.py 1000 5 50 10
```

## 8. 성공/실패 조건 정의

### 8.1 전처리 성공 조건
- **SUCCESS**: Inclusion과 Exclusion 모두 구조화 성공
- **INCLUSION_FAILED**: Inclusion만 실패
- **EXCLUSION_FAILED**: Exclusion만 실패
- **BOTH_FAILED**: 둘 다 실패
- **API_FAILED**: API 호출 실패

### 8.2 검증 성공 조건
- **VERIFIED**: Inclusion과 Exclusion 모두 검증 성공
- **UNCERTAIN**: 불확실 (다중 검증 결과가 일치하지 않음)
- **INCLUSION_FAILED**: Inclusion 검증 실패
- **EXCLUSION_FAILED**: Exclusion 검증 실패
- **BOTH_FAILED**: 둘 다 검증 실패

### 8.3 검증 기준
- 원본 텍스트와 LLM 전처리 결과 비교
- Feature 분류 정확성
- Operator 추출 정확성
- Value 추출 정확성
- 논리 연산자 처리 정확성

## 9. 리포트 생성

### 9.1 전처리 리포트
- 전체 처리 통계
- 상태별 통계 (SUCCESS, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED)
- Feature 분포
- Operator 분포

### 9.2 검증 리포트
- 전체 검증 통계
- 상태별 통계
- 일관성 점수 분포
- 수동 검토 필요 항목
- Outcome 검증 리포트와 동일한 구조

## 10. 향후 확장 계획

1. **Feature 사전 등록**
   - 실제 데이터 분석하여 자주 나오는 feature 추출
   - `inclusion_exclusion_feature_dict` 테이블에 등록
   - 동의어, 표준화된 이름 관리

2. **예외 처리**
   - "except non-melanoma skin cancer" 같은 예외 조건 처리
   - 별도 필드로 추가 가능

3. **시간 조건**
   - "within 6 months" 같은 시간 제약 처리
   - 별도 필드로 추가 가능

4. **중첩 논리**
   - AND/OR의 중첩 구조 지원 (현재는 2단계까지만)

