-- ============================================================================
-- Phase별 정규화 통계 쿼리 (간단 버전)
-- ============================================================================

-- ============================================================================
-- 1. Phase별 데이터 개수
-- ============================================================================
SELECT 
    phase,
    COUNT(*) as total_outcomes,
    COUNT(DISTINCT nct_id) as study_count
FROM outcome_normalized
GROUP BY phase
ORDER BY 
    CASE 
        WHEN phase = 'NA' THEN 1
        WHEN phase LIKE 'PHASE1%' THEN 2
        WHEN phase LIKE 'PHASE2%' THEN 3
        WHEN phase LIKE 'PHASE3%' THEN 4
        WHEN phase LIKE 'PHASE4%' THEN 5
        ELSE 6
    END,
    total_outcomes DESC;

-- ============================================================================
-- 2. Phase별 성공/실패률 (TimeFrame, Measure Code)
-- ============================================================================
SELECT 
    phase,
    COUNT(*) as total_outcomes,
    
    -- 전체 성공/실패
    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count,
    ROUND(COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    
    -- TimeFrame 파싱 성공/실패
    COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as timeframe_success,
    ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_success_rate,
    COUNT(CASE WHEN time_value_main IS NULL OR time_unit_main IS NULL THEN 1 END) as timeframe_failed,
    ROUND(COUNT(CASE WHEN time_value_main IS NULL OR time_unit_main IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_failure_rate,
    
    -- Measure Code 매칭 성공/실패
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as measure_code_success,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_code_success_rate,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as measure_code_failed,
    ROUND(COUNT(CASE WHEN measure_code IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_code_failure_rate,
    
    -- 실패 원인별
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_count,
    COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed_count,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_count
    
FROM outcome_normalized
GROUP BY phase
ORDER BY 
    CASE 
        WHEN phase = 'NA' THEN 1
        WHEN phase LIKE 'PHASE1%' THEN 2
        WHEN phase LIKE 'PHASE2%' THEN 3
        WHEN phase LIKE 'PHASE3%' THEN 4
        WHEN phase LIKE 'PHASE4%' THEN 5
        ELSE 6
    END,
    total_outcomes DESC;

-- ============================================================================
-- 3. Phase NA 제외한 전체 통계
-- ============================================================================
SELECT 
    '전체 (NA 제외)' as category,
    COUNT(*) as total_outcomes,
    COUNT(DISTINCT nct_id) as total_studies,
    
    -- 전체 성공/실패
    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count,
    ROUND(COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    
    -- TimeFrame 파싱 성공/실패
    COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as timeframe_success,
    ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_success_rate,
    COUNT(CASE WHEN time_value_main IS NULL OR time_unit_main IS NULL THEN 1 END) as timeframe_failed,
    ROUND(COUNT(CASE WHEN time_value_main IS NULL OR time_unit_main IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_failure_rate,
    
    -- Measure Code 매칭 성공/실패
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as measure_code_success,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_code_success_rate,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as measure_code_failed,
    ROUND(COUNT(CASE WHEN measure_code IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_code_failure_rate,
    
    -- 실패 원인별
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_count,
    COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed_count,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_count
    
FROM outcome_normalized
WHERE phase != 'NA';

-- ============================================================================
-- 4. Phase별 매칭 실패한 measure_abbreviation 통계
-- ============================================================================
SELECT
    measure_abbreviation,
    phase,
    COUNT(*) AS freq
FROM outcome_normalized_failed
WHERE measure_abbreviation IS NOT NULL
  AND measure_norm IS NULL
GROUP BY measure_abbreviation, phase
ORDER BY freq DESC;
