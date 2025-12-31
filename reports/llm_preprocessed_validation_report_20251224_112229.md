# LLM 전처리 성공 항목 검증 리포트

생성일시: 2025-12-24 11:22:29

## 1. 전체 통계

- **전체 SUCCESS 항목**: 279개
- **미검증**: 279개 (100.00%)

## 2. 상태별 상세 통계


## 3. Study별 통계

- **전체 Study**: 41개

## 4. Measure Code별 통계 (상위 20개)

| Measure Code | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 |
|-------------|----------|--------------|-------------|
| PK | 24 | 0 | 0.00% |
| ADAS_COG | 17 | 0 | 0.00% |
| AE | 16 | 0 | 0.00% |
| ECG | 12 | 0 | 0.00% |
| LAB_TESTS | 10 | 0 | 0.00% |
| MMSE | 10 | 0 | 0.00% |
| AE_SAE | 9 | 0 | 0.00% |
| ADCS_ADL | 8 | 0 | 0.00% |
| NPI | 7 | 0 | 0.00% |
| VITAL_SIGNS | 6 | 0 | 0.00% |
| CDR_SB | 5 | 0 | 0.00% |
| AUC | 5 | 0 | 0.00% |
| MRI | 5 | 0 | 0.00% |
| CMAX | 5 | 0 | 0.00% |
| CIBIC_PLUS | 5 | 0 | 0.00% |

## 5. Time Unit별 통계

| Time Unit | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 | 평균 Time Value |
|----------|----------|--------------|-------------|----------------|
| weeks | 129 | 0 | 0.00% | 0.0 |
| days | 80 | 0 | 0.00% | 0.0 |
| months | 39 | 0 | 0.00% | 0.0 |
| hours | 18 | 0 | 0.00% | 0.0 |
| minutes | 7 | 0 | 0.00% | 0.0 |
| years | 6 | 0 | 0.00% | 0.0 |

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

