# 작업일지 - 2025년 12월 24일

## 작업 개요

LLM 기반 전처리 시스템 개선 및 결과 분석 도구 개발

---

## 주요 작업 내용

### 1. LLM 전처리 결과 통계 생성 시스템 구축

#### 1.1 요약 통계 리포트 생성 스크립트

- **파일**: `llm/generate_llm_preprocessed_summary.py`
- **기능**:
  - `outcome_llm_preprocessed` 테이블의 통계를 조회하여 MD 파일로 저장
  - 전체 Outcome 통계, Study 기준 성공 현황, Measure Code별 통계, Time Unit별 통계 등 제공
- **SQL 쿼리**: `sql/query_llm_preprocessed_summary_stats.sql` 생성

#### 1.2 최종 결과 (2025-12-24 18:29:37 기준)

```
전체 Outcome: 9,030건
성공: 8,912건 (98.7%)
실패: 118건 (1.3%)

상태별 상세:
- SUCCESS: 8,912건 (98.69%)
- TIMEFRAME_FAILED: 88건 (0.97%)
- MEASURE_FAILED: 17건 (0.19%)
- BOTH_FAILED: 13건 (0.14%)

Study 기준:
- 전체 Study: 1,370건
- 완전히 성공: 1,302건 (95.04%)
- 일부 성공: 40건 (2.92%)
- 완전히 실패: 28건 (2.04%)
```

### 2. LLM 전처리 시각화 도구 개발

#### 2.1 Study별 Outcome 분포 시각화

- **파일**: `analysis/visualize_llm_preprocessed_study_outcome_distribution.py`
- **생성 그래프**:
  - `llm_study_outcome_success_count_histogram.png` - Study별 성공한 outcome 개수 분포
  - `llm_study_outcome_success_rate_distribution.png` - 성공률 구간별 분포 (10% 단위)
  - `llm_study_outcome_success_vs_total_scatter.png` - 성공 개수 vs 전체 개수 산점도

#### 2.2 Measure Code 빈도수 분석

- **파일**: `analysis/analyze_llm_preprocessed_dictionary_frequency.py`
- **생성 그래프**:
  - `llm_measure_code_frequency_by_outcome_top50.png` - Outcome 기준 Top 50 Measure Code
  - `llm_measure_code_frequency_by_study_top50.png` - Study 기준 Top 50 Measure Code

#### 2.3 룰베이스 vs LLM 전처리 비교 시각화

- **파일**: `analysis/visualize_rule_vs_llm_success_rate.py`
- **생성 그래프**:
  - `rule_vs_llm_success_rate_comparison.png` - 룰베이스 vs LLM 성공률 비교
  - `normalization_round_success_rate_with_llm.png` - 정규화 단계별 성공률 (LLM 포함)

**비교 결과**:

- 룰베이스 전처리 (ROUND1): 75.98% (6,861/9,030)
- LLM 전처리 (최신): 98.7% (8,912/9,030)
- **차이**: +22.72%p (LLM이 더 높음)

### 3. LLM 전처리 스크립트 개선

#### 3.1 `llm_preprocess_full.py` 주요 수정 사항

**3.1.1 time_frame 없는 경우 처리 개선**

- `time_frame_raw`가 없고 `measure_code`가 있는 경우:
  - `time_value = 0`
  - `time_unit = null`
  - `llm_status = 'SUCCESS'` (실패 처리하지 않음)

**3.1.2 기존 SUCCESS 항목 보호 기능 추가**

- `ON CONFLICT` 절에서 기존 `llm_status = 'SUCCESS'`인 항목은 업데이트하지 않도록 수정
- CASE 문을 사용하여 기존 SUCCESS 값 유지

**3.1.3 처리 모드 옵션 추가**

- `--failed-only`: 실패한 항목만 재처리 (`llm_status != 'SUCCESS'`)
- `--missing-only`: 누락된 항목만 처리 (기본값)
- `--all`: 전체 처리 (기존 SUCCESS 항목은 보호됨)

**3.1.4 버그 수정**

- `time_frame_raw`가 `None`일 때 발생하던 `AttributeError` 수정
- 3곳 모두 수정 완료

**사용 예시**:

```bash
# 실패한 항목만 재처리
python llm/llm_preprocess_full.py --failed-only 100 19

# 누락된 항목만 처리 (기본값)
python llm/llm_preprocess_full.py --missing-only 100 1

# 전체 처리 (기존 SUCCESS는 보호됨)
python llm/llm_preprocess_full.py --all 0 100 1
```

### 4. PARSE_ERROR 항목 재처리 스크립트

#### 4.1 재처리 스크립트 개발

- **파일**: `llm/llm_reprocess_parse_errors.py`
- **기능**: `llm_notes = '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.'`인 항목만 재처리
- **방식**: UPDATE 방식 (기존 파싱 잘된 건은 유지)

