# Inclusion/Exclusion 테이블 구조 설계

## 1. 전체 구조 개요

```
inclusion_exclusion_raw (원본 데이터)
    ↓
inclusion_exclusion_llm_preprocessed (LLM 전처리 결과)
    ├─ inclusion_criteria (JSONB 배열)
    └─ exclusion_criteria (JSONB 배열)
```

## 2. 테이블 구조

### 2.1 inclusion_exclusion_raw (원본 데이터)

```sql
CREATE TABLE inclusion_exclusion_raw (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,  -- 전체 eligibilityCriteria 텍스트
    phase VARCHAR(50),  -- Phase 정보
    source_version VARCHAR(50),
    raw_json JSONB,  -- 원본 study JSON
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_inclusion_exclusion_raw UNIQUE (nct_id)
);

CREATE INDEX idx_inclusion_exclusion_raw_nct_id ON inclusion_exclusion_raw(nct_id);
CREATE INDEX idx_inclusion_exclusion_raw_phase ON inclusion_exclusion_raw(phase);
```

### 2.2 inclusion_exclusion_llm_preprocessed (LLM 전처리 결과)

```sql
CREATE TABLE inclusion_exclusion_llm_preprocessed (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,  -- 원본 텍스트
    phase VARCHAR(50),

    -- LLM 전처리 결과: Inclusion Criteria (JSONB 배열)
    inclusion_criteria JSONB,  -- Inclusion 항목 배열

    -- LLM 전처리 결과: Exclusion Criteria (JSONB 배열)
    exclusion_criteria JSONB,  -- Exclusion 항목 배열

    -- 메타데이터
    llm_confidence NUMERIC(3,2),  -- LLM 신뢰도 (0.00 ~ 1.00)
    llm_notes TEXT,  -- LLM 처리 노트
    parsing_method VARCHAR(20) DEFAULT 'LLM',
    llm_status VARCHAR(20),  -- SUCCESS, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED, API_FAILED
    failure_reason VARCHAR(50),

    -- 검증 결과 (나중에 추가 가능)
    llm_validation_status VARCHAR(20),
    llm_validation_confidence NUMERIC(3,2),
    llm_validation_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_inclusion_exclusion_llm UNIQUE (nct_id)
);

CREATE INDEX idx_inclusion_exclusion_llm_nct_id ON inclusion_exclusion_llm_preprocessed(nct_id);
CREATE INDEX idx_inclusion_exclusion_llm_phase ON inclusion_exclusion_llm_preprocessed(phase);
CREATE INDEX idx_inclusion_exclusion_llm_status ON inclusion_exclusion_llm_preprocessed(llm_status);
CREATE INDEX idx_inclusion_exclusion_llm_inclusion ON inclusion_exclusion_llm_preprocessed USING GIN (inclusion_criteria);
CREATE INDEX idx_inclusion_exclusion_llm_exclusion ON inclusion_exclusion_llm_preprocessed USING GIN (exclusion_criteria);
```

## 3. JSONB 구조 설계

### 3.1 Inclusion/Exclusion 항목 구조 (Feature-Operator-Value 패턴 + 논리 연산자)

각 항목은 다음과 같은 구조를 가집니다:

**기본 구조:**

```json
{
  "criterion_id": 1, // 항목 순서 (1부터 시작)
  "original_text": "age 50 or older", // 원본 텍스트
  "feature": "AGE", // 특성/카테고리
  "operator": ">=", // 연산자 (선택적, 값이 없으면 null)
  "value": 50, // 값 (선택적, 값이 없으면 null)
  "unit": "years", // 단위 (선택적)
  "confidence": 0.95, // LLM 신뢰도
  "notes": "Age requirement clearly stated" // 추가 노트
}
```

**복합 조건 (AND/OR 포함):**

```json
{
  "criterion_id": 1,
  "original_text": "MMSE 10-22 and ADAS greater than or equal to 18",
  "logic_operator": "AND", // 논리 연산자: AND, OR (복합 조건인 경우)
  "conditions": [
    // 하위 조건 배열
    {
      "feature": "LAB_VALUE",
      "operator": "BETWEEN",
      "value": [10, 22],
      "unit": null,
      "test_name": "MMSE"
    },
    {
      "feature": "LAB_VALUE",
      "operator": ">=",
      "value": 18,
      "unit": null,
      "test_name": "ADAS"
    }
  ],
  "confidence": 0.9,
  "notes": "Combined MMSE and ADAS requirements"
}
```

**값이 없는 경우 (카테고리만):**

```json
{
  "criterion_id": 1,
  "original_text": "Probable Alzheimer's disease",
  "feature": "CONDITION",
  "operator": null, // 값이 없으면 null
  "value": "Alzheimer's disease", // 또는 null (카테고리만 있는 경우)
  "unit": null,
  "confidence": 0.85,
  "notes": "Diagnosis requirement without specific criteria"
}
```

