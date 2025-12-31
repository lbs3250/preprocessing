-- ============================================
-- 정규화 패턴별 통계 쿼리
-- ============================================
-- 
-- 실행 순서:
-- 1. update_schema.sql 실행 → match_type, match_keyword 컬럼 추가
-- 2. normalize_phase1.py 실행 → 정규화 재실행 (match_type 채움)
-- 3. separate_normalized_data.py 실행 → success/failed 분리
-- 4. 이 쿼리 파일 실행 → 패턴별 통계 확인
-- ============================================

-- ============================================
-- 1. 매칭 타입(match_type)별 통계
-- ============================================

-- 1-1. match_type별 전체 통계
SELECT 
    COALESCE(match_type, 'NULL (매칭 실패)') as match_type,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY match_type
ORDER BY total_count DESC;

-- 1-2. match_type별 Domain 분포
SELECT 
    match_type,
    domain,
    COUNT(*) as count,
    COUNT(DISTINCT measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY match_type) * 100, 2) as percentage_within_match_type
FROM outcome_normalized
WHERE match_type IS NOT NULL
GROUP BY match_type, domain
ORDER BY match_type, count DESC;

-- 1-3. match_type별 measure_code Top 10
SELECT 
    n.match_type,
    n.measure_code,
    d.canonical_name,
    COUNT(*) as frequency,
    COUNT(DISTINCT n.nct_id) as study_count
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.match_type IS NOT NULL
GROUP BY n.match_type, n.measure_code, d.canonical_name
ORDER BY n.match_type, frequency DESC
LIMIT 10;

-- ============================================
-- 2. 파싱 방법(parsing_method)별 통계
-- ============================================

-- 2-1. parsing_method별 전체 통계
SELECT 
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COUNT(*) as total_count,
    COUNT(measure_code) as matched_count,
    COUNT(CASE WHEN failure_reason IS NULL THEN 1 END) as success_count,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_count,
    ROUND(COUNT(measure_code)::numeric / COUNT(*) * 100, 2) as match_rate_percent,
    ROUND(COUNT(CASE WHEN failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
FROM outcome_normalized
GROUP BY parsing_method
ORDER BY parsing_method;

-- 2-2. parsing_method별 match_type 분포
SELECT 
    parsing_method,
    COALESCE(match_type, 'NULL') as match_type,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY parsing_method) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY parsing_method, match_type
ORDER BY parsing_method, count DESC;

-- 2-3. parsing_method별 failure_reason 분포
SELECT 
    parsing_method,
    COALESCE(failure_reason, 'SUCCESS') as failure_reason,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY parsing_method) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY parsing_method, failure_reason
ORDER BY parsing_method, count DESC;

-- ============================================
-- 3. 실패 원인(failure_reason)별 통계
-- ============================================

-- 3-1. failure_reason별 전체 통계
SELECT 
    COALESCE(failure_reason, 'SUCCESS (성공)') as failure_reason,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY failure_reason
ORDER BY total_count DESC;

-- 3-2. failure_reason별 parsing_method 분포
SELECT 
    COALESCE(failure_reason, 'SUCCESS') as failure_reason,
    parsing_method,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY failure_reason) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY failure_reason, parsing_method
ORDER BY failure_reason, count DESC;

-- 3-3. 실패 케이스 샘플 (MEASURE_FAILED)
SELECT 
    nct_id,
    outcome_type,
    measure_raw,
    measure_clean,
    measure_abbreviation,
    failure_reason,
    parsing_method
FROM outcome_normalized
WHERE failure_reason = 'MEASURE_FAILED'
ORDER BY nct_id, outcome_type
LIMIT 20;

-- 3-4. 실패 케이스 샘플 (TIMEFRAME_FAILED)
SELECT 
    nct_id,
    outcome_type,
    measure_raw,
    time_frame_raw,
    failure_reason,
    parsing_method
FROM outcome_normalized
WHERE failure_reason = 'TIMEFRAME_FAILED'
ORDER BY nct_id, outcome_type
LIMIT 20;

-- 3-5. 실패 케이스 샘플 (BOTH_FAILED)
SELECT 
    nct_id,
    outcome_type,
    measure_raw,
    time_frame_raw,
    failure_reason,
    parsing_method
FROM outcome_normalized
WHERE failure_reason = 'BOTH_FAILED'
ORDER BY nct_id, outcome_type
LIMIT 20;

-- ============================================
-- 4. Domain별 통계
-- ============================================

-- 4-1. Domain별 전체 통계
SELECT 
    COALESCE(domain, 'NULL (Domain 미지정)') as domain,
    COUNT(*) as total_count,
    COUNT(DISTINCT measure_code) as unique_measures,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized WHERE measure_code IS NOT NULL) * 100, 2) as percentage
FROM outcome_normalized
WHERE measure_code IS NOT NULL
GROUP BY domain
ORDER BY total_count DESC;

