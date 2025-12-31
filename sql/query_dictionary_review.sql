-- ============================================================================
-- 사전 정리를 위한 리뷰 쿼리
-- ============================================================================

-- ============================================================================
-- 1. 현재 사전에 있는 항목들 확인
-- ============================================================================
SELECT 
    measure_code,
    canonical_name,
    abbreviation,
    domain,
    keywords
FROM outcome_measure_dict
ORDER BY measure_code;

-- ============================================================================
-- 2. 실패한 약어들 중 빈도수 높은 것들 (사전 추가 후보)
-- ============================================================================
SELECT
    measure_abbreviation,
    phase,
    COUNT(*) AS freq,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized_failed
WHERE measure_abbreviation IS NOT NULL
  AND measure_norm IS NULL
GROUP BY measure_abbreviation, phase
ORDER BY freq DESC
LIMIT 100;

-- ============================================================================
-- 3. 약어 추출은 되었지만 매칭 실패한 케이스 (사전에 없는 약어들)
-- ============================================================================
SELECT
    measure_abbreviation,
    COUNT(*) AS freq,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) as sample_measure_clean,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized_failed
WHERE measure_abbreviation IS NOT NULL
  AND measure_code IS NULL
GROUP BY measure_abbreviation
ORDER BY freq DESC
LIMIT 100;


