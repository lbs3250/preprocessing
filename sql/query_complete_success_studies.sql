-- ============================================
-- 완전히 성공한 Study 개수 조회
-- ============================================
-- 성공 테이블에 있는 nct_id 중에서
-- 실패 테이블에 없는 nct_id의 개수
-- (즉, 모든 outcome이 성공한 study)

SELECT 
    COUNT(DISTINCT success_nct.nct_id) as complete_success_study_count,
    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized_success) as total_success_studies,
    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized_failed) as total_failed_studies,
    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized) as total_all_studies
FROM (
    SELECT DISTINCT nct_id 
    FROM outcome_normalized_success
) success_nct
WHERE NOT EXISTS (
    SELECT 1 
    FROM outcome_normalized_failed failed
    WHERE failed.nct_id = success_nct.nct_id
);

-- 상세 정보 (각 카테고리별 개수)
SELECT 
    '완전히 성공한 Study' as category,
    COUNT(DISTINCT success_nct.nct_id) as count
FROM (
    SELECT DISTINCT nct_id 
    FROM outcome_normalized_success
) success_nct
WHERE NOT EXISTS (
    SELECT 1 
    FROM outcome_normalized_failed failed
    WHERE failed.nct_id = success_nct.nct_id
)

UNION ALL

SELECT 
    '일부 성공한 Study (일부 실패 포함)' as category,
    COUNT(DISTINCT mixed.nct_id) as count
FROM (
    SELECT DISTINCT nct_id 
    FROM outcome_normalized_success
    INTERSECT
    SELECT DISTINCT nct_id 
    FROM outcome_normalized_failed
) mixed

UNION ALL

SELECT 
    '완전히 실패한 Study' as category,
    COUNT(DISTINCT failed_nct.nct_id) as count
FROM (
    SELECT DISTINCT nct_id 
    FROM outcome_normalized_failed
) failed_nct
WHERE NOT EXISTS (
    SELECT 1 
    FROM outcome_normalized_success success
    WHERE success.nct_id = failed_nct.nct_id
);







