-- ============================================================================
-- 계층적 통계 쿼리 (깊이 확장 가능한 구조)
-- ============================================================================
-- level, entity_type, group_key, status, sub_status, count, total, percentage
-- ============================================================================

-- ============================================================================
-- 1. NCTID 기준 통계
-- ============================================================================
WITH study_stats AS (
    SELECT 
        nct_id,
        COUNT(*) as total_outcomes,
        COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as success_outcomes,
        COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failed_outcomes,
        COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_failed,
        COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as time_failed,
        COUNT(CASE WHEN failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed
    FROM outcome_normalized
    GROUP BY nct_id
),
study_classification AS (
    SELECT 
        nct_id,
        total_outcomes,
        success_outcomes,
        failed_outcomes,
        CASE 
            WHEN total_outcomes = success_outcomes THEN 'SUCCESS'
            WHEN success_outcomes = 0 THEN 'FULL_FAIL'
            ELSE 'PARTIAL_FAIL'
        END as study_status,
        measure_failed,
        time_failed,
        both_failed
    FROM study_stats
)
SELECT 
    0 as level,
    'nctid' as entity_type,
    'ALL' as group_key,
    'TOTAL' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    COUNT(*) as total,
    100.0 as percentage
FROM study_classification

UNION ALL

SELECT 
    1 as level,
    'nctid' as entity_type,
    'ALL' as group_key,
    'SUCCESS' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM study_classification) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM study_classification) * 100, 2) as percentage
FROM study_classification
WHERE study_status = 'SUCCESS'

UNION ALL

SELECT 
    1 as level,
    'nctid' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM study_classification) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM study_classification) * 100, 2) as percentage
FROM study_classification
WHERE study_status != 'SUCCESS'

UNION ALL

SELECT 
    2 as level,
    'nctid' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'FULL_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM study_classification) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM study_classification) * 100, 2) as percentage
FROM study_classification
WHERE study_status = 'FULL_FAIL'

UNION ALL

SELECT 
    2 as level,
    'nctid' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'PARTIAL_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM study_classification) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM study_classification) * 100, 2) as percentage
FROM study_classification
WHERE study_status = 'PARTIAL_FAIL'

ORDER BY level, entity_type, group_key, status, sub_status;

-- ============================================================================
-- 2. Outcome 기준 통계
-- ============================================================================
WITH outcome_stats AS (
    SELECT 
        outcome_id,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 'MEASURE_FAIL'
            WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 'TIME_FAIL'
            WHEN failure_reason = 'BOTH_FAILED' THEN 'BOTH_FAIL'
            ELSE 'FULL_FAIL'
        END as outcome_status,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason IS NOT NULL THEN 'FAILURE'
        END as outcome_status_main
    FROM outcome_normalized
)
SELECT 
    0 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'TOTAL' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    COUNT(*) as total,
    100.0 as percentage
FROM outcome_stats

UNION ALL

SELECT 
    1 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'SUCCESS' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status_main = 'SUCCESS'

UNION ALL

SELECT 
    1 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status_main = 'FAILURE'

UNION ALL

SELECT 
    2 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'FULL_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status = 'FULL_FAIL'

UNION ALL

SELECT 
    2 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'MEASURE_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status = 'MEASURE_FAIL'

UNION ALL

SELECT 
    2 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'TIME_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status = 'TIME_FAIL'

UNION ALL

SELECT 
    2 as level,
    'outcome' as entity_type,
    'ALL' as group_key,
    'FAILURE' as status,
    'BOTH_FAIL' as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status = 'BOTH_FAIL'

ORDER BY level, entity_type, group_key, status, sub_status;

-- ============================================================================
-- 3. Primary/Secondary 기준 통계
-- ============================================================================
WITH outcome_stats AS (
    SELECT 
        outcome_type,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 'MEASURE_FAIL'
            WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 'TIME_FAIL'
            WHEN failure_reason = 'BOTH_FAILED' THEN 'BOTH_FAIL'
            ELSE 'FULL_FAIL'
        END as outcome_status,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason IS NOT NULL THEN 'FAILURE'
        END as outcome_status_main
    FROM outcome_normalized
)
SELECT 
    0 as level,
    'outcome_type' as entity_type,
    outcome_type as group_key,
    'TOTAL' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    COUNT(*) as total,
    100.0 as percentage
FROM outcome_stats
GROUP BY outcome_type

UNION ALL

SELECT 
    1 as level,
    'outcome_type' as entity_type,
    outcome_type as group_key,
    'SUCCESS' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status_main = 'SUCCESS'
GROUP BY outcome_type

UNION ALL

