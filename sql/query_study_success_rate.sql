-- ============================================================================
-- Study 단위 성공률 통계 (nct_id 기준)
-- ============================================================================
-- 한 study의 모든 outcome이 성공한 경우를 카운트
-- 성공 기준: measure_code IS NOT NULL AND failure_reason IS NULL
-- ============================================================================

-- ============================================================================
-- 1. 전체 Study 단위 성공률 (Phase 구분 없음)
-- ============================================================================
WITH study_stats AS (
    SELECT 
        nct_id,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                   AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as both_success_outcomes
    FROM outcome_normalized
    GROUP BY nct_id
)
SELECT 
    COUNT(*) as total_studies,
    COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END) as all_outcomes_success_studies,
    COUNT(CASE WHEN total_outcomes = both_success_outcomes THEN 1 END) as all_outcomes_both_success_studies,
    ROUND(COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_outcomes_success_rate_percent,
    ROUND(COUNT(CASE WHEN total_outcomes = both_success_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_outcomes_both_success_rate_percent,
    
    -- 부분 성공 (일부만 성공)
    COUNT(CASE WHEN success_outcomes > 0 AND success_outcomes < total_outcomes THEN 1 END) as partial_success_studies,
    COUNT(CASE WHEN success_outcomes = 0 THEN 1 END) as all_failed_studies,
    
    -- 평균 outcome 개수
    ROUND(AVG(total_outcomes), 2) as avg_outcomes_per_study,
    MIN(total_outcomes) as min_outcomes_per_study,
    MAX(total_outcomes) as max_outcomes_per_study
FROM study_stats;

-- ============================================================================
-- 2. Phase별 Study 단위 성공률
-- ============================================================================
WITH study_stats AS (
    SELECT 
        nct_id,
        COALESCE(phase, 'NA') as phase,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                   AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as both_success_outcomes
    FROM outcome_normalized
    GROUP BY nct_id, COALESCE(phase, 'NA')
)
SELECT 
    phase,
    COUNT(*) as total_studies,
    COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END) as all_outcomes_success_studies,
    COUNT(CASE WHEN total_outcomes = both_success_outcomes THEN 1 END) as all_outcomes_both_success_studies,
    ROUND(COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_outcomes_success_rate_percent,
    ROUND(COUNT(CASE WHEN total_outcomes = both_success_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_outcomes_both_success_rate_percent,
    
    -- 부분 성공
    COUNT(CASE WHEN success_outcomes > 0 AND success_outcomes < total_outcomes THEN 1 END) as partial_success_studies,
    COUNT(CASE WHEN success_outcomes = 0 THEN 1 END) as all_failed_studies,
    
    -- 평균 outcome 개수
    ROUND(AVG(total_outcomes), 2) as avg_outcomes_per_study
FROM study_stats
GROUP BY phase
ORDER BY 
    CASE phase
        WHEN 'PHASE1' THEN 1
        WHEN 'PHASE2' THEN 2
        WHEN 'PHASE3' THEN 3
        WHEN 'PHASE4' THEN 4
        ELSE 5
    END,
    phase;

-- ============================================================================
-- 3. Phase별 상세 통계 (성공/부분성공/실패 분포)
-- ============================================================================
WITH study_stats AS (
    SELECT 
        nct_id,
        COALESCE(phase, 'NA') as phase,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_outcomes
    FROM outcome_normalized
    GROUP BY nct_id, COALESCE(phase, 'NA')
)
SELECT 
    phase,
    COUNT(*) as total_studies,
    
    -- 모든 outcome 성공
    COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END) as all_success_count,
    ROUND(COUNT(CASE WHEN total_outcomes = success_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_success_rate_percent,
    
    -- 부분 성공 (1개 이상 성공, 하지만 모두는 아님)
    COUNT(CASE WHEN success_outcomes > 0 AND success_outcomes < total_outcomes THEN 1 END) as partial_success_count,
    ROUND(COUNT(CASE WHEN success_outcomes > 0 AND success_outcomes < total_outcomes THEN 1 END)::numeric / COUNT(*) * 100, 2) as partial_success_rate_percent,
    
    -- 전체 실패
    COUNT(CASE WHEN success_outcomes = 0 THEN 1 END) as all_failed_count,
    ROUND(COUNT(CASE WHEN success_outcomes = 0 THEN 1 END)::numeric / COUNT(*) * 100, 2) as all_failed_rate_percent,
    
    -- 평균 outcome 개수
    ROUND(AVG(total_outcomes), 2) as avg_outcomes_per_study,
    ROUND(AVG(success_outcomes), 2) as avg_success_outcomes_per_study
    
FROM study_stats
GROUP BY phase
ORDER BY 
    CASE phase
        WHEN 'PHASE1' THEN 1
        WHEN 'PHASE2' THEN 2
        WHEN 'PHASE3' THEN 3
        WHEN 'PHASE4' THEN 4
        ELSE 5
    END,
    phase;

-- ============================================================================
-- 4. Study 단위 성공률 상세 (nct_id별)
-- ============================================================================
WITH study_stats AS (
    SELECT 
        nct_id,
        COALESCE(phase, 'NA') as phase,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                   AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as both_success_outcomes,
        COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_failed_count,
        COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed_count,
        COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_count
    FROM outcome_normalized
    GROUP BY nct_id, COALESCE(phase, 'NA')
),
study_with_status AS (
    SELECT 
        nct_id,
        phase,
        total_outcomes,
        success_outcomes,
        both_success_outcomes,
        CASE 
            WHEN total_outcomes = success_outcomes THEN 'ALL_SUCCESS'
            WHEN success_outcomes = 0 THEN 'ALL_FAILED'
            ELSE 'PARTIAL_SUCCESS'
        END as study_status,
        ROUND(success_outcomes::numeric / total_outcomes * 100, 2) as success_rate_percent,
        measure_failed_count,
        timeframe_failed_count,
        both_failed_count
    FROM study_stats
)
SELECT 
    nct_id,
    phase,
    total_outcomes,
    success_outcomes,
    both_success_outcomes,
    study_status,
    success_rate_percent,
    measure_failed_count,
    timeframe_failed_count,
    both_failed_count
FROM study_with_status
ORDER BY 
    CASE 
        WHEN study_status = 'ALL_SUCCESS' THEN 1
        WHEN study_status = 'PARTIAL_SUCCESS' THEN 2
        WHEN study_status = 'ALL_FAILED' THEN 3
    END,
    success_rate_percent DESC,
    total_outcomes DESC
LIMIT 100;

