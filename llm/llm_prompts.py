"""
LLM 프롬프트 템플릿 정의

전처리(파싱) 및 검증용 프롬프트를 관리합니다.
"""

import os
import csv
from typing import List, Dict

# ============================================================================
# dic.csv 기반 measure_code 목록 로드
# ============================================================================

def load_measure_dict() -> List[Dict[str, str]]:
    """dic.csv 파일에서 measure_code 목록 로드"""
    dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dic.csv')
    measures = []
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                measures.append({
                    'measure_code': row.get('measure_code', ''),
                    'abbreviation': row.get('abbreviation', ''),
                    'canonical_name': row.get('canonical_name', ''),
                    'keywords': row.get('keywords', '')
                })
    except FileNotFoundError:
        print(f"[WARN] dic.csv 파일을 찾을 수 없습니다: {dict_path}")
    except Exception as e:
        print(f"[WARN] dic.csv 로드 실패: {e}")
    
    return measures

def get_measure_code_summary() -> str:
    """measure_code 목록 요약 문자열 생성 (프롬프트용)"""
    measures = load_measure_dict()
    if not measures:
        return "measure_code 목록을 로드할 수 없습니다."
    
    # 주요 measure_code만 요약 (처음 30개)
    summary_lines = []
    for i, m in enumerate(measures[:30]):
        abbrev = m['abbreviation'] if m['abbreviation'] else 'N/A'
        summary_lines.append(f"- {m['measure_code']} (약어: {abbrev})")
    
    if len(measures) > 30:
        summary_lines.append(f"- ... 외 {len(measures) - 30}개 더")
    
    return '\n'.join(summary_lines)

# ============================================================================
# 전처리(파싱) 프롬프트
# ============================================================================

# 실패 항목 전처리 규칙 (기존 실패한 항목을 LLM으로 재파싱)
PREPROCESS_FAILED_RULES = """규칙:
- measure_code: 표준 약어(ADAS-Cog, MMSE, CDR-SB 등) 추출. 확실하지 않으면 null
- time_value: 숫자만 추출. "Up to 17 days" 같은 경우 최대값(17) 추출
- time_unit: weeks/months/days/years/hours/minutes 중 하나. 확실하지 않으면 null
- 복수 시점 처리:
  * "Days 1 and 14" → 최대값(14) 추출
  * "Day 1 and Day 4" → 최대값(4) 추출
  * "1 day and 4" → 두 번째 단위가 생략된 경우, 첫 번째 단위(days) 사용하여 최대값(4) 추출
  * "1 day, 4" → 콤마로 구분된 경우도 동일하게 처리
  * "6 weeks, 12 weeks, 24 weeks" → 최대값(24) 추출
- "Up to N days/weeks" 패턴은 N을 time_value로 사용 (최대값)
- 확실하지 않으면 null 반환"""

def get_preprocess_failed_prompt(items_text: str) -> str:
    """실패 항목 전처리 프롬프트 생성"""
    return f"""{items_text}

{PREPROCESS_FAILED_RULES}

응답: 각 항목의 첫 숫자(outcome_id)를 포함하여 JSON 배열로 응답.
[{{"outcome_id": 첫숫자, "measure_code": "코드|null", "time_value": 숫자|null, "time_unit": "단위|null", "confidence": 0~1, "notes": "요약"}}, ...]"""

PREPROCESS_FAILED_PROMPT_TEMPLATE = "{items}"  # 하위 호환성용 (사용 안 함)

