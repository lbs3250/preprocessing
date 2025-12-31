-- ============================================
-- 기관별 Outcome 실패율 Top 20 (실패율 높은순)
-- ============================================

WITH sponsor_outcomes AS (
    SELECT 
        sp.name_raw as sponsor_name,
        COUNT(*) FILTER (WHERE on_failed.outcome_id IS NOT NULL) as failed_count,
        COUNT(*) as total_count
    FROM outcome_normalized on_all
    LEFT JOIN outcome_normalized_failed on_failed 
        ON on_all.outcome_id = on_failed.outcome_id
    LEFT JOIN study_party_raw sp 
        ON on_all.nct_id = sp.nct_id 
        AND sp.party_type = 'LEAD_SPONSOR'
    WHERE sp.name_raw IS NOT NULL
    GROUP BY sp.name_raw
    HAVING COUNT(*) >= 5  -- 최소 5개 이상의 outcome이 있는 기관만
)
SELECT 
    sponsor_name,
    failed_count,
    total_count,
    ROUND(failed_count::numeric / NULLIF(total_count, 0) * 100, 2) as failure_rate_percent
FROM sponsor_outcomes
ORDER BY failure_rate_percent DESC, failed_count DESC
LIMIT 20;

-- ============================================
-- 기관별 Outcome 실패 카운트 Top 20 (실패 카운트 높은순)
-- ============================================

WITH sponsor_outcomes AS (
    SELECT 
        sp.name_raw as sponsor_name,
        COUNT(*) FILTER (WHERE on_failed.outcome_id IS NOT NULL) as failed_count,
        COUNT(*) as total_count
    FROM outcome_normalized on_all
    LEFT JOIN outcome_normalized_failed on_failed 
        ON on_all.outcome_id = on_failed.outcome_id
    LEFT JOIN study_party_raw sp 
        ON on_all.nct_id = sp.nct_id 
        AND sp.party_type = 'LEAD_SPONSOR'
    WHERE sp.name_raw IS NOT NULL
    GROUP BY sp.name_raw
    HAVING COUNT(*) >= 5  -- 최소 5개 이상의 outcome이 있는 기관만
)
SELECT 
    sponsor_name,
    failed_count,
    total_count,
    ROUND(failed_count::numeric / NULLIF(total_count, 0) * 100, 2) as failure_rate_percent
FROM sponsor_outcomes
ORDER BY failed_count DESC, failure_rate_percent DESC
LIMIT 20;







