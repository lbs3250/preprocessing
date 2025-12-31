-- ============================================
-- Dictionary 매칭 통계 쿼리
-- ============================================

-- 1. 전체 통계
SELECT 
    COUNT(*) as total_outcomes,
    COUNT(measure_code) as dict_matched,
    COUNT(*) - COUNT(measure_code) as dict_unmatched,
    ROUND(COUNT(measure_code)::numeric / COUNT(*) * 100, 2) as match_rate_percent
FROM outcome_normalized;

-- 2. Primary/Secondary별 Dictionary 매칭 통계
SELECT 
    outcome_type,
    COUNT(*) as total,
    COUNT(measure_code) as dict_matched,
    COUNT(*) - COUNT(measure_code) as dict_unmatched,
    ROUND(COUNT(measure_code)::numeric / COUNT(*) * 100, 2) as match_rate_percent
FROM outcome_normalized
GROUP BY outcome_type
ORDER BY outcome_type;

-- 3. Domain별 분포 (매칭 성공한 경우만)
SELECT 
    domain,
    COUNT(*) as count,
    COUNT(DISTINCT measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized WHERE measure_code IS NOT NULL) * 100, 2) as percentage
FROM outcome_normalized
WHERE measure_code IS NOT NULL
GROUP BY domain
ORDER BY count DESC;

-- 4. measure_code별 빈도수 (매칭 성공한 경우)
SELECT 
    n.measure_code,
    d.canonical_name,
    n.domain,
    COUNT(*) as frequency,
    COUNT(DISTINCT n.nct_id) as study_count,
    COUNT(CASE WHEN n.outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN n.outcome_type = 'SECONDARY' THEN 1 END) as secondary_count
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.measure_code IS NOT NULL
GROUP BY n.measure_code, d.canonical_name, n.domain
ORDER BY frequency DESC;

-- 5. Dictionary 매칭 실패한 measure_clean 샘플 (빈도수 기준)
SELECT 
    measure_clean,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_clean IS NOT NULL
  AND measure_clean != ''
GROUP BY measure_clean
ORDER BY frequency DESC;

-- 5-1. Dictionary 매칭 실패한 전체 리스트 (상세)
SELECT 
    nct_id,
    outcome_type,
    outcome_order,
    measure_raw,
    measure_clean,
    measure_abbreviation,
    description_raw,
    time_frame_raw
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_clean IS NOT NULL
  AND measure_clean != ''
ORDER BY measure_clean, nct_id;

-- 6. 약어 추출 성공 vs Dictionary 매칭 성공 비교
SELECT 
    CASE 
        WHEN measure_abbreviation IS NOT NULL AND measure_code IS NOT NULL THEN '약어 추출 + Dictionary 매칭 성공'
        WHEN measure_abbreviation IS NOT NULL AND measure_code IS NULL THEN '약어 추출 성공, Dictionary 매칭 실패'
        WHEN measure_abbreviation IS NULL AND measure_code IS NOT NULL THEN '약어 추출 실패, Dictionary 매칭 성공'
        ELSE '약어 추출 실패 + Dictionary 매칭 실패'
    END as category,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY category
ORDER BY count DESC;

-- 7. Dictionary 매칭 실패한 경우 중 약어가 있는 경우 (추가 Dictionary 항목 후보)
SELECT 
    measure_abbreviation,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) as sample_measure_clean
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_abbreviation IS NOT NULL
GROUP BY measure_abbreviation
ORDER BY frequency DESC;

-- 8. Primary/Secondary별 Domain 분포 (매칭 성공한 경우만)
SELECT 
    outcome_type,
    domain,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY outcome_type) * 100, 2) as percentage_within_type
FROM outcome_normalized
WHERE measure_code IS NOT NULL
GROUP BY outcome_type, domain
ORDER BY outcome_type, count DESC;

-- 9. Dictionary 추가 후보 리스트 (빈도수 기반)
-- measure_code가 없고 약어가 있는 경우
SELECT 
    measure_abbreviation,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    STRING_AGG(DISTINCT measure_clean, ' | ' ORDER BY measure_clean) as sample_measure_clean,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_measure_raw
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_abbreviation IS NOT NULL
GROUP BY measure_abbreviation
ORDER BY frequency DESC;

-- 10. Dictionary 추가 후보 리스트 (measure_clean 기반, 빈도수 기반)
-- measure_code가 없고 measure_clean이 있는 경우
SELECT 
    measure_clean,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_measure_raw
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_clean IS NOT NULL
  AND measure_clean != ''
GROUP BY measure_clean
ORDER BY frequency DESC
LIMIT 100;

-- ============================================
-- parsing_method별 통계 (RULE_BASED vs LLM)
-- ============================================

-- 11. parsing_method별 전체 통계
SELECT 
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COUNT(*) as total_outcomes,
    COUNT(measure_code) as dict_matched,
    COUNT(*) - COUNT(measure_code) as dict_unmatched,
    ROUND(COUNT(measure_code)::numeric / COUNT(*) * 100, 2) as match_rate_percent,
    COUNT(CASE WHEN failure_reason IS NULL THEN 1 END) as success_count,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count
FROM outcome_normalized
GROUP BY parsing_method
ORDER BY parsing_method;

-- 12. parsing_method별 Primary/Secondary 통계
SELECT 
    parsing_method,
    outcome_type,
    COUNT(*) as total,
    COUNT(measure_code) as dict_matched,
    ROUND(COUNT(measure_code)::numeric / COUNT(*) * 100, 2) as match_rate_percent
FROM outcome_normalized
GROUP BY parsing_method, outcome_type
ORDER BY parsing_method, outcome_type;

-- 13. parsing_method별 Domain 분포 (매칭 성공한 경우만)
SELECT 
    parsing_method,
    domain,
    COUNT(*) as count,
    COUNT(DISTINCT measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY parsing_method) * 100, 2) as percentage_within_method
FROM outcome_normalized
WHERE measure_code IS NOT NULL
GROUP BY parsing_method, domain
ORDER BY parsing_method, count DESC;

-- 14. parsing_method별 measure_code 빈도수 비교 (Top 20)
SELECT 
    n.measure_code,
    d.canonical_name,
    n.domain,
    COUNT(CASE WHEN n.parsing_method = 'RULE_BASED' THEN 1 END) as rule_based_count,
    COUNT(CASE WHEN n.parsing_method = 'LLM' THEN 1 END) as llm_count,
    COUNT(*) as total_count
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.measure_code IS NOT NULL
GROUP BY n.measure_code, d.canonical_name, n.domain
ORDER BY total_count DESC
LIMIT 20;

-- 15. parsing_method별 Dictionary 매칭 실패한 measure_clean 빈도수 (Top 30)
SELECT 
    parsing_method,
    measure_clean,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count
FROM outcome_normalized
WHERE measure_code IS NULL
  AND measure_clean IS NOT NULL
  AND measure_clean != ''
GROUP BY parsing_method, measure_clean
ORDER BY parsing_method, frequency DESC
LIMIT 30;

