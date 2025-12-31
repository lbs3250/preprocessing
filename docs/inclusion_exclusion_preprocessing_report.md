# Inclusion/Exclusion LLM 전처리 결과 보고서

생성일: 2025-12-30 18:39:12

## 1. 전체 통계

### 1.1 처리 현황

- **전체 레코드**: 1,320개
- **성공 (SUCCESS)**: 1,270개 (96.21%)
- **Inclusion 실패**: 0개 (0.00%)
- **Exclusion 실패**: 0개 (0.00%)
- **둘 다 실패**: 20개 (1.52%)
- **API 실패**: 30개 (2.27%)

### 1.2 추출 통계

- **Inclusion Criteria 추출**: 1,270개 (96.21%)
- **Exclusion Criteria 추출**: 1,270개 (96.21%)
- **완전 파싱 (둘 다)**: 1,270개 (96.21%)

### 1.3 Criteria 개수 통계

- **평균 Inclusion Criteria 개수**: 10.8개
- **평균 Exclusion Criteria 개수**: 15.6개
- **최대 Inclusion Criteria 개수**: 76개
- **최대 Exclusion Criteria 개수**: 106개
- **최소 Inclusion Criteria 개수**: 1개
- **최소 Exclusion Criteria 개수**: 1개

### 1.4 주요 Feature 분포 (상위 10개)

| 순위 | Feature    | 사용 횟수 |
| ---- | ---------- | --------- |
| 1    | patient    | 6,026     |
| 2    | age        | 1,360     |
| 3    | gender     | 647       |
| 4    | MMSE score | 512       |
| 5    | MMSE       | 473       |
| 6    | diagnosis  | 407       |
| 7    | BMI        | 392       |
| 8    | subject    | 363       |
| 9    | caregiver  | 290       |
| 10   | medication | 245       |

## 2. 전처리 결과 예시

### 2.1 성공 샘플 #1

**NCT ID**: `NCT00000172`

**원본 Eligibility Criteria**:

```
Inclusion Criteria:

* Probable Alzheimer's disease
* Mini-Mental State Examination (MMSE) 10-22 and ADAS greater than or equal to 18
* Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18
* Opportunity for Activities of Daily Living
* Caregiver
* Subjects who live with or have regular daily visits from a responsible caregiver (visit frequency: preferably daily but at least 5 days/week). This includes a friend or relative or paid personnel. The caregiver shou...
```

**전처리 결과**:

- Inclusion Criteria 개수: 8개
- Exclusion Criteria 개수: 13개
- Confidence: N/A

**Inclusion Criteria 예시** (처음 5개):

1. **원본**: `Probable Alzheimer's disease`

   - Feature: `patient`
   - Operator: `=`
   - Value: `probable Alzheimer's disease`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Mini-Mental State Examination (MMSE) >= 10`

   - Feature: `MMSE`
   - Operator: `>=`
   - Value: `10`
   - Unit: `null`
   - Confidence: `0.9`

3. **원본**: `Mini-Mental State Examination (MMSE) <= 22`

   - Feature: `MMSE`
   - Operator: `<=`
   - Value: `22`
   - Unit: `null`
   - Confidence: `0.9`

4. **원본**: `ADAS greater than or equal to 18`

   - Feature: `ADAS`
   - Operator: `>=`
   - Value: `18`
   - Unit: `null`
   - Confidence: `0.9`

5. **원본**: `Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18`
   - Feature: `ADAS-cog-11 score`
   - Operator: `>=`
   - Value: `18`
   - Unit: `null`
   - Confidence: `0.95`

**Exclusion Criteria 예시** (처음 5개):

1. **원본**: `Conditions that could confound diagnosis`

   - Feature: `conditions`
   - Operator: `=`
   - Value: `could confound diagnosis`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Neurodegenerative disorders`

   - Feature: `neurodegenerative disorders`
   - Operator: `=`
   - Value: `present`
   - Unit: `null`
   - Confidence: `0.95`

