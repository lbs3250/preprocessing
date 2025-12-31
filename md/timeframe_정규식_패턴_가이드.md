# Timeframe 정규식 패턴 가이드

이 문서는 ClinicalTrials.gov outcomes 데이터의 timeframe 필드를 정규화하기 위해 사용되는 정규식 패턴들을 상세히 설명합니다.

## 목차
1. [단위 줄임말 처리](#단위-줄임말-처리)
2. [대소문자 처리](#대소문자-처리)
3. [연결어 처리 (and, or, -)](#연결어-처리-and-or--)
4. [숫자와 단위 순서](#숫자와-단위-순서)
5. [복수형 처리](#복수형-처리)
6. [하이픈 포함 패턴](#하이픈-포함-패턴)
7. [서수 패턴](#서수-패턴)
8. [텍스트 숫자](#텍스트-숫자)
9. [복수 시점 처리](#복수-시점-처리)
10. [범위 패턴](#범위-패턴)
11. [특수 패턴](#특수-패턴)

---

## 단위 줄임말 처리

### 지원하는 단위 및 줄임말

| 정규화된 단위 | 지원하는 입력 형태 | 정규식 패턴 |
|--------------|-------------------|------------|
| `week` | `week`, `weeks`, `wk`, `w` | `(week\|weeks\|wk\|w)` |
| `hour` | `hour`, `hours`, `hr`, `hrs`, `h` | `(hour\|hours\|hr\|hrs\|h)` |
| `minute` | `minute`, `minutes`, `min`, `mins` | `(minute\|minutes\|min\|mins)` |
| `day` | `day`, `days`, `d` | `(day\|days\|d)` |
| `month` | `month`, `months` | `(month\|months)` |
| `year` | `year`, `years` | `(year\|years)` |

### 정규화 함수

```python
def normalize_unit(unit_str: str) -> str:
    """단위 문자열을 정규화된 형태로 변환"""
    unit_norm = unit_str.lower().rstrip('s')  # 소문자 변환 후 복수형 's' 제거
    if unit_norm in ('h', 'hr', 'hrs'):
        return 'hour'
    elif unit_norm in ('min', 'mins', 'minute', 'minutes'):
        return 'minute'
    elif unit_norm in ('wk', 'w'):
        return 'week'
    return unit_norm
```

### 예시

**예시 1: 다양한 줄임말 처리**
```
입력: "48 hr"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(hour|hours|hr|hrs|h)\b'
매칭: "48 hr" → value: 48, unit: "hour"
```

```
입력: "30 min"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(minute|minutes|min|mins)\b'
매칭: "30 min" → value: 30, unit: "minute"
```

```
입력: "Wk 50"
정규식: r'\b(wk|w)\s+(\d+(?:\.\d+)?)\b'
매칭: "Wk 50" → value: 50, unit: "week"
```

---

## 대소문자 처리

모든 정규식 패턴은 `re.IGNORECASE` 플래그를 사용하여 대소문자를 구분하지 않습니다.

### 정규식 사용법

```python
pattern = re.compile(r'\b(week|weeks)\s+\d+', re.IGNORECASE)
```

### 예시

**예시 2: 대소문자 혼용 처리**
```
입력: "Week 12", "WEEK 12", "week 12", "WeEk 12"
정규식: r'\b(week|weeks)\s+\d+'
모든 경우 매칭: value: 12, unit: "week"
```

```
입력: "At Day 1", "at day 1", "AT DAY 1"
정규식: r'\bat\s+(day|days)\s+\d+'
모든 경우 매칭: value: 1, unit: "day"
```

---

## 연결어 처리 (and, or, -)

### AND 연결

#### 패턴 1: "N and M unit" 형태
```
정규식: r'\b(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s+(week|weeks|day|days|...)\b'
```

**예시 3: AND로 연결된 복수 시점**
```
입력: "12 and 24 weeks"
정규식: r'\b(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s+(week|weeks)\b'
매칭: 
  - 첫 번째: value: 12, unit: "week"
  - 두 번째: value: 24, unit: "week"
결과: time_points: [{"value": 12, "unit": "week"}, {"value": 24, "unit": "week"}]
```

#### 패턴 2: "Unit N, M, O and P" 형태
```
정규식: r'\b(week|weeks|day|days|...)\s+\d+(?:\s*\([^)]*\))?(?:\s*,\s*\d+(?:\s*\([^)]*\))?)*(?:\s*,\s*)?\s+and\s+\d+'
```

**예시 4: 쉼표와 AND로 연결된 복수 시점**
```
입력: "Days 84, 169, 253, 421, 505, 589, and 757"
정규식: r'\b(day|days)\s+\d+(?:\s*\([^)]*\))?(?:\s*,\s*\d+(?:\s*\([^)]*\))?)*(?:\s*,\s*)?\s+and\s+\d+'
매칭: 
  - 모든 숫자 추출: [84, 169, 253, 421, 505, 589, 757]
결과: time_points: [
  {"value": 84, "unit": "day"},
  {"value": 169, "unit": "day"},
  {"value": 253, "unit": "day"},
  {"value": 421, "unit": "day"},
  {"value": 505, "unit": "day"},
  {"value": 589, "unit": "day"},
  {"value": 757, "unit": "day"}
]
```

### 하이픈(-) 범위 패턴

#### 패턴 1: "N-M unit" 형태
```
정규식: r'\b(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s+(week|weeks|day|days|...)\b'
```

**예시 5: 하이픈으로 연결된 범위**
```
입력: "60-90 minutes"
정규식: r'\b(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s+(minute|minutes|min|mins)\b'
매칭: 
  - num1: 60, num2: 90, unit: "minute"
결과: time_value_main: 90 (최대값), unit: "minute"
```

#### 패턴 2: "Unit N-M" 형태
```
정규식: r'\b(week|weeks|day|days|...)\s+(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)'
```

**예시 6: 단위가 앞에 오는 범위**
```
입력: "Day 15-19"
정규식: r'\b(day|days)\s+(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)'
매칭: 
  - unit: "day", num1: 15, num2: 19
결과: time_value_main: 19 (최대값), unit: "day"
```

---

## 숫자와 단위 순서

### 패턴 1: 숫자 먼저 (가장 일반적)

```
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes|wk|w)\b'
```

**예시 7: 숫자 먼저 패턴**
```
입력: "26 weeks"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(week|weeks)\b'
매칭: num_str="26", unit_str="weeks"
결과: value: 26, unit: "week"
```

```
입력: "48 hr"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(hour|hours|hr|hrs|h)\b'
매칭: num_str="48", unit_str="hr"
결과: value: 48, unit: "hour"
```

```
입력: "30 minutes"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(minute|minutes|min|mins)\b'
매칭: num_str="30", unit_str="minutes"
결과: value: 30, unit: "minute"
```

### 패턴 2: 단위 먼저

```
정규식: r'\b(week|weeks|day|days|month|months|year|years|hour|hours|hr|hrs|min|mins|minute|minutes|wk|w)\s*-?\s*(\d+(?:\.\d+)?)(?:th|st|nd|rd)?\b'
```

**예시 8: 단위 먼저 패턴**
```
입력: "Week 24"
정규식: r'\b(week|weeks)\s*-?\s*(\d+(?:\.\d+)?)\b'
매칭: unit_str="Week", num_str="24"
결과: value: 24, unit: "week"
```

```
입력: "Day 14"
정규식: r'\b(day|days)\s*-?\s*(\d+(?:\.\d+)?)\b'
매칭: unit_str="Day", num_str="14"
결과: value: 14, unit: "day"
```

```
입력: "Wk 50"
정규식: r'\b(wk|w)\s+(\d+(?:\.\d+)?)\b'
매칭: unit_str="Wk", num_str="50"
결과: value: 50, unit: "week"
```

---

## 복수형 처리

모든 단위는 복수형(`s` 접미사)을 지원하며, 정규화 시 자동으로 제거됩니다.

### 정규식 패턴

```python
# 복수형 포함 패턴
pattern = re.compile(r'\b(week|weeks|day|days|month|months|year|years|hour|hours|min|mins|minute|minutes)\s+\d+', re.IGNORECASE)

# 정규화 함수
unit_norm = unit_str.lower().rstrip('s')  # 's' 제거
```

### 예시

**예시 9: 복수형 처리**
```
입력: "26 weeks"
정규식: r'\b(\d+(?:\.\d+)?)\s*(week|weeks)\b'
매칭: unit_str="weeks"
정규화: "weeks".lower().rstrip('s') → "week"
결과: value: 26, unit: "week"
```

```
입력: "1 year"
정규식: r'\b(\d+(?:\.\d+)?)\s*(year|years)\b'
매칭: unit_str="year"
정규화: "year".lower().rstrip('s') → "year"
결과: value: 1, unit: "year"
```

```
입력: "30 minutes"
정규식: r'\b(\d+(?:\.\d+)?)\s*(minute|minutes|min|mins)\b'
매칭: unit_str="minutes"
정규화: "minutes".lower().rstrip('s') → "minute"
결과: value: 30, unit: "minute"
```

---

## 하이픈 포함 패턴

하이픈이 포함된 패턴도 지원합니다 (예: "8-weeks", "96-week").

### 정규식 패턴

```
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(week|weeks|day|days|...)\b'
또는
정규식: r'\b(week|weeks|day|days|...)\s*-?\s*(\d+(?:\.\d+)?)\b'
```

`\s*-?\s*` 부분이 하이픈을 선택적으로 매칭합니다.

### 예시

**예시 10: 하이픈 포함 패턴**
```
입력: "96-week"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(week|weeks)\b'
매칭: num_str="96", unit_str="week"
결과: value: 96, unit: "week"
```

```
입력: "21-months"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(month|months)\b'
매칭: num_str="21", unit_str="months"
정규화: "months".lower().rstrip('s') → "month"
결과: value: 21, unit: "month"
```

```
입력: "8-weeks"
정규식: r'\b(\d+(?:\.\d+)?)\s*-?\s*(week|weeks)\b'
매칭: num_str="8", unit_str="weeks"
정규화: "weeks".lower().rstrip('s') → "week"
결과: value: 8, unit: "week"
```

---

## 서수 패턴

서수 접미사(`th`, `st`, `nd`, `rd`)를 포함한 패턴도 지원합니다.

### 정규식 패턴

```
정규식: r'\b(\d+(?:\.\d+)?)(?:th|st|nd|rd)\s+(month|months|week|weeks|...)\b'
또는
정규식: r'\b(week|weeks|day|days|...)\s*-?\s*(\d+(?:\.\d+)?)(?:th|st|nd|rd)?\b'
```

### 예시

**예시 11: 서수 패턴**
```
입력: "6th month"
정규식: r'\b(\d+(?:\.\d+)?)(?:th|st|nd|rd)\s+(month|months)\b'
매칭: num_str="6", unit_str="month"
결과: value: 6, unit: "month"
```

```
입력: "1st week"
정규식: r'\b(\d+(?:\.\d+)?)(?:th|st|nd|rd)\s+(week|weeks)\b'
매칭: num_str="1", unit_str="week"
결과: value: 1, unit: "week"
```

---

## 텍스트 숫자

영어 텍스트로 표현된 숫자도 지원합니다.

### 지원하는 텍스트 숫자

- `one`, `two`, `three`, `four`, `five`, `six`, `seven`, `eight`, `nine`, `ten`
- `eleven`, `twelve`, `thirteen`, `fourteen`, `fifteen`, `sixteen`, `seventeen`, `eighteen`, `nineteen`
- `twenty`, `thirty`, `forty`, `fifty`, `sixty`, `seventy`, `eighty`, `ninety`, `hundred`

### 정규식 패턴

```
정규식: r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s+(week|weeks|day|days|month|months|year|years|hour|hours|min|mins|minute|minutes)\b'
```

### 예시

**예시 12: 텍스트 숫자 패턴**
```
입력: "Two years"
정규식: r'\b(two)\s+(year|years)\b'
매칭: text_num="two", unit_str="years"
변환: "two" → 2
결과: value: 2, unit: "year"
```

```
입력: "eight weeks"
정규식: r'\b(eight)\s+(week|weeks)\b'
매칭: text_num="eight", unit_str="weeks"
변환: "eight" → 8
결과: value: 8, unit: "week"
```

```
입력: "thirty minutes"
정규식: r'\b(thirty)\s+(minute|minutes|min|mins)\b'
매칭: text_num="thirty", unit_str="minutes"
변환: "thirty" → 30
결과: value: 30, unit: "minute"
```

---

## 복수 시점 처리

쉼표(`,`)와 `and`로 연결된 여러 시점을 처리합니다.

### 패턴 1: 쉼표로 구분된 시점

```
정규식: r'\b(week|weeks|day|days|...)\s+\d+(?:\s*\([^)]*\))?(?:\s*,\s*\d+(?:\s*\([^)]*\))?)+'
```

**예시 13: 쉼표로 구분된 복수 시점**
```
입력: "weeks 9, 17, 25 and 37"
정규식: r'\b(week|weeks)\s+\d+(?:\s*\([^)]*\))?(?:\s*,\s*\d+(?:\s*\([^)]*\))?)*(?:\s*,\s*)?\s+and\s+\d+'
매칭: 
  - 단위: "weeks"
  - 숫자 추출: [9, 17, 25, 37]
결과: time_points: [
  {"value": 9, "unit": "week"},
  {"value": 17, "unit": "week"},
  {"value": 25, "unit": "week"},
  {"value": 37, "unit": "week"}
]
time_value_main: 37 (최대값)
```

### 패턴 2: 쉼표와 AND로 구분된 시점

```
입력: "baseline, 5, 30, 60, and 180 min"
정규식: 
  - baseline 체크: r'\bbaseline\b' → change_from_baseline_flag = TRUE
  - 단위 추출: r'\b(\d+(?:\.\d+)?)\s+(min|mins|minute|minutes)\b' → "min"
  - 숫자 추출: [5, 30, 60, 180]
결과: 
  change_from_baseline_flag: TRUE
  time_points: [
    {"value": 0, "unit": "day"},  # baseline
    {"value": 5, "unit": "minute"},
    {"value": 30, "unit": "minute"},
    {"value": 60, "unit": "minute"},
    {"value": 180, "unit": "minute"}
  ]
  time_value_main: 180 (최대값, hour로 변환하여 비교)
```

---

## 범위 패턴

하이픈(`-`)으로 연결된 범위는 최대값만 추출합니다.

### 패턴 1: "N-M unit" 형태

```
정규식: r'\b(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s+(week|weeks|day|days|...)\b'
```

**예시 14: 범위 패턴 (숫자-숫자 단위)**
```
입력: "60-90 minutes"
정규식: r'\b(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s+(minute|minutes|min|mins)\b'
매칭: num1_str="60", num2_str="90", unit_str="minutes"
결과: 
  - num1: 60, num2: 90
  - max_value: 90
  - time_value_main: 90, unit: "minute"
```

### 패턴 2: "Unit N-M" 형태

```
정규식: r'\b(week|weeks|day|days|...)\s+(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)'
```

**예시 15: 범위 패턴 (단위 숫자-숫자)**
```
입력: "Day 15-19"
정규식: r'\b(day|days)\s+(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)'
매칭: unit_str="Day", num1_str="15", num2_str="19"
결과: 
  - num1: 15, num2: 19
  - max_value: 19
  - time_value_main: 19, unit: "day"
```

---

## 특수 패턴

### 1. "At Day/Week/Month N" 패턴

```
정규식: r'\bat\s+(day|days|week|weeks|month|months|hour|hours|min|mins|minute|minutes)\s+(\d+(?:\.\d+)?)'
```

**예시 16: At 패턴**
```
입력: "At Day 1"
정규식: r'\bat\s+(day|days)\s+(\d+(?:\.\d+)?)'
매칭: unit_word="day", value_str="1"
결과: value: 1, unit: "day"
```

```
입력: "At Week 14"
정규식: r'\bat\s+(week|weeks)\s+(\d+(?:\.\d+)?)'
매칭: unit_word="week", value_str="14"
결과: value: 14, unit: "week"
```

### 2. "For N Months/Weeks/Days" 패턴

```
정규식: r'\bfor\s+(\d+(?:\.\d+)?)\s+(month|months|week|weeks|day|days|hour|hours|min|mins|minute|minutes)'
```

**예시 17: For 패턴**
```
입력: "For 10 Months"
정규식: r'\bfor\s+(\d+(?:\.\d+)?)\s+(month|months)'
매칭: value_str="10", unit_word="Months"
결과: value: 10, unit: "month"
```

### 3. "Year N" 패턴

```
정규식: r'year\s*(\d+(?:\.\d+)?)'
```

**예시 18: Year 패턴**
```
입력: "Year 3.5"
정규식: r'year\s*(\d+(?:\.\d+)?)'
매칭: year_value_str="3.5"
결과: value: 3.5, unit: "year"
```

### 4. "Up to N" 패턴

```
정규식: r'up\s*to\s+(\d+(?:\.\d+)?)\s*(week|weeks|month|months|year|years|day|days|hour|hours)'
```

**예시 19: Up to 패턴**
```
입력: "up to 72 hours"
정규식: r'up\s*to\s+(\d+(?:\.\d+)?)\s*(week|weeks|month|months|year|years|day|days|hour|hours)'
매칭: value_str="72", unit_word="hours"
결과: value: 72, unit: "hour"
```

### 5. Baseline 패턴

```
정규식: r'\bbaseline\b'
```

**예시 20: Baseline 패턴**
```
입력: "Baseline"
정규식: r'\bbaseline\b'
매칭: baseline 발견
결과: 
  change_from_baseline_flag: TRUE
  time_value_main: 0, unit: "day" (baseline만 있는 경우)
```

```
입력: "Baseline, Week 16"
정규식: 
  - baseline: r'\bbaseline\b' → change_from_baseline_flag = TRUE
  - week: r'\b(week|weeks)\s+\d+' → value: 16, unit: "week"
결과: 
  change_from_baseline_flag: TRUE
  time_value_main: 16, unit: "week"
```

---

## 패턴 우선순위

패턴은 다음 순서로 체크됩니다:

1. **Baseline 패턴** (최우선)
2. **"At Day/Week/Month N" 패턴**
3. **"Day N", "Month N", "Week N" 단독 패턴**
4. **"For N Months/Weeks/Days" 패턴**
5. **텍스트 숫자 패턴**
6. **숫자+단위 패턴** (가장 일반적)
7. **Year N 패턴**
8. **"Up to N" 패턴**
9. **"Through study completion" 패턴**

---

## 주의사항

### 1. 약물 코드 제외

약물 코드 패턴 (예: "PF-04447943", "MK-8931")은 시간 단위로 인식하지 않습니다.

```
정규식 체크: r'[A-Z]{2,3}-\d+'
```

### 2. Dose 용량 제외

숫자 뒤에 dose 단위 (mg, g, ml, kg 등)가 오는 경우는 제외합니다.

```
정규식 체크: r'\s*(mg|g|ml|kg|mcg|μg|µg|iu|units?)\b'
```

### 3. 년도 범위 제외

"year 2006-2008" 같은 년도 범위는 실패 처리합니다.

```
조건: unit == 'year' AND (num1 >= 1900 OR num2 >= 1900)
```

---

## 정규식 패턴 요약

### 주요 정규식 패턴 목록

1. **단위 줄임말**: `(week|weeks|wk|w|hour|hours|hr|hrs|h|minute|minutes|min|mins|day|days|d|month|months|year|years)`

2. **대소문자 무시**: `re.IGNORECASE` 플래그 사용

3. **숫자 패턴**: `\d+(?:\.\d+)?` (정수 또는 소수)

4. **하이픈 포함**: `\s*-?\s*` (선택적 하이픈)

5. **복수형**: `(?:s)?` 또는 정규화 함수에서 `rstrip('s')`

6. **서수**: `(?:th|st|nd|rd)?`

7. **AND 연결**: `\s+and\s+`

8. **범위**: `\s*-\s*`

9. **텍스트 숫자**: `(one|two|three|...|hundred)`

---

## 참고

- 모든 패턴은 `normalization_patterns.py`와 `normalize_phase1.py`에 구현되어 있습니다.
- 패턴 매칭은 우선순위에 따라 순차적으로 수행됩니다.
- 복수 시점이 감지되면 `time_points` JSONB 배열에 모든 시점이 저장됩니다.
- 단일 시점인 경우 `time_value_main`과 `time_unit_main`만 저장됩니다.

