# Inclusion/Exclusion LLM 전처리 및 Validation 종합 보고서

생성일: 2026-01-02 09:15:16

---

## 1. 전체 요약

### 1.1 전처리 요약

- **전체 레코드**: 1,429개
- **성공 (SUCCESS)**: 1,361개 (95.24%)
- **Inclusion 실패**: 0개 (0.00%)
- **Exclusion 실패**: 0개 (0.00%)
- **둘 다 실패**: 38개 (2.66%)
- **API 실패**: 30개 (2.10%)

### 1.2 Validation 요약

- **검증 완료 항목**: 1,361개
- **VERIFIED**: 1,189개 (87.36%)
- **UNCERTAIN**: 64개 (4.70%)
- **INCLUSION_FAILED**: 12개 (0.88%)
- **EXCLUSION_FAILED**: 91개 (6.69%)
- **BOTH_FAILED**: 5개 (0.37%)

- **수동 검토 필요**: 419개 (30.79%)
- **평균 일관성 점수**: 0.89

## 2. 전처리 상세 통계

### 2.1 추출 통계

- **Inclusion Criteria 추출**: 1,361개 (95.24%)
- **Exclusion Criteria 추출**: 1,361개 (95.24%)
- **완전 파싱 (둘 다)**: 1,361개 (95.24%)

### 2.2 Criteria 개수 통계

- **평균 Inclusion Criteria 개수**: 10.9개
- **평균 Exclusion Criteria 개수**: 16.3개
- **최대 Inclusion Criteria 개수**: 76개
- **최대 Exclusion Criteria 개수**: 128개
- **최소 Inclusion Criteria 개수**: 1개
- **최소 Exclusion Criteria 개수**: 1개

### 2.3 Confidence 통계


## 3. Validation 상세 통계

### 3.1 검증 상태 분포

- **VERIFIED**: 1,189개 (87.36%)
- **UNCERTAIN**: 64개 (4.70%)
- **INCLUSION_FAILED**: 12개 (0.88%)
- **EXCLUSION_FAILED**: 91개 (6.69%)
- **BOTH_FAILED**: 5개 (0.37%)

### 3.2 검증 신뢰도 통계

- **VERIFIED 평균 신뢰도**: 0.98
- **전체 평균 신뢰도**: 0.95

### 3.3 일관성 점수 통계

- **평균 일관성 점수**: 0.89
- **최소 일관성 점수**: 0.33
- **최대 일관성 점수**: 1.00

- **높은 일관성 (≥0.67)**: 1,316개 (96.69%)
- **중간 일관성 (0.33~0.67)**: 45개 (3.31%)
- **낮은 일관성 (<0.33)**: 0개 (0.00%)

### 3.4 수동 검토 현황

- **수동 검토 필요 항목**: 419개 (30.79%)
- **수동 검토 불필요 항목**: 942개 (69.21%)

### 3.5 수동 검토 불필요 vs 필요 항목 비교

#### 3.5.1 수동 검토 불필요 항목

- **전체**: 942개
- **바로 사용 가능 (VERIFIED)**: 922개 (97.88%)
- **UNCERTAIN**: 1개 (0.11%)
- **실패 항목 (사용 불가)**: 19개 (2.02%)
  - INCLUSION_FAILED: 3개
  - EXCLUSION_FAILED: 15개
  - BOTH_FAILED: 1개
- **평균 신뢰도**: 0.97
- **평균 일관성 점수**: 1.00

#### 3.5.2 수동 검토 필요 항목

- **전체**: 419개
- **VERIFIED**: 267개 (63.72%)
- **UNCERTAIN**: 63개 (15.04%)
- **INCLUSION_FAILED**: 9개 (2.15%)
- **EXCLUSION_FAILED**: 76개 (18.14%)
- **BOTH_FAILED**: 4개 (0.95%)
- **평균 신뢰도**: 0.91
- **평균 일관성 점수**: 0.64

#### 3.5.3 비교 요약

| 항목 | 수동 검토 불필요 | 수동 검토 필요 | 차이 |
| ---- | ---------------- | ------------- | ---- |
| **전체** | 942개 (69.21%) | 419개 (30.79%) | - |
| **바로 사용 가능 (VERIFIED)** | 922개 (97.88%) | 267개 (63.72%) | +34.15%p |
| **실패 항목 (사용 불가)** | 19개 (2.02%) | 89개 (21.24%) | - |
| **평균 신뢰도** | 0.97 | 0.91 | +0.06 |
| **평균 일관성** | 1.00 | 0.64 | +0.36 |


### 3.6 검증 이력 통계

- **검증된 Study 수**: 1,361개
- **총 검증 실행 횟수**: 4,083회
- **평균 검증 신뢰도**: 0.95
- **검증 노트 있는 항목**: 4,057개

## 4. 주요 Feature 분포 (상위 20개)

| 순위 | Feature | 사용 횟수 |
| ---- | ------- | --------- |
| 1 | patient | 6,529 |
| 2 | age | 1,480 |
| 3 | gender | 687 |
| 4 | MMSE score | 553 |
| 5 | MMSE | 506 |
| 6 | subject | 475 |
| 7 | BMI | 434 |
| 8 | diagnosis | 428 |
| 9 | caregiver | 308 |
| 10 | medication | 278 |
| 11 | informed consent | 194 |
| 12 | study partner | 152 |
| 13 | female patient | 130 |
| 14 | body weight | 111 |
| 15 | ALT | 111 |
| 16 | AST | 105 |
| 17 | systolic blood pressure | 99 |
| 18 | participant | 98 |
| 19 | CDR | 97 |
| 20 | medical condition | 90 |