### 3.2 Feature 카테고리 정의

```sql
-- Feature 타입 (VARCHAR로 저장, 다음 중 하나)
'AGE'              -- 나이
'GENDER'           -- 성별
'CONDITION'        -- 질환/상태 (예: diabetes, hypertension)
'MEDICATION'       -- 약물 관련
'LAB_VALUE'        -- 검사 수치 (예: hemoglobin, creatinine)
'PREGNANCY'        -- 임신 관련
'SURGERY'          -- 수술 관련
'PERFORMANCE_STATUS'  -- Performance status (예: ECOG, Karnofsky)
'LIFE_EXPECTANCY'  -- 기대 생존 기간
'ORGAN_FUNCTION'   -- 장기 기능 (예: liver function, kidney function)
'ALLERGY'          -- 알레르기
'CONTRACEPTION'    -- 피임
'CONSENT'          -- 동의/서명
'OTHER'            -- 기타
```

### 3.3 Operator 정의

```sql
-- Operator 타입 (VARCHAR로 저장)
'>='              -- 이상 (greater than or equal)
'<='              -- 이하 (less than or equal)
'>'               -- 초과 (greater than)
'<'               -- 미만 (less than)
'='               -- 같음 (equal)
'!='              -- 같지 않음 (not equal)
'IN'              -- 포함 (in list)
'NOT_IN'          -- 미포함 (not in list)
'CONTAINS'        -- 포함 (contains text)
'NOT_CONTAINS'    -- 미포함 (not contains text)
'BETWEEN'         -- 범위 (between A and B)
'NOT_BETWEEN'     -- 범위 외 (not between A and B)
'PRESENT'         -- 존재함 (present/exists)
'ABSENT'           -- 존재하지 않음 (absent/not exists)
```

### 3.4 Value 타입

- **숫자**: `50`, `18.5`, `100`
- **문자열**: `"male"`, `"diabetes"`, `"Alzheimer's disease"`
- **배열**: `[18, 65]` (BETWEEN 연산자 사용 시)
- **NULL**:
  - operator가 `PRESENT`/`ABSENT`인 경우
  - 값이 명시되지 않은 경우 (카테고리만 있는 경우)

### 3.5 논리 연산자 (Logic Operator)

복합 조건을 표현하기 위한 논리 연산자:

```sql
-- Logic Operator 타입 (VARCHAR로 저장, 최상위 조건에만 사용)
'AND'              -- 모든 조건을 만족해야 함
'OR'               -- 하나 이상의 조건을 만족하면 됨
null               -- 단일 조건인 경우 (논리 연산자 없음)
```

**사용 규칙:**

- 단일 조건: `logic_operator` = null, `conditions` 필드 없음
- 복합 조건: `logic_operator` = "AND" 또는 "OR", `conditions` 배열에 하위 조건들 포함

## 4. 실제 데이터 예시 (복잡한 케이스 포함)

### 4.1 예시 1: 간단한 나이 조건

**원본 텍스트:**

```
Inclusion Criteria:
age 50 or older

Exclusion Criteria:
younger than 50 years
```

**JSONB 구조:**

```json
{
  "inclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "age 50 or older",
      "feature": "AGE",
      "operator": ">=",
      "value": 50,
      "unit": "years",
      "confidence": 0.98,
      "notes": "Clear age requirement"
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "younger than 50 years",
      "feature": "AGE",
      "operator": "<",
      "value": 50,
      "unit": "years",
      "confidence": 0.98,
      "notes": "Clear age exclusion"
    }
  ]
}
```

### 4.2 예시 2: 복잡한 조건 (질환 + 나이)

**원본 텍스트:**

```
Inclusion Criteria:
- Patients with diabetes
- Age between 18 and 65 years

Exclusion Criteria:
- History of cancer (except non-melanoma skin cancer)
- Pregnant or nursing women
```

**JSONB 구조:**

```json
{
  "inclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Patients with diabetes",
      "feature": "CONDITION",
      "operator": "PRESENT",
      "value": "diabetes",
      "unit": null,
      "confidence": 0.92,
      "notes": "Diabetes condition required"
    },
    {
      "criterion_id": 2,
      "original_text": "Age between 18 and 65 years",
      "feature": "AGE",
      "operator": "BETWEEN",
      "value": [18, 65],
      "unit": "years",
      "confidence": 0.95,
      "notes": "Age range specified"
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "History of cancer (except non-melanoma skin cancer)",
      "feature": "CONDITION",
      "operator": "PRESENT",
      "value": "cancer",
      "unit": null,
      "confidence": 0.88,
      "notes": "Cancer history excluded, with exception for non-melanoma skin cancer"
    },
    {
      "criterion_id": 2,
      "original_text": "Pregnant or nursing women",
      "feature": "PREGNANCY",
      "operator": "PRESENT",
      "value": "pregnant_or_nursing",
      "unit": null,
      "confidence": 0.9,
      "notes": "Pregnancy/nursing status exclusion"
    }
  ]
}
```