3. **원본**: `Acute cerebral trauma`

   - Feature: `acute cerebral trauma`
   - Operator: `=`
   - Value: `present`
   - Unit: `null`
   - Confidence: `0.95`

4. **원본**: `Psychiatric disease`

   - Feature: `psychiatric disease`
   - Operator: `=`
   - Value: `present`
   - Unit: `null`
   - Confidence: `0.95`

5. **원본**: `More than one infarct on CT/MRI scans`
   - Feature: `infarcts on CT/MRI scans`
   - Operator: `>`
   - Value: `1`
   - Unit: `null`
   - Confidence: `0.95`

---

### 2.2 성공 샘플 #2

**NCT ID**: `NCT00000173`

**원본 Eligibility Criteria**:

```
Inclusion Criteria:

* Memory complaints and memory difficulties which are verified by an informant.
* Abnormal memory function documented by scoring below the education adjusted cutoff on the Logical Memory II subscale (Delayed Paragraph Recall) from the Wechsler Memory Scale - Revised (the maximum score is 25): a) less than or equal to 8 for 16 or more years of education, b) less than or equal to 4 for 8-15 years of education, c) less than or equal to 2 for 0-7 years of education.
* Mini-Menta...
```

**전처리 결과**:

- Inclusion Criteria 개수: 23개
- Exclusion Criteria 개수: 30개
- Confidence: N/A

**Inclusion Criteria 예시** (처음 5개):

1. **원본**: `Memory complaints and memory difficulties which are verified by an informant.`

   - Feature: `memory complaints and difficulties`
   - Operator: `=`
   - Value: `verified by an informant`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Abnormal memory function documented by scoring below the education adjusted cutoff on the Logical Memory II subscale (Delayed Paragraph Recall) from t...`

   - Feature: `Logical Memory II subscale score`
   - Operator: `=`
   - Value: `below education adjusted cutoff (<=8 for >=16 yrs education, <=4 for 8-15 yrs education, <=2 for 0-7 yrs education)`
   - Unit: `null`
   - Confidence: `0.95`

3. **원본**: `Mini-Mental Exam score >= 24`

   - Feature: `Mini-Mental Exam score`
   - Operator: `>=`
   - Value: `24`
   - Unit: `null`
   - Confidence: `0.9`

4. **원본**: `Mini-Mental Exam score <= 30`

   - Feature: `Mini-Mental Exam score`
   - Operator: `<=`
   - Value: `30`
   - Unit: `null`
   - Confidence: `0.9`

5. **원본**: `Clinical Dementia Rating = 0.5`
   - Feature: `Clinical Dementia Rating`
   - Operator: `=`
   - Value: `0.5`
   - Unit: `null`
   - Confidence: `0.9`

**Exclusion Criteria 예시** (처음 5개):

1. **원본**: `Any significant neurologic disease other than suspected incipient Alzheimer's disease, such as Parkinson's disease, multi-infarct dementia, Huntington...`

   - Feature: `neurologic disease`
   - Operator: `=`
   - Value: `significant, other than suspected incipient Alzheimer's disease`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Major depression or another major psychiatric disorder as described in DSM IV within the past 2 years.`

   - Feature: `major depression or major psychiatric disorder (DSM IV)`
   - Operator: `<=`
   - Value: `2`
   - Unit: `years`
   - Confidence: `0.95`

3. **원본**: `Psychotic features, agitation or behavioral problems within the last 3 months which could lead to difficulty complying with the protocol.`

   - Feature: `psychotic features, agitation or behavioral problems`
   - Operator: `<=`
   - Value: `3`
   - Unit: `months`
   - Confidence: `0.95`

4. **원본**: `History of alcohol or substance abuse or dependence within the past 2 years (DSM IV criteria).`

   - Feature: `alcohol or substance abuse or dependence history (DSM IV)`
   - Operator: `<=`
   - Value: `2`
   - Unit: `years`
   - Confidence: `0.95`

