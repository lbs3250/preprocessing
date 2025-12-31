-- ============================================
-- Success 테이블에서 Dictionary 매칭 안된 항목 조회
-- ============================================

-- 1. Success 테이블에서 measure_code가 NULL인 항목 (Dictionary 매칭 실패)
SELECT 
    nct_id,
    outcome_type,
    outcome_order,
    measure_raw,
    measure_clean,
    measure_abbreviation,
    description_raw,
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag
FROM outcome_normalized_success
WHERE measure_code IS NULL
ORDER BY measure_clean, nct_id
LIMIT 100;

-- 2. Success 테이블에서 measure_code가 NULL인 항목 통계
SELECT 
    COUNT(*) as total_unmatched,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_clean) as unique_measures,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count
FROM outcome_normalized_success
WHERE measure_code IS NULL;

-- 3. Success 테이블에서 measure_code가 NULL인 항목의 measure_clean 빈도수 (Top 50)
SELECT 
    measure_clean,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT measure_abbreviation, ', ' ORDER BY measure_abbreviation) FILTER (WHERE measure_abbreviation IS NOT NULL) as abbreviations,
    STRING_AGG(DISTINCT LEFT(measure_raw, 100), ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized_success
WHERE measure_code IS NULL
  AND measure_clean IS NOT NULL
  AND measure_clean != ''
GROUP BY measure_clean
ORDER BY frequency DESC, measure_clean
LIMIT 50;

-- 4. Success 테이블에서 measure_code가 NULL이고 measure_abbreviation이 있는 항목 (약어는 있는데 매칭 안된 경우)
SELECT 
    measure_abbreviation,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT measure_clean, ', ' ORDER BY measure_clean) FILTER (WHERE measure_clean IS NOT NULL) as measure_cleans,
    STRING_AGG(DISTINCT LEFT(measure_raw, 100), ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized_success
WHERE measure_code IS NULL
  AND measure_abbreviation IS NOT NULL
  AND measure_abbreviation != ''
GROUP BY measure_abbreviation
ORDER BY frequency DESC, measure_abbreviation
LIMIT 50;

-- 5. Success 테이블에서 measure_code가 NULL인 항목의 전체 리스트 (상세)
SELECT 
    nct_id,
    outcome_type,
    outcome_order,
    measure_raw,
    measure_clean,
    measure_abbreviation,
    description_raw,
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag
FROM outcome_normalized_success
WHERE measure_code IS NULL
ORDER BY measure_clean NULLS LAST, nct_id, outcome_type, outcome_order;