### 4.3 예시 3: 검사 수치 조건

**원본 텍스트:**

```
Inclusion Criteria:
- Hemoglobin >= 10 g/dL
- Creatinine clearance >= 30 mL/min
```

**JSONB 구조:**

```json
{
  "inclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Hemoglobin >= 10 g/dL",
      "feature": "LAB_VALUE",
      "operator": ">=",
      "value": 10,
      "unit": "g/dL",
      "confidence": 0.95,
      "notes": "Hemoglobin level requirement"
    },
    {
      "criterion_id": 2,
      "original_text": "Creatinine clearance >= 30 mL/min",
      "feature": "LAB_VALUE",
      "operator": ">=",
      "value": 30,
      "unit": "mL/min",
      "confidence": 0.95,
      "notes": "Creatinine clearance requirement"
    }
  ],
  "exclusion_criteria": []
}
```

### 4.4 예시 4: 복잡한 실제 데이터 (AND 조건 포함)

**원본 텍스트:**

```
Inclusion Criteria:
- Probable Alzheimer's disease
- Mini-Mental State Examination (MMSE) 10-22 and ADAS greater than or equal to 18
- Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18
- Opportunity for Activities of Daily Living
- Caregiver: Subjects who live with or have regular daily visits from a responsible caregiver

Exclusion Criteria:
- Conditions that could confound diagnosis
- Neurodegenerative disorders
- Acute cerebral trauma
- Psychiatric disease
- More than one infarct on CT/MRI scans
- History of alcohol or drug abuse
- Contradictions for a cholinominetic agent: seizures; ulcers; pulmonary conditions (including severe asthma); unstable angina; Afib; bradycardia less than 50; and AV block.
```

**JSONB 구조:**

```json
{
  "inclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Probable Alzheimer's disease",
      "feature": "CONDITION",
      "operator": null,
      "value": "Alzheimer's disease",
      "unit": null,
      "confidence": 0.85,
      "notes": "Diagnosis requirement"
    },
    {
      "criterion_id": 2,
      "original_text": "Mini-Mental State Examination (MMSE) 10-22 and ADAS greater than or equal to 18",
      "logic_operator": "AND",
      "conditions": [
        {
          "feature": "LAB_VALUE",
          "operator": "BETWEEN",
          "value": [10, 22],
          "unit": null,
          "test_name": "MMSE"
        },
        {
          "feature": "LAB_VALUE",
          "operator": ">=",
          "value": 18,
          "unit": null,
          "test_name": "ADAS"
        }
      ],
      "confidence": 0.9,
      "notes": "Combined MMSE and ADAS requirements"
    },
    {
      "criterion_id": 3,
      "original_text": "Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18",
      "feature": "LAB_VALUE",
      "operator": ">=",
      "value": 18,
      "unit": null,
      "test_name": "ADAS-cog-11",
      "confidence": 0.92,
      "notes": "ADAS-cog-11 score requirement"
    },
    {
      "criterion_id": 4,
      "original_text": "Opportunity for Activities of Daily Living",
      "feature": "OTHER",
      "operator": null,
      "value": null,
      "unit": null,
      "confidence": 0.75,
      "notes": "General requirement without specific criteria"
    },
    {
      "criterion_id": 5,
      "original_text": "Caregiver: Subjects who live with or have regular daily visits from a responsible caregiver",
      "feature": "OTHER",
      "operator": null,
      "value": "caregiver_required",
      "unit": null,
      "confidence": 0.88,
      "notes": "Caregiver requirement with detailed description"
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Conditions that could confound diagnosis",
      "feature": "CONDITION",
      "operator": null,
      "value": null,
      "unit": null,
      "confidence": 0.7,
      "notes": "General exclusion category without specific conditions"
    },
    {
      "criterion_id": 2,
      "original_text": "Neurodegenerative disorders",
      "feature": "CONDITION",
      "operator": null,
      "value": "neurodegenerative_disorders",
      "unit": null,
      "confidence": 0.9,
      "notes": "Neurodegenerative disorders exclusion"
    },
    {
      "criterion_id": 3,
      "original_text": "Acute cerebral trauma",
      "feature": "CONDITION",
      "operator": null,
      "value": "acute_cerebral_trauma",
      "unit": null,
      "confidence": 0.92,
      "notes": "Acute cerebral trauma exclusion"
    },
    {
      "criterion_id": 4,
      "original_text": "Psychiatric disease",
      "feature": "CONDITION",
      "operator": null,
      "value": "psychiatric_disease",
      "unit": null,
      "confidence": 0.88,
      "notes": "Psychiatric disease exclusion"
    },
    {
      "criterion_id": 5,
      "original_text": "More than one infarct on CT/MRI scans",
      "feature": "CONDITION",
      "operator": ">",
      "value": 1,
      "unit": "infarcts",
      "confidence": 0.9,
      "notes": "Multiple infarcts exclusion"
    },
    {
      "criterion_id": 6,
      "original_text": "History of alcohol or drug abuse",
      "feature": "CONDITION",
      "operator": null,
      "value": "alcohol_or_drug_abuse",
      "unit": null,
      "confidence": 0.92,
      "notes": "Substance abuse history exclusion"
    },
    {
      "criterion_id": 7,
      "original_text": "Contradictions for a cholinominetic agent: seizures; ulcers; pulmonary conditions (including severe asthma); unstable angina; Afib; bradycardia less than 50; and AV block.",
      "logic_operator": "OR",
      "conditions": [
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "seizures",
          "unit": null
        },
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "ulcers",
          "unit": null
        },
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "pulmonary_conditions",
          "unit": null,
          "notes": "Including severe asthma"
        },
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "unstable_angina",
          "unit": null
        },
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "atrial_fibrillation",
          "unit": null
        },
        {
          "feature": "LAB_VALUE",
          "operator": "<",
          "value": 50,
          "unit": "bpm",
          "test_name": "bradycardia"
        },
        {
          "feature": "CONDITION",
          "operator": null,
          "value": "AV_block",
          "unit": null
        }
      ],
      "confidence": 0.85,
      "notes": "Multiple contraindications for cholinominetic agent"
    }
  ]
}
```