# 초기 전처리 프롬프트 (처음부터 LLM으로 파싱)
def get_preprocess_initial_rules() -> str:
    """초기 전처리 규칙 생성 (dic.csv 기반)"""
    measure_summary = get_measure_code_summary()
    
    return f"""규칙:

## 1. measure_code 추출
measure_raw와 description_raw에서 표준 measure_code를 추출합니다.
다음 measure_code 목록을 참고하세요 (dic.csv 기반):

{measure_summary}

매칭 방법:
- measure_raw나 description_raw에서 약어(abbreviation), canonical_name, keywords를 매칭하여 measure_code 추출
- 예: "ADAS-Cog" 또는 "(ADAS-Cog)" → ADAS_COG
- 예: "Mini-Mental State Examination" → MMSE
- 예: "Cmax" 또는 "Cmax" → CMAX

매칭 우선순위:
1. measure_raw에서 괄호 안 약어 추출 (예: "(ADAS-Cog)" → ADAS_COG)
2. measure_raw에서 표준 약어 직접 매칭
3. canonical_name 부분 매칭 (예: "Alzheimer's Disease Assessment Scale" → ADAS_COG)
4. keywords 매칭 (예: "adas-cog", "adas cog" → ADAS_COG)
5. description_raw에서도 동일하게 매칭 시도

확실하지 않으면 null 반환

## 2. Time Frame 파싱

### 2-1. 단일 시점 또는 범위 시점
단일 시점이나 범위("Day 1 to Day 10")인 경우:
- time_value: 숫자만 추출 (범위인 경우 최대값)
- time_unit: weeks/months/days/years/hours/minutes 중 하나
- time_points: null

예시:
- "Day 7" → time_value: 7, time_unit: "days", time_points: null
- "Week 12" → time_value: 12, time_unit: "weeks", time_points: null
- "Day 1 to Day 10" → time_value: 10, time_unit: "days", time_points: null
- "From week 4 to week 64" → time_value: 64, time_unit: "weeks", time_points: null
- "Up to 17 days" → time_value: 17, time_unit: "days", time_points: null
- "1 day and 4" → time_value: 4, time_unit: "days", time_points: null (단위 생략 시 첫 번째 단위 사용)

### 2-2. 복수 시점 (여러 시점이 명시된 경우)
복수 시점인 경우 (예: "Week 1, Week 14, Week 26"):
- time_value: 모든 시점 중 최대값
- time_unit: 모든 시점의 단위 (일반적으로 동일)
- time_points: 모든 시점을 JSON 배열로 추출 [{{"value": 숫자, "unit": "단위"}}, ...]

예시:
- "Week 1, Week 14, Week 26" → 
  time_value: 26, time_unit: "weeks", 
  time_points: [{{"value": 1, "unit": "weeks"}}, {{"value": 14, "unit": "weeks"}}, {{"value": 26, "unit": "weeks"}}]
- "Days 1 and 14" → 
  time_value: 14, time_unit: "days",
  time_points: [{{"value": 1, "unit": "days"}}, {{"value": 14, "unit": "days"}}]
- "6 weeks, 12 weeks, 24 weeks" → 
  time_value: 24, time_unit: "weeks",
  time_points: [{{"value": 6, "unit": "weeks"}}, {{"value": 12, "unit": "weeks"}}, {{"value": 24, "unit": "weeks"}}]
- "1주차, 2주차, 3주차" (한글) → 
  time_value: 3, time_unit: "weeks",
  time_points: [{{"value": 1, "unit": "weeks"}}, {{"value": 2, "unit": "weeks"}}, {{"value": 3, "unit": "weeks"}}]

## 3. 기타 규칙
- 단위가 생략된 경우("1 day and 4") → 첫 번째 숫자의 단위를 두 번째 숫자에도 적용
- "Up to N days/weeks" 패턴은 N을 time_value로 사용 (최대값)
- 확실하지 않으면 null 반환"""

# 하위 호환성을 위한 상수 (동적 생성 함수 사용)
PREPROCESS_INITIAL_RULES = get_preprocess_initial_rules()

def get_preprocess_initial_prompt(items_text: str) -> str:
    """초기 전처리 프롬프트 생성"""
    rules = get_preprocess_initial_rules()
    
    return f"""다음 outcome 데이터를 파싱하여 measure_code와 time 정보를 추출하세요.

데이터 형식: [outcome_id]|M:[measure_raw]|D:[description_raw]|T:[time_frame_raw]

{items_text}

{rules}

**중요: 반드시 JSON 배열만 반환하세요. 코드나 설명 없이 순수 JSON만 반환합니다.**

응답 형식 (JSON 배열):
[
  {{
    "outcome_id": 123,
    "measure_code": "ADAS_COG",
    "time_value": 12,
    "time_unit": "weeks",
    "time_points": null,
    "confidence": 0.95,
    "notes": "Week 12에서 측정"
  }},
  {{
    "outcome_id": 456,
    "measure_code": "MMSE",
    "time_value": 26,
    "time_unit": "weeks",
    "time_points": [
      {{"value": 1, "unit": "weeks"}},
      {{"value": 14, "unit": "weeks"}},
      {{"value": 26, "unit": "weeks"}}
    ],
    "confidence": 0.9,
    "notes": "Week 1, 14, 26에서 측정"
  }}
]

**반드시 위 형식의 JSON 배열만 반환하세요. 코드나 설명 텍스트는 포함하지 마세요.**"""