5. **원본**: `History of schizophrenia (DSM IV criteria).`
   - Feature: `schizophrenia history (DSM IV)`
   - Operator: `=`
   - Value: `present`
   - Unit: `null`
   - Confidence: `0.95`

---

### 2.3 성공 샘플 #3

**NCT ID**: `NCT00000171`

**원본 Eligibility Criteria**:

```
Inclusion Criteria:

* Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease (AD). Patients must have disrupted sleep, documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors.
* A diagnosis of probable AD.
* MMSE score 0-26.
* Hachinski Ischemia Scale score less than or equal to 4.
* A 2-week history of two or more sleep disorder behaviors, occurring at least once weekly, as reported by the caregiver on the Sleep Disorder Inventory.
* CT ...
```

**전처리 결과**:

- Inclusion Criteria 개수: 17개
- Exclusion Criteria 개수: 15개
- Confidence: N/A

**Inclusion Criteria 예시** (처음 5개):

1. **원본**: `Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease (AD).`

   - Feature: `patient`
   - Operator: `=`
   - Value: `NINCDS-ADRDA criteria for probable Alzheimer's disease (AD)`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Patients must have disrupted sleep, documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors.`

   - Feature: `patient`
   - Operator: `=`
   - Value: `disrupted sleep documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors`
   - Unit: `null`
   - Confidence: `0.95`

3. **원본**: `A diagnosis of probable AD.`

   - Feature: `patient`
   - Operator: `=`
   - Value: `diagnosis of probable AD`
   - Unit: `null`
   - Confidence: `0.95`

4. **원본**: `MMSE score >= 0`

   - Feature: `MMSE score`
   - Operator: `>=`
   - Value: `0`
   - Unit: `null`
   - Confidence: `0.9`

5. **원본**: `MMSE score <= 26`
   - Feature: `MMSE score`
   - Operator: `<=`
   - Value: `26`
   - Unit: `null`
   - Confidence: `0.9`

**Exclusion Criteria 예시** (처음 5개):

1. **원본**: `Sleep disturbance is acute (within the last 2 weeks).`

   - Feature: `sleep disturbance`
   - Operator: `=`
   - Value: `acute (within the last 2 weeks)`
   - Unit: `null`
   - Confidence: `0.95`

2. **원본**: `Sleep disturbance is associated with an acute illness with delirium.`

   - Feature: `sleep disturbance`
   - Operator: `=`
   - Value: `associated with an acute illness with delirium`
   - Unit: `null`
   - Confidence: `0.95`

3. **원본**: `Clinically significant movement disorder that would interfere with the actigraph readings.`

   - Feature: `movement disorder`
   - Operator: `=`
   - Value: `clinically significant, interfering with actigraph readings`
   - Unit: `null`
   - Confidence: `0.95`

4. **원본**: `Not having a mobile upper extremity to which to attach an actigraph.`

   - Feature: `mobile upper extremity for actigraph`
   - Operator: `!=`
   - Value: `present`
   - Unit: `null`
   - Confidence: `0.95`

5. **원본**: `Severe agitation.`
   - Feature: `agitation`
   - Operator: `=`
   - Value: `severe`
   - Unit: `null`
   - Confidence: `0.95`

---

## 3. 범위 조건 처리 예시

범위 조건(예: "MMSE ≥18 and ≤26", "Age 50-85 years")은 두 개의 별도 criterion으로 분리되어 처리됩니다.

### 3.1 범위 조건 샘플 #1

**NCT ID**: `NCT00000171`

**원본 Eligibility Criteria**:

```
Inclusion Criteria:

* Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease (AD). Patients must have disrupted sleep, documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors.
* A diagnosis of probable AD.
* MMSE score 0-26.
* Hachinski Ische...
```

**범위 조건이 포함된 Inclusion Criteria**:

1. **MMSE score >= 0**

   - Feature: `MMSE score`
   - Operator: `>=`
   - Value: `0`
   - Unit: `None`

2. **MMSE score <= 26**

   - Feature: `MMSE score`
   - Operator: `<=`
   - Value: `26`
   - Unit: `None`

3. **Hachinski Ischemia Scale score less than or equal to 4.**

   - Feature: `Hachinski Ischemia Scale score`
   - Operator: `<=`
   - Value: `4`
   - Unit: `None`

4. **Actigraph evidence of a mean nocturnal sleep time of less than 7 hours per night (at least 5 nights **

   - Feature: `mean nocturnal sleep time`
   - Operator: `<`
   - Value: `7`
   - Unit: `hours per night`

5. **55 years of age or older.**

   - Feature: `age`
   - Operator: `>=`
   - Value: `55`
   - Unit: `years`

6. **Hamilton Depression Rating Scale score of 15 or less.**
   - Feature: `Hamilton Depression Rating Scale score`
   - Operator: `<=`
   - Value: `15`
   - Unit: `None`

---

### 3.2 범위 조건 샘플 #2

**NCT ID**: `NCT00000172`

**원본 Eligibility Criteria**:

```
Inclusion Criteria:

* Probable Alzheimer's disease
* Mini-Mental State Examination (MMSE) 10-22 and ADAS greater than or equal to 18
* Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18
* Opportunity for Activities of Daily Living
* Caregiver
* Subjects who li...
```

**범위 조건이 포함된 Inclusion Criteria**:

1. **Mini-Mental State Examination (MMSE) >= 10**

   - Feature: `MMSE`
   - Operator: `>=`
   - Value: `10`
   - Unit: `None`

2. **Mini-Mental State Examination (MMSE) <= 22**

   - Feature: `MMSE`
   - Operator: `<=`
   - Value: `22`
   - Unit: `None`

3. **ADAS greater than or equal to 18**

   - Feature: `ADAS`
   - Operator: `>=`
   - Value: `18`
   - Unit: `None`

4. **Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18**
   - Feature: `ADAS-cog-11 score`
   - Operator: `>=`
   - Value: `18`
   - Unit: `None`

---

## 4. 전처리 특징

### 4.1 범위 조건 처리

- 범위 조건은 **두 개의 별도 criterion으로 분리**되어 처리됩니다
- 예: "MMSE ≥18 and ≤26" →
  - `{"feature": "MMSE", "operator": ">=", "value": 18}`
  - `{"feature": "MMSE", "operator": "<=", "value": 26}`
- Inclusion criteria는 기본적으로 AND 로직이므로, 두 개로 분리해도 문제없습니다

### 4.2 Feature 추출

- 가장 많이 사용되는 feature는 `patient` (6,026회)
- 나이, 성별, 검사 수치(MMSE, BMI 등)가 주요 feature로 추출됨
- 환자/참가자 관련 조건은 `patient` 또는 `subject`로 통일

### 4.3 Operator 변환

- 모든 자연어 표현이 표준 수학 연산자로 변환됨
- 사용되는 operator: `=`, `!=`, `<`, `<=`, `>`, `>=`
- "present", "absent", "within", "between" 같은 텍스트는 모두 부등호로 변환

### 4.4 Value 추출

- 숫자: 50, 18.5, 12 등
- 문자열: "male", "diabetes", "NINCDS-ADRDA criteria" 등
- 조건/상태: feature가 "patient"인 경우, value는 조건이나 상태를 나타내는 문자열
- **절대 null 사용 금지**: 값이 명시되지 않은 경우에도 적절한 문자열 사용

## 5. 실패 사례 분석

### 5.1 실패 유형

- **BOTH_FAILED**: 20개 (1.52%)
  - 주요 원인: `[PARSE_ERROR] LLM 응답에 nct_id가 없음. 모든 복구 시도 실패.`
- **API_FAILED**: 30개 (2.27%)
  - API 호출 실패

### 5.2 개선 사항

- nct_id 복구 로직 추가로 대부분의 nct_id 누락 문제 해결
- 순서 기반 복구 메커니즘으로 파싱 실패 시에도 데이터 복구 시도

## 6. 전처리 결과 JSON 구조 예시

### 6.1 전체 JSON 구조

```json
{
  "nct_id": "NCT00000172",
  "inclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Probable Alzheimer's disease",
      "feature": "patient",
      "operator": "=",
      "value": "probable Alzheimer's disease",
      "unit": null,
      "confidence": 0.95
    },
    {
      "criterion_id": 2,
      "original_text": "Mini-Mental State Examination (MMSE) >= 10",
      "feature": "MMSE",
      "operator": ">=",
      "value": 10,
      "unit": null,
      "confidence": 0.9
    },
    {
      "criterion_id": 3,
      "original_text": "Mini-Mental State Examination (MMSE) <= 22",
      "feature": "MMSE",
      "operator": "<=",
      "value": 22,
      "unit": null,
      "confidence": 0.9
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": 1,
      "original_text": "Conditions that could confound diagnosis",
      "feature": "conditions",
      "operator": "=",
      "value": "could confound diagnosis",
      "unit": null,
      "confidence": 0.95
    },
    {
      "criterion_id": 2,
      "original_text": "Neurodegenerative disorders",
      "feature": "neurodegenerative disorders",
      "operator": "=",
      "value": "present",
      "unit": null,
      "confidence": 0.95
    }
  ]
}
```

### 6.2 범위 조건 분리 예시

**원본**: "MMSE score 0-26"

**전처리 결과** (두 개로 분리):

```json
[
  {
    "criterion_id": 4,
    "original_text": "MMSE score >= 0",
    "feature": "MMSE score",
    "operator": ">=",
    "value": 0,
    "unit": null,
    "confidence": 0.9
  },
  {
    "criterion_id": 5,
    "original_text": "MMSE score <= 26",
    "feature": "MMSE score",
    "operator": "<=",
    "value": 26,
    "unit": null,
    "confidence": 0.9
  }
]
```

**원본**: "Age between 55 and 90 (inclusive)"

**전처리 결과** (두 개로 분리):

```json
[
  {
    "criterion_id": 9,
    "original_text": "Age >= 55",
    "feature": "age",
    "operator": ">=",
    "value": 55,
    "unit": "years",
    "confidence": 0.9
  },
  {
    "criterion_id": 10,
    "original_text": "Age <= 90",
    "feature": "age",
    "operator": "<=",
    "value": 90,
    "unit": "years",
    "confidence": 0.9
  }
]
```

## 7. 결론

- **전처리 성공률**: 96.21% (1,270/1,320)
- **평균 Inclusion Criteria**: 10.8개
- **평균 Exclusion Criteria**: 15.6개
- 범위 조건이 올바르게 두 개의 criterion으로 분리되어 처리됨
- 주요 feature들이 일관되게 추출됨
- nct_id 복구 로직으로 파싱 실패율 감소

### 7.1 주요 성과

1. **높은 성공률**: 96.21%의 전처리 성공률 달성
2. **범위 조건 처리**: "MMSE 10-22" 같은 범위 조건이 두 개의 명확한 criterion으로 분리됨
3. **일관된 Feature 추출**: `patient`, `age`, `gender`, `MMSE` 등 주요 feature가 일관되게 추출됨
4. **표준 Operator 사용**: 모든 자연어 표현이 표준 수학 연산자(`=`, `!=`, `<`, `<=`, `>`, `>=`)로 변환됨

### 7.2 개선 필요 사항

1. **nct_id 누락 문제**: 일부 항목에서 여전히 nct_id 누락 발생 (20개, 1.52%)
2. **API 실패**: 30개 항목에서 API 호출 실패 (2.27%)
3. **Feature 통일**: "MMSE"와 "MMSE score" 같이 유사한 feature의 통일 필요
