-- Inclusion Criteria Feature 분포
-- Inclusion Criteria에서 사용된 feature들의 빈도수와 비율

SELECT 
    feature,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage,
    COUNT(DISTINCT nct_id) as study_count
FROM (
    SELECT 
        iep.nct_id,
        jsonb_array_elements(iep.inclusion_criteria)::jsonb->>'feature' as feature
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.inclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.inclusion_criteria) = 'array'
      AND iep.inclusion_criteria != '[]'::jsonb
) inc_features
WHERE feature IS NOT NULL
GROUP BY feature
ORDER BY count DESC;

-- Exclusion Criteria Feature 분포
-- Exclusion Criteria에서 사용된 feature들의 빈도수와 비율

SELECT 
    feature,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage,
    COUNT(DISTINCT nct_id) as study_count
FROM (
    SELECT 
        iep.nct_id,
        jsonb_array_elements(iep.exclusion_criteria)::jsonb->>'feature' as feature
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.exclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.exclusion_criteria) = 'array'
      AND iep.exclusion_criteria != '[]'::jsonb
) exc_features
WHERE feature IS NOT NULL
GROUP BY feature
ORDER BY count DESC;

-- Inclusion과 Exclusion Feature 분포 비교 (통합)
-- Inclusion과 Exclusion에서 사용된 feature를 함께 비교

WITH inclusion_features AS (
    SELECT 
        'INCLUSION' as criteria_type,
        jsonb_array_elements(iep.inclusion_criteria)::jsonb->>'feature' as feature,
        iep.nct_id
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.inclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.inclusion_criteria) = 'array'
      AND iep.inclusion_criteria != '[]'::jsonb
),
exclusion_features AS (
    SELECT 
        'EXCLUSION' as criteria_type,
        jsonb_array_elements(iep.exclusion_criteria)::jsonb->>'feature' as feature,
        iep.nct_id
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.exclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.exclusion_criteria) = 'array'
      AND iep.exclusion_criteria != '[]'::jsonb
),
all_features AS (
    SELECT * FROM inclusion_features
    UNION ALL
    SELECT * FROM exclusion_features
)
SELECT 
    feature,
    COUNT(*) FILTER (WHERE criteria_type = 'INCLUSION') as inclusion_count,
    COUNT(*) FILTER (WHERE criteria_type = 'EXCLUSION') as exclusion_count,
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) FILTER (WHERE criteria_type = 'INCLUSION') as inclusion_study_count,
    COUNT(DISTINCT nct_id) FILTER (WHERE criteria_type = 'EXCLUSION') as exclusion_study_count,
    COUNT(DISTINCT nct_id) as total_study_count
FROM all_features
WHERE feature IS NOT NULL
GROUP BY feature
ORDER BY total_count DESC;

-- Top N Feature (Inclusion vs Exclusion 비교)
-- 가장 많이 사용된 상위 N개 feature의 Inclusion/Exclusion 비교

WITH inclusion_features AS (
    SELECT 
        'INCLUSION' as criteria_type,
        jsonb_array_elements(iep.inclusion_criteria)::jsonb->>'feature' as feature,
        iep.nct_id
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.inclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.inclusion_criteria) = 'array'
      AND iep.inclusion_criteria != '[]'::jsonb
),
exclusion_features AS (
    SELECT 
        'EXCLUSION' as criteria_type,
        jsonb_array_elements(iep.exclusion_criteria)::jsonb->>'feature' as feature,
        iep.nct_id
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
      AND iep.exclusion_criteria IS NOT NULL
      AND jsonb_typeof(iep.exclusion_criteria) = 'array'
      AND iep.exclusion_criteria != '[]'::jsonb
),
all_features AS (
    SELECT * FROM inclusion_features
    UNION ALL
    SELECT * FROM exclusion_features
),
feature_stats AS (
    SELECT 
        feature,
        COUNT(*) FILTER (WHERE criteria_type = 'INCLUSION') as inclusion_count,
        COUNT(*) FILTER (WHERE criteria_type = 'EXCLUSION') as exclusion_count,
        COUNT(*) as total_count
    FROM all_features
    WHERE feature IS NOT NULL
    GROUP BY feature
),
top_features AS (
    SELECT feature
    FROM feature_stats
    ORDER BY total_count DESC
    LIMIT 20  -- 상위 20개 feature
)
SELECT 
    tf.feature,
    COALESCE(fs.inclusion_count, 0) as inclusion_count,
    COALESCE(fs.exclusion_count, 0) as exclusion_count,
    COALESCE(fs.total_count, 0) as total_count,
    CASE 
        WHEN COALESCE(fs.inclusion_count, 0) + COALESCE(fs.exclusion_count, 0) > 0 
        THEN ROUND(COALESCE(fs.inclusion_count, 0) * 100.0 / (COALESCE(fs.inclusion_count, 0) + COALESCE(fs.exclusion_count, 0)), 2)
        ELSE 0 
    END as inclusion_percentage,
    CASE 
        WHEN COALESCE(fs.inclusion_count, 0) + COALESCE(fs.exclusion_count, 0) > 0 
        THEN ROUND(COALESCE(fs.exclusion_count, 0) * 100.0 / (COALESCE(fs.inclusion_count, 0) + COALESCE(fs.exclusion_count, 0)), 2)
        ELSE 0 
    END as exclusion_percentage
FROM top_features tf
LEFT JOIN feature_stats fs ON tf.feature = fs.feature
ORDER BY COALESCE(fs.total_count, 0) DESC;

-- Study별 Inclusion/Exclusion Feature 개수 통계
-- 각 study에서 사용된 inclusion/exclusion feature의 개수 분포

SELECT 
    'INCLUSION' as criteria_type,
    COUNT(*) FILTER (WHERE feature_count = 0) as zero_features,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 1 AND 5) as features_1_5,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 6 AND 10) as features_6_10,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 11 AND 20) as features_11_20,
    COUNT(*) FILTER (WHERE feature_count > 20) as features_over_20,
    AVG(feature_count) as avg_feature_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY feature_count) as median_feature_count,
    MAX(feature_count) as max_feature_count,
    COUNT(*) as total_studies
FROM (
    SELECT 
        iep.nct_id,
        CASE 
            WHEN iep.inclusion_criteria IS NULL OR jsonb_typeof(iep.inclusion_criteria) != 'array' THEN 0
            ELSE (SELECT COUNT(*) FROM jsonb_array_elements(iep.inclusion_criteria))
        END as feature_count
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
) inc_stats
UNION ALL
SELECT 
    'EXCLUSION' as criteria_type,
    COUNT(*) FILTER (WHERE feature_count = 0) as zero_features,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 1 AND 5) as features_1_5,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 6 AND 10) as features_6_10,
    COUNT(*) FILTER (WHERE feature_count BETWEEN 11 AND 20) as features_11_20,
    COUNT(*) FILTER (WHERE feature_count > 20) as features_over_20,
    AVG(feature_count) as avg_feature_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY feature_count) as median_feature_count,
    MAX(feature_count) as max_feature_count,
    COUNT(*) as total_studies
FROM (
    SELECT 
        iep.nct_id,
        CASE 
            WHEN iep.exclusion_criteria IS NULL OR jsonb_typeof(iep.exclusion_criteria) != 'array' THEN 0
            ELSE (SELECT COUNT(*) FROM jsonb_array_elements(iep.exclusion_criteria))
        END as feature_count
    FROM inclusion_exclusion_llm_preprocessed iep
    WHERE iep.llm_status = 'SUCCESS'
) exc_stats;