PREPROCESS_INITIAL_PROMPT_TEMPLATE = "{items}"  # 하위 호환성용

# ============================================================================
# 검증 프롬프트
# ============================================================================

VALIDATION_RULES = """규칙:
- M=원본 measure_raw에 Code 포함 확인
- D=원본 description_raw에도 Code 포함 여부 확인 (measure_raw에 없으면 description_raw에서 확인)
- T=원본 time_frame_raw에서 직접 추출한 시간값(숫자+단위)과 정규화값(time_value_main+time_unit_main)이 일치하는지 확인
- 단일시점=최대값+UNIT 일치 확인
- 복수시점=time_points에 모두 포함 확인
- 패턴코드는 무시하고 값만 확인

**중요: time_frame_raw가 없거나 비어있는 경우 (time_value=0, time_unit=null)**
- 원본에 time_frame_raw가 없거나 비어있으면, 정규화값이 time_value=0이고 time_unit=null인 것이 정상입니다.
- 이 경우 TIMEFRAME_FAILED로 판단하지 마세요. VERIFIED로 처리하세요.
- time_frame_raw가 없는데 time_value가 0이 아니면 TIMEFRAME_FAILED입니다.

**중요: Baseline이 포함된 경우 (예: "Baseline, Month 12", "Baseline to Month 12")**
- 원본에 "Baseline"이 포함되어 있고, 정규화값에 최종 시점(예: Month 12, 12 months)이 정확히 추출되었다면, time_points가 없어도 정상입니다.
- Baseline은 시작점(0)을 의미하므로, time_points에 명시적으로 포함하지 않아도 됩니다.
- 예: "Baseline, Month 12" → time_value=12, time_unit=months, time_points=null → VERIFIED (정상)
- 예: "Baseline to Month 12" → time_value=12, time_unit=months, time_points=null → VERIFIED (정상)
- 이 경우 TIME_POINTS_MISSING으로 판단하지 마세요. VERIFIED로 처리하세요.

Notes 작성 형식: [문제유형] 간단설명. 상세내용.
문제유형: [MEASURE_MISMATCH] [TIME_MISMATCH] [TIME_POINTS_MISSING] [TIME_VALUE_WRONG] [TIME_UNIT_WRONG] [VERIFIED]
예: [TIME_POINTS_MISSING] Points 필드 누락. 원본에 '12,14,26,40 weeks'가 있는데 Points가 비어있음.
예: [TIME_VALUE_WRONG] Time 값 불일치. 원본 최대값 '24 weeks'인데 정규화값은 '20 weeks'.
예: [VERIFIED] 모든 값 일치. time_frame_raw 없음, time_value=0 정상.
예: [VERIFIED] measure_code 일치, time_frame_raw 없음으로 time_value=0 정상.
예: [VERIFIED] measure_code 일치, Baseline 포함으로 time_points 없음 정상.

중요: 응답 시 각 항목의 첫 숫자(outcome_id)를 반드시 포함해야 함. 항목 형식: [outcome_id]|..."""

def get_validation_prompt(items_text: str) -> str:
    """검증 프롬프트 생성"""
    return f"""{items_text}

{VALIDATION_RULES}

응답: 각 항목의 첫 숫자(outcome_id)를 포함하여 JSON 배열로 응답.
[{{"outcome_id": 첫숫자, "status": "VERIFIED|UNCERTAIN|MEASURE_FAILED|TIMEFRAME_FAILED|BOTH_FAILED", "confidence": 0~1, "notes": "요약"}}, ...]"""

VALIDATION_PROMPT_TEMPLATE = "{items}"  # 하위 호환성용

# ============================================================================
# Inclusion/Exclusion 전처리 프롬프트
# ============================================================================

