-- ============================================================================
-- ADAS 관련 measure_abbreviation 추출 및 통계
-- ============================================================================
-- measure_abbreviation에 "adas"가 포함된 모든 항목 추출
-- 키워드 추가를 위한 데이터 수집
-- ============================================================================

-- ============================================================================
-- 1. ADAS 관련 measure_abbreviation 전체 목록 (빈도수 순)
-- ============================================================================
SELECT 
    measure_abbreviation,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as unique_studies,
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as matched_count,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as unmatched_count,
    ROUND(COUNT(CASE WHEN measure_code IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as unmatched_rate_percent,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) 
        FILTER (WHERE measure_clean IS NOT NULL) as sample_measures
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND LOWER(measure_abbreviation) LIKE '%adas%'
GROUP BY measure_abbreviation
ORDER BY total_count DESC, measure_abbreviation;

-- ============================================================================
-- 2. ADAS 관련 measure_abbreviation - 매칭 실패한 경우만
-- ============================================================================
SELECT 
    measure_abbreviation,
    COUNT(*) as unmatched_count,
    COUNT(DISTINCT nct_id) as unique_studies,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) 
        FILTER (WHERE measure_clean IS NOT NULL) as sample_measures,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) 
        FILTER (WHERE measure_raw IS NOT NULL) as sample_raw_measures
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND LOWER(measure_abbreviation) LIKE '%adas%'
  AND measure_code IS NULL
GROUP BY measure_abbreviation
ORDER BY unmatched_count DESC, measure_abbreviation;

-- ============================================================================
-- 3. ADAS 관련 measure_abbreviation - Phase별 통계
-- ============================================================================
SELECT 
    COALESCE(phase, 'NA') as phase,
    measure_abbreviation,
    COUNT(*) as total_count,
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as matched_count,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as unmatched_count
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND LOWER(measure_abbreviation) LIKE '%adas%'
GROUP BY COALESCE(phase, 'NA'), measure_abbreviation
ORDER BY 
    CASE COALESCE(phase, 'NA')
        WHEN 'PHASE1' THEN 1
        WHEN 'PHASE2' THEN 2
        WHEN 'PHASE3' THEN 3
        WHEN 'PHASE4' THEN 4
        ELSE 5
    END,
    unmatched_count DESC,
    measure_abbreviation;

-- ============================================================================
-- 4. ADAS 관련 전체 통계 요약
-- ============================================================================
SELECT 
    COUNT(*) as total_adas_abbreviation_count,
    COUNT(DISTINCT measure_abbreviation) as unique_adas_abbreviations,
    COUNT(DISTINCT nct_id) as unique_studies,
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as matched_count,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as unmatched_count,
    ROUND(COUNT(CASE WHEN measure_code IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as unmatched_rate_percent
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND LOWER(measure_abbreviation) LIKE '%adas%';

-- ============================================================================
-- 5. ADAS 관련 measure_abbreviation 상세 정보 (매칭 실패한 경우)
-- ============================================================================
SELECT 
    nct_id,
    phase,
    outcome_type,
    measure_abbreviation,
    measure_clean,
    measure_raw,
    failure_reason,
    match_type
FROM outcome_normalized
WHERE measure_abbreviation IS NOT NULL 
  AND measure_abbreviation != ''
  AND LOWER(measure_abbreviation) LIKE '%adas%'
  AND measure_code IS NULL
ORDER BY measure_abbreviation, nct_id, outcome_type, outcome_order
LIMIT 200;