---

## 생성된 파일 목록

### 스크립트

1. `llm/generate_llm_preprocessed_summary.py` - 요약 통계 리포트 생성
2. `analysis/visualize_llm_preprocessed_study_outcome_distribution.py` - Study별 분포 시각화
3. `analysis/analyze_llm_preprocessed_dictionary_frequency.py` - Measure Code 빈도수 분석
4. `analysis/visualize_rule_vs_llm_success_rate.py` - 룰베이스 vs LLM 비교
5. `llm/llm_reprocess_parse_errors.py` - PARSE_ERROR 재처리

### SQL 쿼리

1. `sql/query_llm_preprocessed_summary_stats.sql` - 요약 통계 쿼리

### 리포트

1. `reports/llm_preprocessed_summary_20251224_182937.md` - 최종 요약 리포트

### 시각화

1. `visualization/llm_study_outcome_success_count_histogram.png`
2. `visualization/llm_study_outcome_success_rate_distribution.png`
3. `visualization/llm_study_outcome_success_vs_total_scatter.png`
4. `visualization/llm_measure_code_frequency_by_outcome_top50.png`
5. `visualization/llm_measure_code_frequency_by_study_top50.png`
6. `visualization/rule_vs_llm_success_rate_comparison.png`
7. `visualization/normalization_round_success_rate_with_llm.png`

---

## 최종 성과

### LLM 전처리 최종 결과 (2025-12-24 18:29:37 기준)

- **전체 Outcome**: 9,030건
- **성공**: 8,912건 (98.7%)
- **실패**: 118건 (1.3%)

#### 상태별 상세 통계

- **SUCCESS**: 8,912건 (98.69%)
- **TIMEFRAME_FAILED**: 88건 (0.97%)
- **MEASURE_FAILED**: 17건 (0.19%)
- **BOTH_FAILED**: 13건 (0.14%)

#### Study별 통계

- **전체 Studies**: 1,370건
- **완전히 성공**: 1,302건 (95.04%)
- **일부 성공**: 40건 (2.92%)
- **완전히 실패**: 28건 (2.04%)

#### 실패 이유별 통계

- **TIMEFRAME_FAILED**: 88건 (74.58%)
- **MEASURE_FAILED**: 17건 (14.41%)
- **BOTH_FAILED**: 13건 (11.02%)

### 룰베이스 vs LLM 비교

- **룰베이스 전처리 (ROUND1)**: 75.98% 성공률 (6,861/9,030)
- **LLM 전처리 (최신)**: 98.7% 성공률 (8,912/9,030)
- **성능 향상**: +22.72%p

### 주요 Measure Code 성공률 (Top 10)

1. **ADAS_COG**: 484건 (100.00%)
2. **MMSE**: 337건 (100.00%)
3. **ADCS_ADL**: 224건 (100.00%)
4. **CMAX**: 195건 (100.00%)
5. **CDR_SB**: 183건 (100.00%)
6. **AUC**: 156건 (100.00%)
7. **TMAX**: 124건 (100.00%)
8. **VITAL_SIGNS**: 113건 (100.00%)
9. **CGIC**: 113건 (100.00%)
10. **CDR_GLOBAL**: 76건 (100.00%)

### Time Unit별 성공률

- **weeks**: 4,163/4,173 (99.76%)
- **days**: 1,727/1,728 (99.94%)
- **months**: 1,452/1,459 (99.52%)
- **hours**: 676/676 (100.00%)
- **years**: 459/459 (100.00%)
- **minutes**: 126/127 (99.21%)

### Phase별 성공률

- **PHASE1,PHASE2**: 432/432 (100.00%)
- **NA**: 444/448 (99.11%)
- **PHASE3**: 1,832/1,856 (98.71%)
- **PHASE2**: 2,757/2,790 (98.82%)
- **PHASE4**: 558/567 (98.41%)
- **PHASE1**: 2,430/2,476 (98.14%)

---

## 개선 사항

1. ✅ 기존 SUCCESS 항목 보호 기능 추가
2. ✅ time_frame 없는 경우 올바른 처리 (SUCCESS로 처리)
3. ✅ 다양한 처리 모드 옵션 제공
4. ✅ 버그 수정 (NoneType 에러)
5. ✅ 룰베이스와 LLM 전처리 결과 비교 도구 제공
6. ✅ 상세한 통계 및 시각화 도구 구축

---

## 다음 작업 계획

1. LLM 전처리 결과 검증 프로세스 개선
2. 실패 항목 분석 및 재처리 자동화
3. 성능 모니터링 및 최적화

---

## 참고 사항

- 모든 스크립트는 `outcome_llm_preprocessed` 테이블을 기반으로 동작
- 기존 `outcome_normalized` 테이블과의 비교 분석 가능
- 배치 처리 시 기존 SUCCESS 항목은 자동으로 보호됨