-- 4-2. Domain별 match_type 분포
SELECT 
    domain,
    COALESCE(match_type, 'NULL') as match_type,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY domain) * 100, 2) as percentage
FROM outcome_normalized
WHERE domain IS NOT NULL
GROUP BY domain, match_type
ORDER BY domain, count DESC;

-- 4-3. Domain별 Top measure_code
SELECT 
    n.domain,
    n.measure_code,
    d.canonical_name,
    COUNT(*) as frequency,
    COUNT(DISTINCT n.nct_id) as study_count
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.domain IS NOT NULL
GROUP BY n.domain, n.measure_code, d.canonical_name
ORDER BY n.domain, frequency DESC
LIMIT 10;

-- ============================================
-- 5. Time Frame 패턴별 통계
-- ============================================

-- 5-1. time_unit_main별 통계
SELECT 
    COALESCE(time_unit_main, 'NULL (파싱 실패)') as time_unit,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    AVG(time_value_main) as avg_time_value,
    MIN(time_value_main) as min_time_value,
    MAX(time_value_main) as max_time_value,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY time_unit_main
ORDER BY total_count DESC;

-- 5-2. change_from_baseline_flag별 통계
SELECT 
    change_from_baseline_flag,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY change_from_baseline_flag
ORDER BY change_from_baseline_flag;

-- 5-3. time_phase별 통계
SELECT 
    COALESCE(time_phase, 'NULL') as time_phase,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY time_phase
ORDER BY total_count DESC;

-- 5-4. Time Frame 파싱 성공/실패 통계
SELECT 
    CASE 
        WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 'SUCCESS (파싱 성공)'
        WHEN time_frame_raw IS NOT NULL THEN 'FAILED (파싱 실패)'
        ELSE 'NULL (time_frame_raw 없음)'
    END as timeframe_status,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY timeframe_status
ORDER BY total_count DESC;

-- ============================================
-- 6. 종합 패턴 매트릭스
-- ============================================

-- 6-1. match_type × parsing_method 매트릭스
SELECT 
    COALESCE(match_type, 'NULL') as match_type,
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COUNT(*) as count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM outcome_normalized
GROUP BY match_type, parsing_method
ORDER BY match_type, parsing_method;

-- 6-2. match_type × failure_reason 매트릭스
SELECT 
    COALESCE(match_type, 'NULL') as match_type,
    COALESCE(failure_reason, 'SUCCESS') as failure_reason,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM outcome_normalized
GROUP BY match_type, failure_reason
ORDER BY match_type, failure_reason;

-- 6-3. parsing_method × failure_reason 매트릭스
SELECT 
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COALESCE(failure_reason, 'SUCCESS') as failure_reason,
    COUNT(*) as count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM outcome_normalized
GROUP BY parsing_method, failure_reason
ORDER BY parsing_method, failure_reason;

-- 6-4. Domain × match_type 매트릭스
SELECT 
    COALESCE(domain, 'NULL') as domain,
    COALESCE(match_type, 'NULL') as match_type,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY domain) * 100, 2) as percentage_within_domain
FROM outcome_normalized
WHERE domain IS NOT NULL
GROUP BY domain, match_type
ORDER BY domain, count DESC;

-- ============================================
-- 7. 성공 케이스 패턴 분석 (outcome_normalized_success)
-- ============================================

-- 7-1. success 테이블의 match_type별 통계
SELECT 
    COALESCE(match_type, 'NULL') as match_type,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized_success) * 100, 2) as percentage
FROM outcome_normalized_success
GROUP BY match_type
ORDER BY total_count DESC;

-- 7-2. success 테이블의 Domain별 통계
SELECT 
    COALESCE(domain, 'NULL') as domain,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized_success) * 100, 2) as percentage
FROM outcome_normalized_success
GROUP BY domain
ORDER BY total_count DESC;

-- 7-3. success 테이블의 parsing_method별 통계
SELECT 
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized_success) * 100, 2) as percentage
FROM outcome_normalized_success
GROUP BY parsing_method
ORDER BY total_count DESC;

-- ============================================
-- 8. 실패 케이스 패턴 분석 (outcome_normalized_failed)
-- ============================================

-- 8-1. failed 테이블의 failure_reason별 통계
SELECT 
    COALESCE(failure_reason, 'NULL') as failure_reason,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized_failed) * 100, 2) as percentage
FROM outcome_normalized_failed
GROUP BY failure_reason
ORDER BY total_count DESC;

-- 8-2. failed 테이블의 parsing_method별 통계
SELECT 
    COALESCE(parsing_method, 'NULL') as parsing_method,
    COALESCE(failure_reason, 'NULL') as failure_reason,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY parsing_method) * 100, 2) as percentage
FROM outcome_normalized_failed
GROUP BY parsing_method, failure_reason
ORDER BY parsing_method, total_count DESC;