INCLUSION_EXCLUSION_PREPROCESS_RULES = """규칙:

## 1. Inclusion/Exclusion 분리
- "Inclusion Criteria:" 섹션과 "Exclusion Criteria:" 섹션을 명확히 구분
- 각 섹션 내의 **각 불릿/문장마다 하나의 JSON 객체** 생성
- 하나의 original_text = 하나의 JSON 객체

**중요: 번호가 매겨진 리스트와 중첩 불릿 포인트 처리**
- 번호가 매겨진 리스트 (1., 2., 3. ...): 각 번호 항목을 하나의 criterion으로 처리
- 중첩된 불릿 포인트 (*): 각 * 불릿 포인트를 별도의 criterion으로 처리
  * 예: "3. Clinical findings consistent with:
       * other primary degenerative dementia
       * other neurodegenerative condition
       * cerebrovascular disease"
  → 3개의 별도 criterion으로 처리:
     - "other primary degenerative dementia"
     - "other neurodegenerative condition"  
     - "cerebrovascular disease"
- 범위 조건 (예: "MMSE ≥18 and ≤26", "Age 50-85 years"): **반드시 두 개의 별도 criterion으로 분리**
  * 예: "MMSE ≥18 and ≤26" → 
    - {"feature": "MMSE", "operator": ">=", "value": 18}
    - {"feature": "MMSE", "operator": "<=", "value": 26}
  * 예: "Age 50-85 years" → 
    - {"feature": "age", "operator": ">=", "value": 50, "unit": "years"}
    - {"feature": "age", "operator": "<=", "value": 85, "unit": "years"}
  * Inclusion criteria는 기본적으로 AND 로직이므로, 두 개로 분리해도 문제없습니다.
- 매우 긴 문장: 하나의 criterion으로 처리하되, 핵심 조건만 추출

## 2. Feature 추출
**중요: feature는 문장의 주체(subject)입니다. 누가/무엇이 조건을 만족해야 하는지 나타냅니다.**

- 환자/참가자 관련: feature: "patient" 또는 "subject"
  * 예: "Patients must meet NINCDS-ADRDA criteria" → feature: "patient", value: "NINCDS-ADRDA criteria"
  * 예: "Patients must have disrupted sleep" → feature: "patient", value: "disrupted sleep"
  * 예: "Ability to ingest oral medication" → feature: "patient", value: "ability to ingest oral medication"
- 나이 조건: feature: "age" (나이 자체가 조건의 주체)
  * 예: "age 50 or older" → feature: "age", value: 50
- 성별 조건: feature: "gender" (성별 자체가 조건의 주체)
  * 예: "male or female" → feature: "gender", value: "male or female"
- 검사 수치: feature에 검사명 직접 사용 (검사 자체가 조건의 주체)
  * 예: "MMSE 10-22" → feature: "MMSE", value: 10 (또는 범위)
  * 예: "Global CDR score = 0.5" → feature: "Global CDR", value: 0.5
  * 예: "NYU Delayed Paragraph Recall < 9" → feature: "NYU Delayed Paragraph Recall", value: 9
- 약물/치료: feature에 약물명 또는 "medication" 사용
  * 예: "Stable medication for 4 weeks" → feature: "medication", value: "stable"
- 기타: 문장의 주체가 무엇인지 파악하여 feature 설정

**절대 사용하지 마세요**: 
- test_name 필드
- logic_operator 필드
- conditions 필드
- **카테고리만 사용 (예: "CONDITION", "LAB_VALUE", "GENDER", "AGE" 등) - 구체적인 항목명을 사용하세요!**

## 3. Operator 추출 (모든 자연어를 부등호로 변환)
**중요: 모든 자연어 표현을 표준 수학 연산자(부등호)로 변환하세요. 텍스트로 남기지 마세요.**

자연어 → 부등호 변환 규칙:
- 크기 비교:
  * "50 or older", "at least 50", "≥50", "at least", "greater than or equal" → operator: ">="
  * "younger than 50", "less than 50", "<50", "below" → operator: "<"
  * "greater than 50", "more than 50", ">50", "above" → operator: ">"
  * "50 or younger", "at most 50", "≤50", "no more than" → operator: "<="
- 동등 비교:
  * "equal to 50", "exactly 50", "=50", "is 50" → operator: "="
  * "not equal to 50", "≠50", "not 50" → operator: "!="
- 시간 표현:
  * "within the last 12 months", "in the past 12 months", "within 12 months" → operator: "<=" (과거로부터의 시간)
  * "at least 12 months ago" → operator: ">="
  * "more than 12 months ago" → operator: ">"
- 존재 여부:
  * "with X", "has X", "X present", "X exists", "must have X", "must meet X" → operator: "=", value: "X" (X는 질환명, 상태명, 조건 등)
  * "without X", "no X", "X absent", "X not present", "does not have X" → operator: "!=", value: "X"
  * 예: "Patients must meet NINCDS-ADRDA criteria" → feature: "patient", operator: "=", value: "NINCDS-ADRDA criteria"
  * 예: "Patients must have disrupted sleep" → feature: "patient", operator: "=", value: "disrupted sleep"
- 범위 표현:
  * "between X and Y", "X-Y", "X and Y" → **반드시 두 개의 별도 criterion으로 분리**
    * 예: "between 18 and 65" → 
      - {"feature": "age", "operator": ">=", "value": 18, "unit": "years"}
      - {"feature": "age", "operator": "<=", "value": 65, "unit": "years"}
    * 예: "50-85 years" → 
      - {"feature": "age", "operator": ">=", "value": 50, "unit": "years"}
      - {"feature": "age", "operator": "<=", "value": 85, "unit": "years"}

**중요**: 
- 반드시 표준 수학 연산자만 사용: =, !=, <, <=, >, >=
- "present", "absent", "within", "between" 같은 텍스트는 절대 사용하지 마세요. 모두 부등호로 변환하세요.
- logic_operator, conditions 필드는 절대 사용하지 마세요
- 하나의 문장 = 하나의 JSON 객체
- **무조건 feature operator value 형식으로 작성**

## 4. Value 추출
- 숫자: 50, 18.5, 12
- 문자열: "male", "diabetes", "schizophrenia", "NINCDS-ADRDA criteria for probable Alzheimer's disease", "disrupted sleep"
- 조건/상태: feature가 "patient"인 경우, value는 조건이나 상태를 나타내는 문자열
  * 예: "Patients must meet NINCDS-ADRDA criteria" → value: "NINCDS-ADRDA criteria"
  * 예: "Patients must have disrupted sleep" → value: "disrupted sleep"
- **절대 null 사용 금지**: 값이 명시되지 않은 경우에도 적절한 문자열을 value로 사용

## 5. Unit 추출
- 나이: "years", "months"
- 시간: "months", "years", "days", "weeks"
- 검사 수치: "g/dL", "mL/min", "bpm", "mg/dL" 등
- 없으면 null

## 6. 예시
- "age 50 or older" → 
  {{"feature": "age", "operator": ">=", "value": 50, "unit": "years"}}

- "Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease (AD)" → 
  {{"feature": "patient", "operator": "=", "value": "NINCDS-ADRDA criteria for probable Alzheimer's disease (AD)"}}

- "Patients must have disrupted sleep" → 
  {{"feature": "patient", "operator": "=", "value": "disrupted sleep"}}

- "A known history of schizophrenia of at least 12 months" → 
  {{"feature": "patient", "operator": ">=", "value": 12, "unit": "months"}} (또는 feature: "schizophrenia history", value: 12)

- "T.I.A or Major infarction within the last 12 months" → 
  {{"feature": "patient", "operator": "<=", "value": 12, "unit": "months"}} (또는 feature: "T.I.A or Major infarction", value: 12)

- "MMSE 10-22" → 
  {{"feature": "MMSE", "operator": ">=", "value": 10}},
  {{"feature": "MMSE", "operator": "<=", "value": 22}}

- "Global CDR score = 0.5" → 
  {{"feature": "Global CDR", "operator": "=", "value": 0.5}}

- "male or female" → 
  {{"feature": "gender", "operator": "=", "value": "male or female"}}

- "BMI between 18 and 35" → 
  {{"feature": "BMI", "operator": ">=", "value": 18, "unit": "kg/m²"}},
  {{"feature": "BMI", "operator": "<=", "value": 35, "unit": "kg/m²"}}

- "no clinical events suggestive of stroke" → 
  {{"feature": "patient", "operator": "!=", "value": "clinical events suggestive of stroke"}}

- "Ability to ingest oral medication" → 
  {{"feature": "patient", "operator": "=", "value": "ability to ingest oral medication"}}

**복잡한 구조 처리 예시**:
- 번호 리스트: "2. Age 50-85 years" → 
  {{"criterion_id": 1, "original_text": "Age ≥50 years", "feature": "age", "operator": ">=", "value": 50, "unit": "years", "confidence": 0.95}},
  {{"criterion_id": 2, "original_text": "Age ≤85 years", "feature": "age", "operator": "<=", "value": 85, "unit": "years", "confidence": 0.95}}
- 중첩 불릿: "3. Clinical findings consistent with:
       * other primary degenerative dementia" → 
  {{"criterion_id": 1, "original_text": "other primary degenerative dementia", "feature": "patient", "operator": "!=", "value": "other primary degenerative dementia", "unit": null, "confidence": 0.9}}
- 범위 조건: "6. Mild to moderate stage of AD according to MMSE ≥18 and ≤26" → 
  {{"criterion_id": 1, "original_text": "MMSE ≥18", "feature": "MMSE", "operator": ">=", "value": 18, "unit": null, "confidence": 0.95}},
  {{"criterion_id": 2, "original_text": "MMSE ≤26", "feature": "MMSE", "operator": "<=", "value": 26, "unit": null, "confidence": 0.95}}
- 복합 조건: "9. Absence of major depressive disease according to GDS of < 5" → 
  {{"feature": "GDS", "operator": "<", "value": 5, "unit": null, "confidence": 0.95}}
- 긴 문장: "4. Patients who show CSF biomarker data supporting the diagnosis of AD (for Czech Republic only: lumbar punctures can be performed for screening purposes), or patients with a positive Amyloid Pet Scan will qualify for the study" → 
  {{"feature": "patient", "operator": "=", "value": "CSF biomarker data supporting AD diagnosis or positive Amyloid Pet Scan", "unit": null, "confidence": 0.9}}

**핵심 원칙**:
- 하나의 불릿/문장 = 하나의 JSON 객체
- logic_operator, conditions 필드 절대 사용 금지
- feature에 구체적인 이름 직접 사용
- operator는 부등호 우선 (=, !=, <, <=, >, >=)
- 단순하고 직관적인 구조 유지"""

