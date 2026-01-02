-- 전체 Feature 통계 (Inclusion/Exclusion/Total Top 100)
-- 숫자형 여부와 관계없이 모든 feature의 통계

WITH all_expanded AS (
    SELECT 
        iep.nct_id,
        'INCLUSION' as criteria_type,
        jsonb_array_elements(iep.inclusion_criteria)::jsonb as criterion
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.inclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.inclusion_criteria) = 'array'
      AND iep.inclusion_criteria != '[]'::jsonb
    UNION ALL
    SELECT 
        iep.nct_id,
        'EXCLUSION' as criteria_type,
        jsonb_array_elements(iep.exclusion_criteria)::jsonb as criterion
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.exclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.exclusion_criteria) = 'array'
      AND iep.exclusion_criteria != '[]'::jsonb
),
all_features AS (
    SELECT 
        nct_id,
        criteria_type,
        criterion->>'feature' as feature,
        criterion->>'operator' as operator
    FROM all_expanded
    WHERE criterion->>'feature' IS NOT NULL
),
feature_stats AS (
    SELECT 
        feature,
        COUNT(*) FILTER (WHERE criteria_type = 'INCLUSION') as inclusion_count,
        COUNT(*) FILTER (WHERE criteria_type = 'EXCLUSION') as exclusion_count,
        COUNT(*) as total_count,
        COUNT(DISTINCT nct_id) FILTER (WHERE criteria_type = 'INCLUSION') as inclusion_study_count,
        COUNT(DISTINCT nct_id) FILTER (WHERE criteria_type = 'EXCLUSION') as exclusion_study_count,
        COUNT(DISTINCT nct_id) as total_study_count,
        COUNT(DISTINCT operator) as operator_count,
        STRING_AGG(DISTINCT operator, ', ' ORDER BY operator) as operators_used
    FROM all_features
    GROUP BY feature
)
SELECT * FROM (
    -- Total 기준 Top 100
    SELECT * FROM (
        SELECT 
            'TOTAL' as sort_by,
            feature,
            inclusion_count,
            exclusion_count,
            total_count,
            inclusion_study_count,
            exclusion_study_count,
            total_study_count,
            operator_count,
            operators_used
        FROM feature_stats
        ORDER BY total_count DESC
        LIMIT 100
    ) total_sub

    UNION ALL

    -- Inclusion 기준 Top 100
    SELECT * FROM (
        SELECT 
            'INCLUSION' as sort_by,
            feature,
            inclusion_count,
            exclusion_count,
            total_count,
            inclusion_study_count,
            exclusion_study_count,
            total_study_count,
            operator_count,
            operators_used
        FROM feature_stats
        ORDER BY inclusion_count DESC
        LIMIT 100
    ) inc_sub

    UNION ALL

    -- Exclusion 기준 Top 100
    SELECT * FROM (
        SELECT 
            'EXCLUSION' as sort_by,
            feature,
            inclusion_count,
            exclusion_count,
            total_count,
            inclusion_study_count,
            exclusion_study_count,
            total_study_count,
            operator_count,
            operators_used
        FROM feature_stats
        ORDER BY exclusion_count DESC
        LIMIT 100
    ) exc_sub
) all_results
ORDER BY 
    CASE sort_by 
        WHEN 'TOTAL' THEN 1
        WHEN 'INCLUSION' THEN 2
        WHEN 'EXCLUSION' THEN 3
    END,
    CASE sort_by 
        WHEN 'TOTAL' THEN total_count 
        WHEN 'INCLUSION' THEN inclusion_count 
        WHEN 'EXCLUSION' THEN exclusion_count 
    END DESC;

