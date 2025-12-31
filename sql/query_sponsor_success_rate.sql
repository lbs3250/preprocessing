-- ============================================================================
-- 기관별 정규화 성공률/실패율 통계 쿼리
-- ============================================================================
-- outcome_normalized와 study_party_raw를 조인하여 기관별 성공/실패율 계산
-- ============================================================================

-- ============================================================================
-- 1. LEAD_SPONSOR별 전체 통계
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    COUNT(*) as total_outcomes,
    COUNT(DISTINCT n.nct_id) as study_count,
    
    -- 성공/실패 통계
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END) as failed_count,
    COUNT(CASE WHEN n.measure_code IS NULL THEN 1 END) as measure_failed_count,
    COUNT(CASE WHEN n.time_value_main IS NULL OR n.time_unit_main IS NULL THEN 1 END) as timeframe_failed_count,
    
    -- 성공률/실패율
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent,
    ROUND(COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    
    -- failure_reason별 분포
    COUNT(CASE WHEN n.failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed,
    COUNT(CASE WHEN n.failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed,
    COUNT(CASE WHEN n.failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed
    
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
GROUP BY sp.name_raw, sp.class_raw
HAVING COUNT(*) >= 10  -- 최소 10건 이상인 기관만 표시
ORDER BY total_outcomes DESC;

-- ============================================================================
-- 2. LEAD_SPONSOR별 성공률 Top 20 (성공률 높은 순)
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    COUNT(*) as total_outcomes,
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
GROUP BY sp.name_raw, sp.class_raw
HAVING COUNT(*) >= 10
ORDER BY success_rate_percent DESC, total_outcomes DESC
LIMIT 20;

-- ============================================================================
-- 3. LEAD_SPONSOR별 실패율 Top 20 (실패율 높은 순)
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    COUNT(*) as total_outcomes,
    COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END) as failed_count,
    -- study 기준 실패 개수: 하나라도 실패한 outcome이 있으면 그 study는 실패
    COUNT(DISTINCT CASE WHEN n.failure_reason IS NOT NULL THEN n.nct_id END) as study_failed_count,
    ROUND(COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    -- study 기준 실패율
    ROUND(COUNT(DISTINCT CASE WHEN n.failure_reason IS NOT NULL THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as study_failure_rate_percent,
    COUNT(CASE WHEN n.failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed,
    COUNT(CASE WHEN n.failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed,
    COUNT(CASE WHEN n.failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND COALESCE(n.phase, 'NA') != 'NA'
GROUP BY sp.name_raw, sp.class_raw
HAVING COUNT(*) >= 10
ORDER BY failure_rate_percent DESC, total_outcomes DESC
LIMIT 10000;

-- ============================================================================
-- 3-1. 실패율 높은 상위 50개 기관의 실패한 데이터 상세 조회
-- ============================================================================
WITH top_failed_sponsors AS (
    SELECT 
        sp.name_raw as sponsor_name,
        sp.class_raw as sponsor_class,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END) as failed_count,
        COUNT(DISTINCT CASE WHEN n.failure_reason IS NOT NULL THEN n.nct_id END) as study_failed_count,
        ROUND(COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
        ROUND(COUNT(DISTINCT CASE WHEN n.failure_reason IS NOT NULL THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as study_failure_rate_percent
    FROM outcome_normalized n
    INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
    WHERE sp.party_type = 'LEAD_SPONSOR'
      AND COALESCE(n.phase, 'NA') != 'NA'
    GROUP BY sp.name_raw, sp.class_raw
    HAVING COUNT(*) >= 10
    ORDER BY failure_rate_percent DESC, total_outcomes DESC
    LIMIT 50
)
SELECT 
    tfs.sponsor_name,
    tfs.sponsor_class,
    tfs.failure_rate_percent,
    tfs.study_failure_rate_percent,
    n.nct_id,
    n.outcome_type,
    n.outcome_order,
    n.measure_raw,
    n.measure_clean,
    n.measure_abbreviation,
    n.measure_code,
    n.match_type,
    n.match_keyword,
    n.time_frame_raw,
    n.time_value_main,
    n.time_unit_main,
    n.failure_reason,
    n.phase,
    n.description_raw
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
INNER JOIN top_failed_sponsors tfs ON sp.name_raw = tfs.sponsor_name AND sp.class_raw = tfs.sponsor_class
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND COALESCE(n.phase, 'NA') != 'NA'
  AND n.failure_reason IS NOT NULL
ORDER BY tfs.failure_rate_percent DESC, tfs.sponsor_name, n.nct_id, n.outcome_type, n.outcome_order;

-- ============================================================================
-- 4. LEAD_SPONSOR별 Primary/Secondary 성공률 비교
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    n.outcome_type,
    COUNT(*) as total_outcomes,
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
GROUP BY sp.name_raw, sp.class_raw, n.outcome_type
HAVING COUNT(*) >= 5
ORDER BY sp.name_raw, n.outcome_type;

-- ============================================================================
-- 5. LEAD_SPONSOR별 match_type 분포
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    COALESCE(n.match_type, 'NULL (매칭 실패)') as match_type,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY sp.name_raw) * 100, 2) as percentage_within_sponsor
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND sp.name_raw IN (
      SELECT sp2.name_raw
      FROM outcome_normalized n2
      INNER JOIN study_party_raw sp2 ON n2.nct_id = sp2.nct_id
      WHERE sp2.party_type = 'LEAD_SPONSOR'
      GROUP BY sp2.name_raw
      HAVING COUNT(*) >= 20
  )
GROUP BY sp.name_raw, n.match_type
ORDER BY sp.name_raw, count DESC;

-- ============================================================================
-- 6. LEAD_SPONSOR별 failure_reason 상세 분포
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    COALESCE(n.failure_reason, 'SUCCESS (성공)') as failure_reason,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY sp.name_raw) * 100, 2) as percentage_within_sponsor
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND sp.name_raw IN (
      SELECT sp2.name_raw
      FROM outcome_normalized n2
      INNER JOIN study_party_raw sp2 ON n2.nct_id = sp2.nct_id
      WHERE sp2.party_type = 'LEAD_SPONSOR'
      GROUP BY sp2.name_raw
      HAVING COUNT(*) >= 20
  )
GROUP BY sp.name_raw, n.failure_reason
ORDER BY sp.name_raw, count DESC;

-- ============================================================================
-- 7. LEAD_SPONSOR별 Domain 분포 (성공한 경우만)
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    n.domain,
    COUNT(*) as count,
    COUNT(DISTINCT n.measure_code) as unique_measures,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY sp.name_raw) * 100, 2) as percentage_within_sponsor
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND n.measure_code IS NOT NULL
  AND n.failure_reason IS NULL
  AND sp.name_raw IN (
      SELECT sp2.name_raw
      FROM outcome_normalized n2
      INNER JOIN study_party_raw sp2 ON n2.nct_id = sp2.nct_id
      WHERE sp2.party_type = 'LEAD_SPONSOR'
      GROUP BY sp2.name_raw
      HAVING COUNT(*) >= 20
  )
GROUP BY sp.name_raw, n.domain
ORDER BY sp.name_raw, count DESC;

-- ============================================================================
-- 8. LEAD_SPONSOR별 parsing_method 분포
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    COALESCE(n.parsing_method, 'NULL') as parsing_method,
    COUNT(*) as total_count,
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
  AND sp.name_raw IN (
      SELECT sp2.name_raw
      FROM outcome_normalized n2
      INNER JOIN study_party_raw sp2 ON n2.nct_id = sp2.nct_id
      WHERE sp2.party_type = 'LEAD_SPONSOR'
      GROUP BY sp2.name_raw
      HAVING COUNT(*) >= 20
  )
GROUP BY sp.name_raw, n.parsing_method
ORDER BY sp.name_raw, parsing_method;

-- ============================================================================
-- 9. LEAD_SPONSOR별 전체 요약 (간단 버전)
-- ============================================================================
SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    COUNT(*) as total_outcomes,
    COUNT(DISTINCT n.nct_id) as study_count,
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END) as failed_count,
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent,
    ROUND(COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
GROUP BY sp.name_raw, sp.class_raw
HAVING COUNT(*) >= 10
ORDER BY total_outcomes DESC;

