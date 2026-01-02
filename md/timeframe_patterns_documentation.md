# Timeframe 정규화 패턴 문서

이 문서는 ClinicalTrials.gov 데이터의 timeframe 정규화에 사용되는 정규식 패턴들을 설명합니다.

각 패턴은 우선순위에 따라 순차적으로 매칭되며, 매칭된 패턴 코드가 데이터베이스에 저장됩니다.

---

## 패턴 목록

### PATTERN1: Baseline 패턴

**정규식:**
```regex
\bbaseline\b
```

**설명:**
- Baseline 키워드가 포함된 timeframe을 감지합니다.
- `change_from_baseline_flag`가 `TRUE`로 설정됩니다.
- Baseline만 있고 숫자나 단위가 없는 경우 → 0 day로 처리됩니다.

**예제:**
- `"baseline"`
- `"Baseline"`
- `"These measurements will be taken at baseline"`
- `"baseline, 5, 30, 60, and 180 min"`

**우선순위:** 최우선 (1순위)

---

### PATTERN2: "At Day/Week/Month N" 패턴

**정규식:**
```regex
\bat\s+(day|days|week|weeks|month|months)\s+\d+
```

**설명:**
- "At Day N", "At Week N", "At Month N" 형식을 감지합니다.
- 단일 시점만 추출합니다.

**예제:**
- `"At Day 7"`
- `"At Week 12"`
- `"At Month 6"`
- `"at week 24"`

**우선순위:** 2순위

---

### PATTERN3: "Day N", "Month N", "Week N" 단독 패턴

**정규식:**
```regex
\b(day|days|month|months|week|weeks)\s+\d+
```

**설명:**
- 단위와 숫자가 함께 나타나는 단독 패턴을 감지합니다.
- 하이픈 포함, 서수 포함, wk/W 단위도 처리합니다.

**예제:**
- `"Day 14"`
- `"Week 24"`
- `"Month 6"`
- `"Wk 50"`
- `"W24"`
- `"6th month"`
- `"8-weeks"`
- `"30 minutes"`

**우선순위:** 3순위

---

### PATTERN4: "Day N to Day M", "Day N through M" 패턴

**정규식:**
```regex
\bday\s+\d+\s+to\s+day\s+\d+
\bday\s+\d+\s+through\s+\d+
```

**설명:**
- 범위를 나타내는 패턴을 감지합니다.
- "Day N to Day M" 또는 "Day N through M" 형식입니다.

**예제:**
- `"Day 1 to Day 7"`
- `"Day 14 through 28"`
- `"day 1 to day 14"`

**우선순위:** 4순위

---

### PATTERN5: "For N Months/Weeks/Days/Minutes" 패턴

**정규식:**
```regex
\bfor\s+\d+\s+(month|months|week|weeks|day|days|hour|hours|min|mins|minute|minutes)
```

**설명:**
- "For N [단위]" 형식을 감지합니다.
- 기간을 나타내는 패턴입니다.

**예제:**
- `"For 12 weeks"`
- `"For 6 months"`
- `"For 30 minutes"`
- `"for 2 days"`

**우선순위:** 5순위

---

### PATTERN6: "At Months N and M" 패턴

**정규식:**
```regex
\bat\s+months?\s+\d+\s+and\s+\d+
```

**설명:**
- "At Months N and M" 형식을 감지합니다.
- 복수 시점을 나타내는 패턴입니다.

**예제:**
- `"At Months 3 and 6"`
- `"At Month 12 and 24"`
- `"at months 6 and 12"`

**우선순위:** 6순위

---

### PATTERN7: Year 패턴

**정규식:**
```regex
year\s*\d+
```

**설명:**
- "Year N" 형식을 감지합니다.
- 년도 범위 패턴("year 2006-2008")은 실패 처리됩니다.

**예제:**
- `"Year 1"`
- `"year 2"`
- `"Year 3"`

**우선순위:** 7순위

---

### PATTERN8: "Up to Day/Week/Month N" 패턴 (단위 포함)

**정규식:**
```regex
up\s*to\s+(day|days|week|weeks|month|months|year|years)\s+\d+
```

**설명:**
- "Up to [단위] N" 형식을 감지합니다.
- 단위가 명시적으로 포함된 패턴입니다.

**예제:**
- `"Up to Week 12"`
- `"Up to Day 30"`
- `"up to month 6"`

