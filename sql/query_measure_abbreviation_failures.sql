-- ============================================================================
-- measure_abbreviation이 있는 경우 중 실패 빈도수 통계
-- ============================================================================
-- measure_abbreviation이 추출되었지만 MEASURE_CODE_FAILED 또는 BOTH_FAILED인 경우 분석
-- ============================================================================

-- ============================================================================
-- 1. measure_abbreviation별 실패 빈도수 (전체)
-- ============================================================================
SELECT 
    measure_abbreviation,
    COUNT(*) as total_count,
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_count,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_count,
    COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END) as total_failed_count,
    ROUND(COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    COUNT(DISTINCT nct_id) as unique_studies
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED')
GROUP BY measure_abbreviation
ORDER BY total_failed_count DESC, measure_abbreviation
LIMIT 100;

-- ============================================================================
-- 2. measure_abbreviation별 실패 빈도수 (Phase별)
-- ============================================================================
SELECT 
    COALESCE(phase, 'NA') as phase,
    measure_abbreviation,
    COUNT(*) as total_count,
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_count,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_count,
    COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END) as total_failed_count,
    ROUND(COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    COUNT(DISTINCT nct_id) as unique_studies
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED')
GROUP BY COALESCE(phase, 'NA'), measure_abbreviation
ORDER BY 
    CASE COALESCE(phase, 'NA')
        WHEN 'PHASE1' THEN 1
        WHEN 'PHASE2' THEN 2
        WHEN 'PHASE3' THEN 3
        WHEN 'PHASE4' THEN 4
        ELSE 5
    END,
    total_failed_count DESC,
    measure_abbreviation;

-- ============================================================================
-- 3. 전체 통계 요약
-- ============================================================================
SELECT 
    COUNT(*) as total_with_abbreviation,
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_total,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_total,
    COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END) as total_failed,
    ROUND(COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END)::numeric / COUNT(*) * 100, 2) as overall_failure_rate_percent,
    COUNT(DISTINCT measure_abbreviation) as unique_abbreviations,
    COUNT(DISTINCT nct_id) as unique_studies
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != '';

-- ============================================================================
-- 4. Phase별 전체 통계 요약
-- ============================================================================
SELECT 
    COALESCE(phase, 'NA') as phase,
    COUNT(*) as total_with_abbreviation,
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed_total,
    COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed_total,
    COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END) as total_failed,
    ROUND(COUNT(CASE WHEN failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED') THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    COUNT(DISTINCT measure_abbreviation) as unique_abbreviations,
    COUNT(DISTINCT nct_id) as unique_studies
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
GROUP BY COALESCE(phase, 'NA')
ORDER BY 
    CASE COALESCE(phase, 'NA')
        WHEN 'PHASE1' THEN 1
        WHEN 'PHASE2' THEN 2
        WHEN 'PHASE3' THEN 3
        WHEN 'PHASE4' THEN 4
        ELSE 5
    END,
    phase;

-- ============================================================================
-- 5. measure_abbreviation별 상세 정보 (실패한 경우만)
-- ============================================================================
SELECT 
    measure_abbreviation,
    failure_reason,
    COUNT(*) as count,
    COUNT(DISTINCT nct_id) as unique_studies,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) 
        FILTER (WHERE measure_clean IS NOT NULL) as sample_measures
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND failure_reason IN ('MEASURE_CODE_FAILED', 'BOTH_FAILED')
GROUP BY measure_abbreviation, failure_reason
ORDER BY count DESC, measure_abbreviation, failure_reason;