## 5. 전처리 결과 예시

### 5.1 성공 샘플 #1

**NCT ID**: `NCT00000171`

**원본 Eligibility Criteria** (일부):

```
Inclusion Criteria:

* Patients must meet NINCDS-ADRDA criteria for probable Alzheimer's disease (AD). Patients must have disrupted sleep, documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors.
* A diagnosis of probable AD.
* MMSE score 0-26.
* Hachinski Ischemia Scale score less than or equal to 4.
* A 2-week history of two or more sleep disorder behaviors, occurring at least once weekly, as reported by the caregiver on the Sleep Disorder Inventory.
* CT ...
```

**Inclusion Criteria 개수**: 17개
**Exclusion Criteria 개수**: 15개
**Validation Status**: VERIFIED
**Validation Confidence**: 0.98
**Consistency Score**: 1.00

**Inclusion Criteria 예시** (처음 5개):

**1.** Feature: `patient`, Operator: `=`, Value: `NINCDS-ADRDA criteria for probable Alzheimer's disease (AD)`, Confidence: `0.95`

**2.** Feature: `patient`, Operator: `=`, Value: `disrupted sleep documented by clinical history and by 1 to 2 weeks of recording using wrist activity monitors`, Confidence: `0.95`

**3.** Feature: `patient`, Operator: `=`, Value: `diagnosis of probable AD`, Confidence: `0.95`

**4.** Feature: `MMSE score`, Operator: `>=`, Value: `0`, Confidence: `0.9`

**5.** Feature: `MMSE score`, Operator: `<=`, Value: `26`, Confidence: `0.9`


*... 외 12개 항목*

---

### 5.2 성공 샘플 #2

**NCT ID**: `NCT00000172`

**원본 Eligibility Criteria** (일부):

```
Inclusion Criteria:

* Probable Alzheimer's disease
* Mini-Mental State Examination (MMSE) 10-22 and ADAS greater than or equal to 18
* Alzheimer's Disease Assessment Scale cognitive portion (ADAS-cog-11) score of at least 18
* Opportunity for Activities of Daily Living
* Caregiver
* Subjects who live with or have regular daily visits from a responsible caregiver (visit frequency: preferably daily but at least 5 days/week). This includes a friend or relative or paid personnel. The caregiver shou...
```

**Inclusion Criteria 개수**: 8개
**Exclusion Criteria 개수**: 13개
**Validation Status**: VERIFIED
**Validation Confidence**: 0.98
**Consistency Score**: 1.00

**Inclusion Criteria 예시** (처음 5개):

**1.** Feature: `patient`, Operator: `=`, Value: `probable Alzheimer's disease`, Confidence: `0.95`

**2.** Feature: `MMSE`, Operator: `>=`, Value: `10`, Confidence: `0.9`

**3.** Feature: `MMSE`, Operator: `<=`, Value: `22`, Confidence: `0.9`

**4.** Feature: `ADAS`, Operator: `>=`, Value: `18`, Confidence: `0.9`

**5.** Feature: `ADAS-cog-11 score`, Operator: `>=`, Value: `18`, Confidence: `0.95`


*... 외 3개 항목*

---

### 5.3 성공 샘플 #3

**NCT ID**: `NCT00000173`

**원본 Eligibility Criteria** (일부):

```
Inclusion Criteria:

* Memory complaints and memory difficulties which are verified by an informant.
* Abnormal memory function documented by scoring below the education adjusted cutoff on the Logical Memory II subscale (Delayed Paragraph Recall) from the Wechsler Memory Scale - Revised (the maximum score is 25): a) less than or equal to 8 for 16 or more years of education, b) less than or equal to 4 for 8-15 years of education, c) less than or equal to 2 for 0-7 years of education.
* Mini-Menta...
```

**Inclusion Criteria 개수**: 23개
**Exclusion Criteria 개수**: 30개
**Validation Status**: VERIFIED
**Validation Confidence**: 0.97
**Consistency Score**: 1.00

**Inclusion Criteria 예시** (처음 5개):

**1.** Feature: `memory complaints and difficulties`, Operator: `=`, Value: `verified by an informant`, Confidence: `0.95`

**2.** Feature: `Logical Memory II subscale score`, Operator: `=`, Value: `below education adjusted cutoff (<=8 for >=16 yrs education, <=4 for 8-15 yrs education, <=2 for 0-7 yrs education)`, Confidence: `0.95`

**3.** Feature: `Mini-Mental Exam score`, Operator: `>=`, Value: `24`, Confidence: `0.9`

**4.** Feature: `Mini-Mental Exam score`, Operator: `<=`, Value: `30`, Confidence: `0.9`

**5.** Feature: `Clinical Dementia Rating`, Operator: `=`, Value: `0.5`, Confidence: `0.9`


*... 외 18개 항목*

---

## 6. 결론

### 6.1 전처리 성과

- 전처리 성공률: **95.24%** (1,361/1,429)
- Inclusion/Exclusion 모두 추출 성공률: **95.24%**

### 6.2 Validation 성과

- 검증 완료율: **1,361개** 항목 검증 완료
- VERIFIED 비율: **87.36%** (1,189/1,361)
- 수동 검토 필요 비율: **30.79%**

---

*보고서 생성일시: 2026-01-02 09:15:16*