def get_inclusion_exclusion_preprocess_prompt(items_text: str) -> str:
    """Inclusion/Exclusion 전처리 프롬프트 생성"""
    return f"""다음 Inclusion/Exclusion Criteria를 구조화하세요.

데이터 형식: [nct_id]|[eligibility_criteria_raw]

{items_text}

{INCLUSION_EXCLUSION_PREPROCESS_RULES}

**중요: 반드시 JSON 배열만 반환하세요. 코드나 설명 없이 순수 JSON만 반환합니다.**

응답 형식 (JSON 배열):
[
  {{
    "nct_id": "NCT12345678",
    "inclusion_criteria": [
      {{
        "criterion_id": 1,
        "original_text": "age 50 or older",
        "feature": "age",
        "operator": ">=",
        "value": 50,
        "unit": "years",
        "confidence": 0.95
      }},
      {{
        "criterion_id": 2,
        "original_text": "Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease",
        "feature": "patient",
        "operator": "=",
        "value": "NINCDS-ADRDA criteria for probable Alzheimer's disease",
        "unit": null,
        "confidence": 0.95
      }},
      {{
        "criterion_id": 3,
        "original_text": "Patients must have disrupted sleep",
        "feature": "patient",
        "operator": "=",
        "value": "disrupted sleep",
        "unit": null,
        "confidence": 0.95
      }}
    ],
    "exclusion_criteria": [
      {{
        "criterion_id": 1,
        "original_text": "younger than 50 years",
        "feature": "age",
        "operator": "<",
        "value": 50,
        "unit": "years",
        "confidence": 0.95
      }},
      {{
        "criterion_id": 2,
        "original_text": "T.I.A or Major infarction within the last 12 months",
        "feature": "T.I.A or Major infarction",
        "operator": "<=",
        "value": 12,
        "unit": "months",
        "confidence": 0.9
      }}
    ]
  }},
  {{
    "nct_id": "NCT87654321",
    "inclusion_criteria": [
      {{
        "criterion_id": 1,
        "original_text": "Global CDR score = 0.5",
        "feature": "Global CDR",
        "operator": "=",
        "value": 0.5,
        "unit": null,
        "confidence": 0.95
      }},
      {{
        "criterion_id": 2,
        "original_text": "NYU Delayed Paragraph Recall < 9",
        "feature": "NYU Delayed Paragraph Recall",
        "operator": "<",
        "value": 9,
        "unit": null,
        "confidence": 0.95
      }}
    ],
    "exclusion_criteria": []
  }}
]

**반드시 위 형식의 JSON 배열만 반환하세요. 코드나 설명 텍스트는 포함하지 마세요.**

**⚠️ 필수: 각 JSON 객체의 최상위 레벨에 반드시 "nct_id" 필드를 포함하세요. 입력 데이터의 첫 번째 부분(nct_id)을 그대로 사용하세요. nct_id가 없으면 응답이 무효화됩니다.**

**절대 사용하지 마세요**:
- logic_operator 필드
- conditions 필드
- test_name 필드
- feature에 카테고리만 사용 (예: "CONDITION", "LAB_VALUE", "GENDER", "AGE" 등)

**중요 원칙**:
- 하나의 불릿/문장 = 하나의 JSON 객체
- feature는 문장의 주체(subject): "patient", "age", "gender", "MMSE" 등
- value는 조건/상태/값: "NINCDS-ADRDA criteria", "disrupted sleep", 50, "male" 등
  * 올바름: feature: "patient", value: "NINCDS-ADRDA criteria"
  * 올바름: feature: "age", value: 50
  * 올바름: feature: "MMSE", value: 10
  * 잘못됨: feature: "CONDITION", value: null (카테고리 사용 금지, null 사용 금지)
- operator는 무조건 부등호만 사용 (=, !=, <, <=, >, >=)
- "present", "absent", "within", "between" 같은 텍스트는 모두 부등호로 변환
- **value는 절대 null이 될 수 없습니다**: 값이 명시되지 않은 경우에도 적절한 문자열 사용
- notes 필드 절대 사용 금지
- 무조건 feature operator value 형식으로 작성
- feature = 주체(항목명), operator = 부등호, value = 조건/상태/값 (null 불가)
"""

