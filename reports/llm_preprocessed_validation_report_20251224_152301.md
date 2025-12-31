# LLM 전처리 성공 항목 검증 리포트

생성일시: 2025-12-24 15:23:01

## 1. 전체 통계

- **전체 SUCCESS 항목**: 6,211개
- **미검증**: 6,211개 (100.00%)

## 2. 상태별 상세 통계


## 3. Study별 통계

- **전체 Study**: 916개

## 4. Measure Code별 통계 (상위 20개)

| Measure Code | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 |
|-------------|----------|--------------|-------------|
| ADAS_COG | 318 | 0 | 0.00% |
| MMSE | 226 | 0 | 0.00% |
| AE | 212 | 0 | 0.00% |
| NPI | 207 | 0 | 0.00% |
| PK | 158 | 0 | 0.00% |
| ADCS_ADL | 150 | 0 | 0.00% |
| CMAX | 145 | 0 | 0.00% |
| AMYLOID_PET | 136 | 0 | 0.00% |
| CDR_SB | 125 | 0 | 0.00% |
| ADVERSE_EVENTS | 116 | 0 | 0.00% |
| AUC | 112 | 0 | 0.00% |
| VITAL_SIGNS | 101 | 0 | 0.00% |
| TMAX | 100 | 0 | 0.00% |
| CGIC | 87 | 0 | 0.00% |
| ECG | 87 | 0 | 0.00% |
| TAU_PET | 84 | 0 | 0.00% |
| CSF_ABETA | 69 | 0 | 0.00% |
| SAFETY_TOLERABILITY | 59 | 0 | 0.00% |
| CDR_GLOBAL | 53 | 0 | 0.00% |
| CIBIC_PLUS | 52 | 0 | 0.00% |

## 5. Time Unit별 통계

| Time Unit | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 | 평균 Time Value |
|----------|----------|--------------|-------------|----------------|
| weeks | 2,838 | 0 | 0.00% | 0.0 |
| days | 1,263 | 0 | 0.00% | 0.0 |
| months | 1,077 | 0 | 0.00% | 0.0 |
| hours | 541 | 0 | 0.00% | 0.0 |
| years | 330 | 0 | 0.00% | 0.0 |
| minutes | 95 | 0 | 0.00% | 0.0 |
| week | 38 | 0 | 0.00% | 0.0 |
| baseline | 14 | 0 | 0.00% | 0.0 |
| visits | 12 | 0 | 0.00% | 0.0 |
| year | 2 | 0 | 0.00% | 0.0 |
| month | 1 | 0 | 0.00% | 0.0 |

## 6. 검증 방법

1. **대상**: `outcome_llm_preprocessed` 테이블에서 `llm_status = 'SUCCESS'`인 항목
2. **검증 내용**:
   - 원본 데이터(`measure_raw`, `time_frame_raw`)와 LLM 추출 결과(`llm_measure_code`, `llm_time_value`, `llm_time_unit`) 비교
   - Measure Code 일치 여부 확인
   - Time 정보 일치 여부 확인 (단일 시점, 범위 시점, 복수 시점 모두 고려)
3. **검증 상태**:
   - `VERIFIED`: 원본과 추출 결과가 완벽하게 일치
   - `UNCERTAIN`: 애매한 경우 또는 불확실한 매칭
   - `MEASURE_FAILED`: Measure Code 불일치
   - `TIMEFRAME_FAILED`: Time 정보 불일치
   - `BOTH_FAILED`: Measure Code와 Time 정보 모두 불일치
4. **검증 결과 저장**: `llm_validation_status`, `llm_validation_confidence`, `llm_validation_notes` 컬럼에 저장

## 7. 요약

