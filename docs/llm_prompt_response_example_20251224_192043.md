# LLM 전처리 프롬프트 및 응답 예시

생성일시: 2025-12-24 19:20:43

## 1. 입력 데이터

```json
{
  "id": 1,
  "measure_raw": "Alzheimer's Disease Assessment Scale-Cognitive Subscale (ADAS-Cog)",
  "description_raw": "Change from baseline in ADAS-Cog score",
  "time_frame_raw": "Baseline, Week 12, Week 24, Week 36"
}
```

## 2. 프롬프트

```
다음 outcome 데이터를 파싱하여 measure_code와 time 정보를 추출하세요.

데이터 형식: [outcome_id]|M:[measure_raw]|D:[description_raw]|T:[time_frame_raw]

1|M:Alzheimer's Disease Assessment Scale-Cognitive Subscale (ADAS-Cog)|D:Change from baseline in ADAS-Cog score|T:Baseline, Week 12, Week 24, Week 36

규칙:

## 1. measure_code 추출
measure_raw와 description_raw에서 표준 measure_code를 추출합니다.
다음 measure_code 목록을 참고하세요 (dic.csv 기반):

- ADAS_COG (약어: ADAS-Cog)
- CDR_SB (약어: CDR-SB)
- MMSE (약어: MMSE)
- MOCA (약어: MoCA)
- PACC (약어: PACC)
- RBANS (약어: RBANS)
- NTB (약어: NTB)
- WAIS (약어: WAIS)
- ADAS_EXEC (약어: ADAS-Exec)
- ADCS_ADL (약어: ADCS-ADL)
- ADL (약어: ADL)
- IADL (약어: IADL)
- FAQ (약어: FAQ)
- DAD (약어: DAD)
- BADLS (약어: BADLS)
- CIBIC_PLUS (약어: CIBIC+)
- CGIC (약어: CGIC)
- CDR_GLOBAL (약어: CDR)
- GDS (약어: GDS)
- NPI (약어: NPI)
- NPI_Q (약어: NPI-Q)
- BEHAVE_AD (약어: BEHAVE-AD)
- CMAI (약어: CMAI)
- HAMD (약어: HAM-D)
- HADS (약어: HADS)
- AES (약어: AES)
- AMYLOID_PET (약어: Amyloid PET)
- TAU_PET (약어: Tau PET)
- FDG_PET (약어: FDG-PET)
- CSF_ABETA (약어: CSF Aβ)
- ... 외 93개 더

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
- time_points: 모든 시점을 JSON 배열로 추출 [{"value": 숫자, "unit": "단위"}, ...]

예시:
- "Week 1, Week 14, Week 26" →
  time_value: 26, time_unit: "weeks",
  time_points: [{"value": 1, "unit": "weeks"}, {"value": 14, "unit": "weeks"}, {"value": 26, "unit": "weeks"}]
- "Days 1 and 14" →
  time_value: 14, time_unit: "days",
  time_points: [{"value": 1, "unit": "days"}, {"value": 14, "unit": "days"}]
- "6 weeks, 12 weeks, 24 weeks" →
  time_value: 24, time_unit: "weeks",
  time_points: [{"value": 6, "unit": "weeks"}, {"value": 12, "unit": "weeks"}, {"value": 24, "unit": "weeks"}]
- "1주차, 2주차, 3주차" (한글) →
  time_value: 3, time_unit: "weeks",
  time_points: [{"value": 1, "unit": "weeks"}, {"value": 2, "unit": "weeks"}, {"value": 3, "unit": "weeks"}]

## 3. 기타 규칙
- 단위가 생략된 경우("1 day and 4") → 첫 번째 숫자의 단위를 두 번째 숫자에도 적용
- "Up to N days/weeks" 패턴은 N을 time_value로 사용 (최대값)
- 확실하지 않으면 null 반환

**중요: 반드시 JSON 배열만 반환하세요. 코드나 설명 없이 순수 JSON만 반환합니다.**

응답 형식 (JSON 배열):
[
  {
    "outcome_id": 123,
    "measure_code": "ADAS_COG",
    "time_value": 12,
    "time_unit": "weeks",
    "time_points": null,
    "confidence": 0.95,
    "notes": "Week 12에서 측정"
  },
  {
    "outcome_id": 456,
    "measure_code": "MMSE",
    "time_value": 26,
    "time_unit": "weeks",
    "time_points": [
      {"value": 1, "unit": "weeks"},
      {"value": 14, "unit": "weeks"},
      {"value": 26, "unit": "weeks"}
    ],
    "confidence": 0.9,
    "notes": "Week 1, 14, 26에서 측정"
  }
]

**반드시 위 형식의 JSON 배열만 반환하세요. 코드나 설명 텍스트는 포함하지 마세요.**
```

## 3. LLM 응답

```json
[
  {
    "outcome_id": 1,
    "measure_code": "ADAS_COG",
    "time_value": 36,
    "time_unit": "weeks",
    "time_points": [
      {
        "value": 12,
        "unit": "weeks"
      },
      {
        "value": 24,
        "unit": "weeks"
      },
      {
        "value": 36,
        "unit": "weeks"
      }
    ],
    "confidence": 0.95,
    "notes": "ADAS_COG 측정값이 Week 12, Week 24, Week 36에서 확인됨."
  }
]
```

````

## 4. 파싱된 응답

```json
[
  {
    "outcome_id": 1,
    "measure_code": "ADAS_COG",
    "time_value": 36,
    "time_unit": "weeks",
    "time_points": [
      {
        "value": 12,
        "unit": "weeks"
      },
      {
        "value": 24,
        "unit": "weeks"
      },
      {
        "value": 36,
        "unit": "weeks"
      }
    ],
    "confidence": 0.95,
    "notes": "ADAS_COG 측정값이 Week 12, Week 24, Week 36에서 확인됨."
  }
]
````

## 5. 추출된 정보

| 항목         | 값                                                                                               |
| ------------ | ------------------------------------------------------------------------------------------------ |
| outcome_id   | 1                                                                                                |
| measure_code | ADAS_COG                                                                                         |
| time_value   | 36                                                                                               |
| time_unit    | weeks                                                                                            |
| time_points  | [{"value": 12, "unit": "weeks"}, {"value": 24, "unit": "weeks"}, {"value": 36, "unit": "weeks"}] |
| confidence   | 0.95                                                                                             |
| notes        | ADAS_COG 측정값이 Week 12, Week 24, Week 36에서 확인됨.                                          |
