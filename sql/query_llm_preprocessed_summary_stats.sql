-- LLM 전처리 결과 요약 통계 쿼리

-- ============================================================================
-- 1. 전체 Outcome 통계 (성공/실패)
-- ============================================================================

-- 전체 통계
SELECT 
    COUNT(*) as total_outcomes,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED', 'API_FAILED')) as failed_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
    ROUND(COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED', 'API_FAILED'))::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as failed_rate
FROM outcome_llm_preprocessed;

-- 상태별 상세 통계
SELECT 
    llm_status,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed) * 100, 2) as percentage
FROM outcome_llm_preprocessed
GROUP BY llm_status
ORDER BY count DESC;

-- ============================================================================
-- 2. Study 기준 성공 현황 (NCT ID 기준)
-- ============================================================================

-- Study별 통계
WITH StudyStats AS (
    SELECT 
        nct_id,
        COUNT(*) as total_outcomes,
        COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_outcomes,
        COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED')) as failed_outcomes
    FROM outcome_llm_preprocessed
    GROUP BY nct_id
)
SELECT 
    COUNT(*) as total_studies,
    COUNT(*) FILTER (WHERE success_outcomes = total_outcomes) as complete_success_studies,
    COUNT(*) FILTER (WHERE success_outcomes > 0 AND failed_outcomes > 0) as partial_success_studies,
    COUNT(*) FILTER (WHERE success_outcomes = 0) as complete_failed_studies,
    ROUND(COUNT(*) FILTER (WHERE success_outcomes = total_outcomes)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as complete_success_rate,
    ROUND(COUNT(*) FILTER (WHERE success_outcomes > 0 AND failed_outcomes > 0)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as partial_success_rate,
    ROUND(COUNT(*) FILTER (WHERE success_outcomes = 0)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as complete_failed_rate
FROM StudyStats;

-- ============================================================================
-- 3. Measure Code별 통계
-- ============================================================================

-- Measure Code별 성공률 (상위 20개)
SELECT 
    llm_measure_code,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate
FROM outcome_llm_preprocessed
WHERE llm_measure_code IS NOT NULL
GROUP BY llm_measure_code
HAVING COUNT(*) >= 5
ORDER BY total_count DESC
LIMIT 20;

-- ============================================================================
-- 4. Time Unit별 통계
-- ============================================================================

-- Time Unit별 통계
SELECT 
    llm_time_unit,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
    AVG(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as avg_time_value,
    MIN(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as min_time_value,
    MAX(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as max_time_value
FROM outcome_llm_preprocessed
WHERE llm_time_unit IS NOT NULL
GROUP BY llm_time_unit
ORDER BY total_count DESC;

-- ============================================================================
-- 5. 검증 상태별 통계 (SUCCESS 항목 기준)
-- ============================================================================

-- SUCCESS 항목의 검증 상태 분포
SELECT 
    llm_validation_status,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NOT NULL) * 100, 2) as percentage,
    AVG(llm_validation_confidence) as avg_confidence
FROM outcome_llm_preprocessed
WHERE llm_status = 'SUCCESS'
  AND llm_validation_status IS NOT NULL
GROUP BY llm_validation_status
ORDER BY count DESC;

-- ============================================================================
-- 6. 실패 이유별 통계
-- ============================================================================

-- failure_reason별 통계
SELECT 
    failure_reason,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE failure_reason IS NOT NULL) * 100, 2) as percentage
FROM outcome_llm_preprocessed
WHERE failure_reason IS NOT NULL
GROUP BY failure_reason
ORDER BY count DESC;

-- ============================================================================
-- 7. Phase별 통계
-- ============================================================================

-- Phase별 성공률
SELECT 
    phase,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate
FROM outcome_llm_preprocessed
WHERE phase IS NOT NULL
GROUP BY phase
ORDER BY total_count DESC;