## 5. 쿼리 예시

### 5.1 특정 나이 조건 검색

```sql
-- 나이 50세 이상인 Inclusion 조건 찾기
SELECT nct_id, inclusion_criteria
FROM inclusion_exclusion_llm_preprocessed
WHERE inclusion_criteria @> '[{"feature": "AGE", "operator": ">=", "value": 50}]'::jsonb;
```

### 5.2 특정 질환 조건 검색

```sql
-- Diabetes가 Inclusion 조건인 경우
SELECT nct_id, inclusion_criteria
FROM inclusion_exclusion_llm_preprocessed
WHERE inclusion_criteria @> '[{"feature": "CONDITION", "value": "diabetes"}]'::jsonb;
```

### 5.3 복합 조건 검색

```sql
-- 나이 18-65세이고 Diabetes가 Inclusion 조건인 경우
SELECT nct_id, inclusion_criteria
FROM inclusion_exclusion_llm_preprocessed
WHERE inclusion_criteria @> '[{"feature": "AGE", "operator": "BETWEEN", "value": [18, 65]}]'::jsonb
  AND inclusion_criteria @> '[{"feature": "CONDITION", "value": "diabetes"}]'::jsonb;
```

## 6. LLM 프롬프트 설계 고려사항

1. **Feature 분류**: LLM이 텍스트를 읽고 적절한 feature 카테고리로 분류
2. **Operator 추출**: 자연어를 연산자로 변환
   - "50 or older" → `>=`, `50`
   - "younger than 50" → `<`, `50`
   - "between 18 and 65" → `BETWEEN`, `[18, 65]`
3. **Value 추출**: 숫자, 문자열, 배열 등 적절한 형태로 추출
4. **Unit 추출**: 단위가 명시된 경우 추출 (years, months, g/dL, mL/min 등)

## 7. Feature 사전 등록 (향후 계획)

나중에 실제 데이터를 분석하여 자주 나오는 feature들을 사전에 등록:

```sql
CREATE TABLE inclusion_exclusion_feature_dict (
    feature_code VARCHAR(50) PRIMARY KEY,
    feature_name VARCHAR(200) NOT NULL,
    category VARCHAR(50),  -- AGE, CONDITION, LAB_VALUE 등
    canonical_name VARCHAR(200),  -- 표준화된 이름
    synonyms TEXT[],  -- 동의어 배열
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**예시:**

- `feature_code`: "ALZHEIMERS_DISEASE"
- `feature_name`: "Alzheimer's Disease"
- `category`: "CONDITION"
- `canonical_name`: "Alzheimer Disease"
- `synonyms`: ["AD", "Alzheimer", "Alzheimers", "probable Alzheimer's disease"]

## 8. 확장 가능성

나중에 필요하면:

- **예외 처리**: "except non-melanoma skin cancer" 같은 예외 조건을 별도 필드로 추가
- **시간 조건**: "within 6 months" 같은 시간 제약을 별도 필드로 추가
- **중첩 논리**: AND/OR의 중첩 구조 (현재는 2단계까지만 지원)
- **조건 그룹**: 여러 조건을 하나의 그룹으로 묶기
