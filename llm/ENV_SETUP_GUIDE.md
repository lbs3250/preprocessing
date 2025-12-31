# .env 파일 설정 가이드

## Gemini API 제한 (gemini-2.5-flash 기준)

| 제한 항목 | 제한값       | 설명         |
| --------- | ------------ | ------------ |
| RPM       | 5회/분       | 분당 요청 수 |
| TPM       | 250K 토큰/분 | 분당 토큰 수 |
| RPD       | 20회/일      | 일일 요청 수 |

## 환경변수 설정

### 1. API 키 설정

```bash
# 필수: 첫 번째 API 키
GEMINI_API_KEY=your_api_key_here

# 선택: 추가 API 키 (여러 키 사용 시 RPD 제한을 분산)
GEMINI_API_KEY_2=your_second_api_key_here
GEMINI_API_KEY_3=your_third_api_key_here
GEMINI_API_KEY_4=your_fourth_api_key_here
# ... 최대 6개까지 권장
```

**여러 키 사용 시:**

- 각 키당 RPD 20회/일
- 6개 키 사용 시 최대 120회/일 가능
- 키는 429 에러 발생 시 자동으로 전환됨

### 2. 모델 설정

```bash
# gemini-2.5-flash (최신, 빠름, RPD 제한 있음)
GEMINI_MODEL=gemini-2.5-flash

# gemini-1.5-flash (안정적, RPM 더 높음)
# GEMINI_MODEL=gemini-1.5-flash
```

### 3. 배치 크기 (BATCH_SIZE)

**가장 중요한 설정!** RPD 제한을 지키기 위해 가능한 크게 설정하세요.

```bash
# 권장값: 데이터량에 따라 조정
BATCH_SIZE=200
```

**배치 크기 선택 가이드:**

| 처리할 항목 수  | 권장 BATCH_SIZE | 예상 호출 횟수 | 6개 키 사용 시 |
| --------------- | --------------- | -------------- | -------------- |
| < 1,000개       | 200             | 5회            | 키당 1회       |
| 1,000~5,000개   | 300             | 17회           | 키당 3회       |
| 5,000~10,000개  | 400             | 25회           | 키당 4회       |
| 10,000~20,000개 | 500             | 40회           | 키당 7회       |
| > 20,000개      | 500 (최대)      | 40+회          | 키당 7+회      |

**토큰 계산:**

- 데이터 100개 ≈ 1,500토큰
- BATCH_SIZE=500 → 약 7,500토큰 (TPM 제한 250K 내)

### 4. 분당 요청 수 제한 (MAX_REQUESTS_PER_MINUTE)

```bash
# gemini-2.5-flash: 5회/분
MAX_REQUESTS_PER_MINUTE=5

# gemini-1.5-flash: 15회/분
# MAX_REQUESTS_PER_MINUTE=15
```

**참고:** 배치 처리를 사용하므로 배치당 1회 호출됩니다.

- 실제 딜레이 = 60 / MAX_REQUESTS_PER_MINUTE 초
- MAX_REQUESTS_PER_MINUTE=5 → 배치당 12초 대기

### 5. 재시도 설정

```bash
# 재시도 횟수 (API 실패 시)
MAX_RETRIES=3

# 재시도 딜레이 (초)
RETRY_DELAY=2.0
```

## 설정 예시

### 예시 1: 소량 데이터 (< 1,000개)

```bash
GEMINI_MODEL=gemini-2.5-flash
MAX_REQUESTS_PER_MINUTE=5
BATCH_SIZE=200
MAX_RETRIES=3
RETRY_DELAY=2.0
```

**예상:**

- 1,000개 항목 → 5회 호출
- 6개 키 사용 시 → 키당 1회 미만
- RPD 제한 여유 있음 ✅

### 예시 2: 중량 데이터 (5,000~10,000개)

```bash
GEMINI_MODEL=gemini-2.5-flash
MAX_REQUESTS_PER_MINUTE=5
BATCH_SIZE=400
MAX_RETRIES=3
RETRY_DELAY=2.0
```

**예상:**

- 10,000개 항목 → 25회 호출
- 6개 키 사용 시 → 키당 약 4회
- RPD 제한(20회) 내 ✅

### 예시 3: 대량 데이터 (> 20,000개)

```bash
GEMINI_MODEL=gemini-2.5-flash
MAX_REQUESTS_PER_MINUTE=5
BATCH_SIZE=500
MAX_RETRIES=3
RETRY_DELAY=2.0

# 추가 키 5개 더 추가 (총 6개 키 권장)
GEMINI_API_KEY_2=...
GEMINI_API_KEY_3=...
GEMINI_API_KEY_4=...
GEMINI_API_KEY_5=...
GEMINI_API_KEY_6=...
```

**예상:**

- 20,000개 항목 → 40회 호출
- 6개 키 사용 시 → 키당 약 7회
- RPD 제한(20회) 내 ✅

## 딜레이 계산

배치 처리 사용 시:

- **배치당 딜레이** = 60 / MAX_REQUESTS_PER_MINUTE (초)
- MAX_REQUESTS_PER_MINUTE=5 → **배치당 12초 대기**

예시:

- 10,000개 항목, BATCH_SIZE=400
- 25개 배치 × 12초 = **약 5분** 처리 시간

## 문제 해결

### RPD 제한 초과 시

1. **BATCH_SIZE 증가**: 가장 효과적

   ```bash
   BATCH_SIZE=500  # 더 크게 설정
   ```

2. **추가 API 키 사용**: RPD 제한 분산

   ```bash
   GEMINI_API_KEY_2=...
   GEMINI_API_KEY_3=...
   # ... 최대 6개까지
   ```

3. **여러 날에 나눠서 처리**: 하루 20회 제한 내에서만 처리

### RPM 제한 초과 시

1. **MAX_REQUESTS_PER_MINUTE 줄이기**

   ```bash
   MAX_REQUESTS_PER_MINUTE=3  # 더 안전하게
   ```

2. **BATCH_SIZE 늘려서 호출 횟수 자체를 줄이기**

## 권장 설정 요약

```bash
# API 키 (최소 1개, 권장 3~6개)
GEMINI_API_KEY=your_key
GEMINI_API_KEY_2=your_key_2
GEMINI_API_KEY_3=your_key_3

# 모델
GEMINI_MODEL=gemini-2.5-flash

# 배치 크기 (가장 중요!)
BATCH_SIZE=300  # 데이터량에 따라 200~500 조정

# 분당 요청 제한
MAX_REQUESTS_PER_MINUTE=5

# 재시도
MAX_RETRIES=3
RETRY_DELAY=2.0
```