**우선순위:** 8순위

---

### PATTERN9: "Up to N" 패턴

**정규식:**
```regex
up\s*to\s+\d+
```

**설명:**
- "Up to N" 형식을 감지합니다.
- 단위가 없는 경우입니다.

**예제:**
- `"Up to 12"`
- `"up to 24"`
- `"Upto 6"` (띄어쓰기 없음 지원)

**우선순위:** 9순위

---

### PATTERN10: 복수 시점 패턴

**정규식:**
```regex
(week|weeks|day|days|month|months)\s+\d+.*?,\s*(week|weeks|day|days|month|months)\s+\d+
```

**설명:**
- 복수 시점을 나타내는 패턴을 감지합니다.
- 쉼표로 구분된 여러 시점을 처리합니다.

**예제:**
- `"Week 1, Week 14"`
- `"Day 7, Day 14, Day 21"`
- `"Month 3, Month 6, Month 12"`

**우선순위:** 10순위

---

### PATTERN11: Through 패턴

**정규식:**
```regex
through\s+(study|completion|end)
```

**설명:**
- "Through study", "Through completion", "Through end" 형식을 감지합니다.

**예제:**
- `"Through study completion"`
- `"through end"`
- `"Through completion"`

**우선순위:** 11순위

---

### PATTERN12: 텍스트 숫자 패턴

**정규식:**
```regex
\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s+(week|weeks|month|months|year|years|day|days|hour|hours|min|mins|minute|minutes)\b
```

**설명:**
- 텍스트로 표현된 숫자를 감지합니다.
- "Two years", "eight weeks", "thirty minutes" 등이 해당됩니다.

**예제:**
- `"Two years"`
- `"Eight weeks"`
- `"Thirty minutes"`
- `"Twelve months"`

**우선순위:** 12순위

---

### PATTERN13: 숫자+단위 패턴

**정규식:**
```regex
\d+\s*-?\s*(week|weeks|month|months|year|years|day|days|hour|hours|hr|hrs|min|mins|minute|minutes)
```

**설명:**
- 숫자와 단위가 함께 나타나는 일반적인 패턴입니다.
- 하이픈 포함, hr/hrs, min/mins/minute/minutes 단위를 지원합니다.

**예제:**
- `"26 weeks"`
- `"96-week"`
- `"21-months"`
- `"48 hr"`
- `"30 minutes"`
- `"2 min"`

**우선순위:** 13순위

---

### PATTERN14: Percent 패턴

**정규식:**
```regex
%|percent|percentage
```

**설명:**
- 퍼센트 관련 패턴을 감지합니다.
- 분류용 패턴입니다.

**예제:**
- `"50%"`
- `"percent"`
- `"percentage"`

**우선순위:** 14순위

---

### PATTERN15: Time 패턴

**정규식:**
```regex
time\s+to\s+(respond|complete|finish)
```

**설명:**
- "Time to respond", "Time to complete", "Time to finish" 형식을 감지합니다.

**예제:**
- `"Time to respond"`
- `"Time to complete"`
- `"Time to finish"`

**우선순위:** 15순위

---

## 패턴 매칭 실패

패턴이 매칭되지 않는 경우 `pattern_code`는 `NULL`로 저장됩니다.

---

## 패턴 코드 저장

정규화된 데이터는 `outcome_normalized` 테이블의 `pattern_code` 컬럼에 패턴 코드가 저장됩니다.

- `outcome_normalized`: 정규화된 모든 데이터
- `outcome_normalized_success`: 성공한 데이터 (패턴 코드 포함)
- `outcome_normalized_failed`: 실패한 데이터 (패턴 코드 포함)

---

## 패턴 통계 조회

패턴별 통계를 조회하려면 다음 SQL 쿼리를 사용할 수 있습니다:

```sql
SELECT 
    pattern_code,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
WHERE pattern_code IS NOT NULL
GROUP BY pattern_code
ORDER BY count DESC;
```

---

## 참고사항

1. 패턴은 우선순위 순서대로 매칭됩니다.
2. 첫 번째로 매칭된 패턴이 사용됩니다.
3. 복수 시점 패턴(PATTERN10)은 `time_points` JSONB 배열에 저장됩니다.
4. Baseline 패턴(PATTERN1)은 `change_from_baseline_flag`를 `TRUE`로 설정합니다.








