-- outcome_llm_preprocessed 테이블 상태 통계 쿼리

-- ============================================================================
-- 1. llm_status별 통계 (전처리 상태)
-- ============================================================================

-- 전체 llm_status 분포
SELECT 
    llm_status,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed) * 100, 2) as percentage
FROM outcome_llm_preprocessed
GROUP BY llm_status
ORDER BY count DESC;

-- llm_status별 상세 통계 (신뢰도 포함)
SELECT 
    llm_status,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_measure_code IS NOT NULL) as with_measure,
    COUNT(*) FILTER (WHERE llm_time_value IS NOT NULL) as with_time,
    COUNT(*) FILTER (WHERE llm_measure_code IS NOT NULL AND llm_time_value IS NOT NULL) as complete,
    AVG(llm_confidence) as avg_confidence,
    MIN(llm_confidence) as min_confidence,
    MAX(llm_confidence) as max_confidence
FROM outcome_llm_preprocessed
GROUP BY llm_status
ORDER BY total_count DESC;

-- ============================================================================
-- 2. llm_validation_status별 통계 (검증 상태)
-- ============================================================================

-- 전체 검증 상태 분포
SELECT 
    llm_validation_status,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE llm_validation_status IS NOT NULL) * 100, 2) as percentage
FROM outcome_llm_preprocessed
WHERE llm_validation_status IS NOT NULL
GROUP BY llm_validation_status
ORDER BY count DESC;

-- 검증 상태별 상세 통계 (신뢰도 포함)
SELECT 
    llm_validation_status,
    COUNT(*) as total_count,
    AVG(llm_validation_confidence) as avg_confidence,
    MIN(llm_validation_confidence) as min_confidence,
    MAX(llm_validation_confidence) as max_confidence,
    COUNT(*) FILTER (WHERE llm_validation_confidence >= 0.9) as high_confidence_count,
    COUNT(*) FILTER (WHERE llm_validation_confidence < 0.5) as low_confidence_count
FROM outcome_llm_preprocessed
WHERE llm_validation_status IS NOT NULL
GROUP BY llm_validation_status
ORDER BY total_count DESC;

-- ============================================================================
-- 3. llm_status와 llm_validation_status 교차 통계
-- ============================================================================

-- 전처리 상태별 검증 상태 분포
SELECT 
    llm_status,
    llm_validation_status,
    COUNT(*) as count
FROM outcome_llm_preprocessed
WHERE llm_validation_status IS NOT NULL
GROUP BY llm_status, llm_validation_status
ORDER BY llm_status, count DESC;

-- SUCCESS 항목의 검증 상태 상세
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
-- 4. failure_reason별 통계
-- ============================================================================

-- 실패 이유별 통계
SELECT 
    failure_reason,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE failure_reason IS NOT NULL) * 100, 2) as percentage
FROM outcome_llm_preprocessed
WHERE failure_reason IS NOT NULL
GROUP BY failure_reason
ORDER BY count DESC;

-- ============================================================================
-- 5. 전체 요약 통계
-- ============================================================================

-- 전체 요약
SELECT 
    COUNT(*) as total_outcomes,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED')) as failed_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED') as verified_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NULL) as not_validated_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED')::NUMERIC / 
          NULLIF(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NOT NULL), 0) * 100, 2) as verified_rate
FROM outcome_llm_preprocessed;

-- ============================================================================
-- 6. Study별 통계
-- ============================================================================

-- Study별 전처리 성공률
WITH StudyStats AS (
    SELECT 
        nct_id,
        COUNT(*) as total_outcomes,
        COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_outcomes,
        COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED') as verified_outcomes
    FROM outcome_llm_preprocessed
    GROUP BY nct_id
)
SELECT 
    COUNT(*) as total_studies,
    COUNT(*) FILTER (WHERE success_outcomes = total_outcomes) as all_success_studies,
    COUNT(*) FILTER (WHERE verified_outcomes = success_outcomes AND success_outcomes > 0) as all_verified_studies,
    COUNT(*) FILTER (WHERE success_outcomes = 0) as all_failed_studies,
    AVG(success_outcomes::NUMERIC / NULLIF(total_outcomes, 0) * 100) as avg_success_rate,
    AVG(verified_outcomes::NUMERIC / NULLIF(success_outcomes, 0) * 100) as avg_verified_rate
FROM StudyStats;

-- ============================================================================
-- 7. 시간대별 통계 (생성일 기준)
-- ============================================================================

-- 일별 처리 통계
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED') as verified_count
FROM outcome_llm_preprocessed
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ============================================================================
-- 8. Measure Code별 통계
-- ============================================================================

-- Measure Code별 성공률 및 검증률
SELECT 
    llm_measure_code,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED') as verified_count,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
    ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED')::NUMERIC / 
          NULLIF(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NOT NULL), 0) * 100, 2) as verified_rate
FROM outcome_llm_preprocessed
WHERE llm_measure_code IS NOT NULL
GROUP BY llm_measure_code
HAVING COUNT(*) >= 5
ORDER BY total_count DESC
LIMIT 20;

-- ============================================================================
-- 9. Time Unit별 통계
-- ============================================================================

-- Time Unit별 통계
SELECT 
    llm_time_unit,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status = 'VERIFIED') as verified_count,
    AVG(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as avg_time_value,
    MIN(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as min_time_value,
    MAX(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as max_time_value
FROM outcome_llm_preprocessed
WHERE llm_time_unit IS NOT NULL
GROUP BY llm_time_unit
ORDER BY total_count DESC;