-- 8-3. failed 테이블에서 measure_clean 패턴 분석
SELECT 
    measure_clean,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN outcome_type = 'PRIMARY' THEN 1 END) as primary_count,
    COUNT(CASE WHEN outcome_type = 'SECONDARY' THEN 1 END) as secondary_count,
    STRING_AGG(DISTINCT measure_raw, ' | ' ORDER BY measure_raw) as sample_raw_texts
FROM outcome_normalized_failed
WHERE measure_clean IS NOT NULL
  AND measure_clean != ''
GROUP BY measure_clean
ORDER BY frequency DESC
LIMIT 30;

-- ============================================
-- 9. 패턴별 상세 샘플 데이터
-- ============================================

-- 9-1. MEASURE_CODE 매칭 성공 샘플
SELECT 
    n.nct_id,
    n.outcome_type,
    n.measure_raw,
    n.measure_clean,
    n.measure_code,
    d.canonical_name,
    n.match_type,
    n.domain
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.match_type = 'MEASURE_CODE'
ORDER BY n.nct_id, n.outcome_type
LIMIT 20;

-- 9-2. ABBREVIATION 매칭 성공 샘플
SELECT 
    n.nct_id,
    n.outcome_type,
    n.measure_raw,
    n.measure_abbreviation,
    n.measure_code,
    d.canonical_name,
    n.match_type,
    n.match_keyword
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.match_type = 'ABBREVIATION'
ORDER BY n.nct_id, n.outcome_type
LIMIT 20;

-- 9-3. KEYWORD 매칭 성공 샘플
SELECT 
    n.nct_id,
    n.outcome_type,
    n.measure_raw,
    n.measure_clean,
    n.measure_code,
    d.canonical_name,
    n.match_type,
    n.match_keyword
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.match_type = 'KEYWORD'
ORDER BY n.nct_id, n.outcome_type
LIMIT 20;

-- 9-4. CANONICAL_NAME 매칭 성공 샘플
SELECT 
    n.nct_id,
    n.outcome_type,
    n.measure_raw,
    n.measure_clean,
    n.measure_code,
    d.canonical_name,
    n.match_type
FROM outcome_normalized n
LEFT JOIN outcome_measure_dict d ON n.measure_code = d.measure_code
WHERE n.match_type = 'CANONICAL_NAME'
ORDER BY n.nct_id, n.outcome_type
LIMIT 20;

-- ============================================
-- 10. 추가 통계 및 분석
-- ============================================

-- 10-1. Primary/Secondary별 match_type 분포
SELECT 
    outcome_type,
    COALESCE(match_type, 'NULL (매칭 실패)') as match_type,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY outcome_type) * 100, 2) as percentage_within_type
FROM outcome_normalized
GROUP BY outcome_type, match_type
ORDER BY outcome_type, count DESC;

-- 10-2. measure_abbreviation 추출 성공률
SELECT 
    CASE 
        WHEN measure_abbreviation IS NOT NULL THEN '약어 추출 성공'
        ELSE '약어 추출 실패'
    END as abbrev_status,
    COUNT(*) as total_count,
    COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END) as matched_count,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as match_rate_percent
FROM outcome_normalized
WHERE measure_clean IS NOT NULL
GROUP BY abbrev_status
ORDER BY abbrev_status;

-- 10-3. match_keyword별 통계 (매칭에 사용된 키워드)
SELECT 
    match_type,
    match_keyword,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures
FROM outcome_normalized
WHERE match_keyword IS NOT NULL
GROUP BY match_type, match_keyword
ORDER BY match_type, frequency DESC
LIMIT 30;

-- 10-4. 복수 시점(time_points) 패턴 분석
SELECT 
    CASE 
        WHEN time_points IS NOT NULL THEN '복수 시점 (time_points 있음)'
        WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN '단일 시점'
        ELSE '시점 파싱 실패'
    END as timepoint_pattern,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_normalized) * 100, 2) as percentage
FROM outcome_normalized
GROUP BY timepoint_pattern
ORDER BY total_count DESC;

-- 10-5. 전체 요약 통계
SELECT 
    '전체 Outcomes' as category,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures
FROM outcome_normalized
UNION ALL
SELECT 
    '성공 (measure_code IS NOT NULL AND failure_reason IS NULL)' as category,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures
FROM outcome_normalized
WHERE measure_code IS NOT NULL AND failure_reason IS NULL
UNION ALL
SELECT 
    '매칭 성공 (measure_code IS NOT NULL)' as category,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT measure_code) as unique_measures
FROM outcome_normalized
WHERE measure_code IS NOT NULL
UNION ALL
SELECT 
    'Time Frame 파싱 성공' as category,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    NULL as unique_measures
FROM outcome_normalized
WHERE time_value_main IS NOT NULL AND time_unit_main IS NOT NULL
ORDER BY category;

