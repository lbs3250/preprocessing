-- 숫자형 Value를 가진 Feature 통계 (Inclusion/Exclusion/Total Top 100)
-- value가 숫자(int/float)이고 비교 연산자(>, <, >=, <=, =, !=)를 사용하는 항목

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
numeric_features AS (
    SELECT 
        nct_id,
        criteria_type,
        criterion->>'feature' as feature,
        criterion->>'operator' as operator,
        CASE 
            WHEN jsonb_typeof(criterion->'value') = 'number' 
            THEN (criterion->>'value')::numeric 
            ELSE NULL 
        END as value_numeric
    FROM all_expanded
    WHERE criterion->>'operator' IN ('>', '<', '>=', '<=', '=', '!=')
      AND criterion->>'feature' IS NOT NULL
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
        MIN(value_numeric) as min_value,
        MAX(value_numeric) as max_value,
        AVG(value_numeric) as avg_value,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value_numeric) as median_value,
        COUNT(DISTINCT operator) as operator_count,
        STRING_AGG(DISTINCT operator, ', ' ORDER BY operator) as operators_used
    FROM numeric_features
    WHERE feature IS NOT NULL AND value_numeric IS NOT NULL
    GROUP BY feature
)
SELECT 
    feature,
    inclusion_count,
    exclusion_count,
    total_count,
    inclusion_study_count,
    exclusion_study_count,
    total_study_count,
    min_value,
    max_value,
    ROUND(avg_value::numeric, 2) as avg_value,
    ROUND(median_value::numeric, 2) as median_value,
    operator_count,
    operators_used
FROM feature_stats
ORDER BY total_count DESC
LIMIT 100;