# ============================================================================
# Inclusion/Exclusion 검증 프롬프트
# ============================================================================

INCLUSION_EXCLUSION_VALIDATION_RULES = """규칙:
- 원본 eligibilityCriteria 텍스트와 LLM 전처리 결과를 비교
- Inclusion Criteria 검증: 원본 텍스트의 Inclusion 섹션과 전처리된 inclusion_criteria 비교
- Exclusion Criteria 검증: 원본 텍스트의 Exclusion 섹션과 전처리된 exclusion_criteria 비교
- Feature 분류 정확성 확인
- Operator 추출 정확성 확인
- Value 추출 정확성 확인
- 논리 연산자 처리 정확성 확인

검증 상태:
- VERIFIED: Inclusion과 Exclusion 모두 검증 성공
- UNCERTAIN: 불확실 (일부 불일치 또는 애매한 경우)
- INCLUSION_FAILED: Inclusion 검증 실패
- EXCLUSION_FAILED: Exclusion 검증 실패
- BOTH_FAILED: 둘 다 검증 실패

Notes 작성 형식: [문제유형] 간단설명. 상세내용.
문제유형: [INCLUSION_MISMATCH] [EXCLUSION_MISMATCH] [FEATURE_MISMATCH] [OPERATOR_MISMATCH] [VALUE_MISMATCH] [LOGIC_MISMATCH] [VERIFIED]
예: [INCLUSION_MISMATCH] Inclusion 항목 누락. 원본에 'age 50 or older'가 있는데 전처리 결과에 없음.
예: [FEATURE_MISMATCH] Feature 분류 오류. 'diabetes'가 CONDITION이어야 하는데 OTHER로 분류됨.
예: [VERIFIED] 모든 값 일치.

중요: 응답 시 각 항목의 첫 문자열(nct_id)을 반드시 포함해야 함."""

def get_inclusion_exclusion_validation_prompt(items_text: str) -> str:
    """Inclusion/Exclusion 검증 프롬프트 생성"""
    return f"""{items_text}

{INCLUSION_EXCLUSION_VALIDATION_RULES}

응답: 각 항목의 첫 문자열(nct_id)을 포함하여 JSON 배열로 응답.
[{{"nct_id": "NCT12345678", "status": "VERIFIED|UNCERTAIN|INCLUSION_FAILED|EXCLUSION_FAILED|BOTH_FAILED", "confidence": 0~1, "notes": "요약"}}, ...]"""
