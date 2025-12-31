-- ============================================
-- outcome_normalized_success 테이블에 포함된 실패 케이스 확인
-- ============================================

-- 1. success 테이블에 있는데 measure_code가 NULL인 경우
SELECT 
    'measure_code가 NULL' as issue_type,
    COUNT(*) as count,
    COUNT(DISTINCT nct_id) as study_count
FROM outcome_normalized_success
WHERE measure_code IS NULL;

-- 2. success 테이블에 있는데 failure_reason이 있는 경우
SELECT 
    'failure_reason이 있음' as issue_type,
    failure_reason,
    COUNT(*) as count,
    COUNT(DISTINCT nct_id) as study_count
FROM outcome_normalized_success
WHERE failure_reason IS NOT NULL
GROUP BY failure_reason
ORDER BY count DESC;

-- 3. success 테이블에 있는데 measure_code가 NULL이거나 failure_reason이 있는 상세 데이터
SELECT 
    nct_id,
    outcome_type,
    outcome_order,
    measure_raw,
    measure_clean,
    measure_code,
    failure_reason,
    CASE 
        WHEN measure_code IS NULL THEN 'measure_code NULL'
        WHEN failure_reason IS NOT NULL THEN 'failure_reason: ' || failure_reason
        ELSE 'OK'
    END as issue
FROM outcome_normalized_success
WHERE measure_code IS NULL 
   OR failure_reason IS NOT NULL
ORDER BY nct_id, outcome_type, outcome_order
LIMIT 50;

-- 4. Study별로 성공한 outcome과 실패한 outcome이 섞여있는 경우
WITH study_outcome_status AS (
    SELECT 
        nct_id,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as successful_outcomes,
        COUNT(CASE WHEN measure_code IS NULL OR failure_reason IS NOT NULL THEN 1 END) as failed_outcomes
    FROM outcome_normalized_success
    GROUP BY nct_id
    HAVING COUNT(CASE WHEN measure_code IS NULL OR failure_reason IS NOT NULL THEN 1 END) > 0
)
SELECT 
    nct_id,
    total_outcomes,
    successful_outcomes,
    failed_outcomes,
    ROUND(failed_outcomes::numeric / total_outcomes * 100, 1) as failed_percentage
FROM study_outcome_status
ORDER BY failed_outcomes DESC, nct_id
LIMIT 20;

-- 5. 통계 요약
SELECT 
    '전체 success 테이블' as category,
    COUNT(*) as total_count,
    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as truly_successful,
    COUNT(CASE WHEN measure_code IS NULL THEN 1 END) as measure_code_null,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as has_failure_reason,
    COUNT(CASE WHEN measure_code IS NULL OR failure_reason IS NOT NULL THEN 1 END) as has_issues
FROM outcome_normalized_success;