SELECT 
    1 as level,
    'outcome_type' as entity_type,
    outcome_type as group_key,
    'FAILURE' as status,
    NULL::VARCHAR as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status_main = 'FAILURE'
GROUP BY outcome_type

UNION ALL

SELECT 
    2 as level,
    'outcome_type' as entity_type,
    outcome_type as group_key,
    'FAILURE' as status,
    outcome_status as sub_status,
    COUNT(*) as count,
    (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM outcome_stats o2 WHERE o2.outcome_type = outcome_stats.outcome_type) * 100, 2) as percentage
FROM outcome_stats
WHERE outcome_status_main = 'FAILURE'
GROUP BY outcome_type, outcome_status

ORDER BY level, entity_type, group_key, status, sub_status;

-- ============================================================================
-- 4. Phase 기준 통계
-- ============================================================================
WITH outcome_stats AS (
    SELECT 
        COALESCE(phase, 'NA') as phase,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason = 'MEASURE_CODE_FAILED' THEN 'MEASURE_FAIL'
            WHEN failure_reason = 'TIMEFRAME_FAILED' THEN 'TIME_FAIL'
            WHEN failure_reason = 'BOTH_FAILED' THEN 'BOTH_FAIL'
            ELSE 'FULL_FAIL'
        END as outcome_status,
        CASE 
            WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 'SUCCESS'
            WHEN failure_reason IS NOT NULL THEN 'FAILURE'
        END as outcome_status_main
    FROM outcome_normalized
),
phase_totals AS (
    SELECT phase, COUNT(*) as total_count
    FROM outcome_stats
    GROUP BY phase
),
phase_results AS (
    SELECT 
        0 as level,
        'phase' as entity_type,
        pt.phase as group_key,
        'TOTAL' as status,
        NULL::VARCHAR as sub_status,
        pt.total_count as count,
        pt.total_count as total,
        100.0 as percentage,
        CASE pt.phase
            WHEN 'PHASE1' THEN 1
            WHEN 'PHASE2' THEN 2
            WHEN 'PHASE3' THEN 3
            WHEN 'PHASE4' THEN 4
            ELSE 5
        END as phase_order
    FROM phase_totals pt

    UNION ALL

    SELECT 
        1 as level,
        'phase' as entity_type,
        os.phase as group_key,
        'SUCCESS' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        pt.total_count as total,
        ROUND(COUNT(*)::numeric / pt.total_count * 100, 2) as percentage,
        CASE os.phase
            WHEN 'PHASE1' THEN 1
            WHEN 'PHASE2' THEN 2
            WHEN 'PHASE3' THEN 3
            WHEN 'PHASE4' THEN 4
            ELSE 5
        END as phase_order
    FROM outcome_stats os
    INNER JOIN phase_totals pt ON os.phase = pt.phase
    WHERE os.outcome_status_main = 'SUCCESS'
    GROUP BY os.phase, pt.total_count

    UNION ALL

    SELECT 
        1 as level,
        'phase' as entity_type,
        os.phase as group_key,
        'FAILURE' as status,
        NULL::VARCHAR as sub_status,
        COUNT(*) as count,
        pt.total_count as total,
        ROUND(COUNT(*)::numeric / pt.total_count * 100, 2) as percentage,
        CASE os.phase
            WHEN 'PHASE1' THEN 1
            WHEN 'PHASE2' THEN 2
            WHEN 'PHASE3' THEN 3
            WHEN 'PHASE4' THEN 4
            ELSE 5
        END as phase_order
    FROM outcome_stats os
    INNER JOIN phase_totals pt ON os.phase = pt.phase
    WHERE os.outcome_status_main = 'FAILURE'
    GROUP BY os.phase, pt.total_count

    UNION ALL

    SELECT 
        2 as level,
        'phase' as entity_type,
        os.phase as group_key,
        'FAILURE' as status,
        os.outcome_status as sub_status,
        COUNT(*) as count,
        pt.total_count as total,
        ROUND(COUNT(*)::numeric / pt.total_count * 100, 2) as percentage,
        CASE os.phase
            WHEN 'PHASE1' THEN 1
            WHEN 'PHASE2' THEN 2
            WHEN 'PHASE3' THEN 3
            WHEN 'PHASE4' THEN 4
            ELSE 5
        END as phase_order
    FROM outcome_stats os
    INNER JOIN phase_totals pt ON os.phase = pt.phase
    WHERE os.outcome_status_main = 'FAILURE'
    GROUP BY os.phase, os.outcome_status, pt.total_count
)
SELECT 
    level,
    entity_type,
    group_key,
    status,
    sub_status,
    count,
    total,
    percentage
FROM phase_results
ORDER BY 
    level, 
    entity_type, 
    phase_order,
    status, 
    sub_status;

