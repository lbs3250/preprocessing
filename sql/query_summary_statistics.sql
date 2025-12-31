-- ============================================================================
-- 전체 통계 요약 쿼리
-- ============================================================================

-- ============================================================================
-- 1. 총 데이터수 대비 성공/실패 통계
-- ============================================================================
SELECT 
    -- 총 데이터 수
    COUNT(*) as total_outcomes,
    
    -- Outcome 성공/실패 (measure_code 기준)
    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END) as outcome_success_count,
    COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END) as outcome_failed_count,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as outcome_success_rate_percent,
    ROUND(COUNT(CASE WHEN failure_reason = 'MEASURE_CODE_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END)::numeric / COUNT(*) * 100, 2) as outcome_failure_rate_percent,
    
    -- Timeframe 성공/실패
    COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as timeframe_success_count,
    COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END) as timeframe_failed_count,
    ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_success_rate_percent,
    ROUND(COUNT(CASE WHEN failure_reason = 'TIMEFRAME_FAILED' OR failure_reason = 'BOTH_FAILED' THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_failure_rate_percent,
    
    -- 전체 성공 (둘 다 성공)
    COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
               AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as both_success_count,
    ROUND(COUNT(CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                     AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as both_success_rate_percent,
    
    -- 총 NCT ID 수
    COUNT(DISTINCT nct_id) as total_nct_id_count,
    
    -- Outcome 성공한 NCT ID 수 (distinct)
    COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN nct_id END) as outcome_success_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as outcome_success_nct_id_rate_percent,
    
    -- Timeframe 성공한 NCT ID 수 (distinct)
    COUNT(DISTINCT CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END) as timeframe_success_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as timeframe_success_nct_id_rate_percent,
    
    -- 둘 다 성공한 NCT ID 수 (distinct)
    COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                        AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END) as both_success_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN measure_code IS NOT NULL AND failure_reason IS NULL 
                              AND time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN nct_id END)::numeric / COUNT(DISTINCT nct_id) * 100, 2) as both_success_nct_id_rate_percent
    
FROM outcome_normalized;

-- ============================================================================
-- 2. 누락 필드 비율 (Outcome 기준)
-- ============================================================================
SELECT 
    COUNT(*) as total_outcomes,
    
    -- Timeframe 누락
    COUNT(CASE WHEN time_frame_raw IS NULL OR time_frame_raw = '' THEN 1 END) as timeframe_null_count,
    ROUND(COUNT(CASE WHEN time_frame_raw IS NULL OR time_frame_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_null_rate_percent,
    
    -- Measure_raw 누락
    COUNT(CASE WHEN measure_raw IS NULL OR measure_raw = '' THEN 1 END) as measure_raw_null_count,
    ROUND(COUNT(CASE WHEN measure_raw IS NULL OR measure_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_raw_null_rate_percent,
    
    -- Description_raw 누락
    COUNT(CASE WHEN description_raw IS NULL OR description_raw = '' THEN 1 END) as description_raw_null_count,
    ROUND(COUNT(CASE WHEN description_raw IS NULL OR description_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as description_raw_null_rate_percent,
    
    -- Phase 누락 (NA 포함)
    COUNT(CASE WHEN phase IS NULL OR phase = 'NA' THEN 1 END) as phase_null_or_na_count,
    ROUND(COUNT(CASE WHEN phase IS NULL OR phase = 'NA' THEN 1 END)::numeric / COUNT(*) * 100, 2) as phase_null_or_na_rate_percent,
    
    -- Sponsor 누락 (study_party_raw 조인 필요)
    COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END) as sponsor_null_count,
    ROUND(COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as sponsor_null_rate_percent,
    
    -- LEAD_SPONSOR 누락
    COUNT(CASE WHEN sp_lead.nct_id IS NULL THEN 1 END) as lead_sponsor_null_count,
    ROUND(COUNT(CASE WHEN sp_lead.nct_id IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as lead_sponsor_null_rate_percent,
    
    -- Measure_clean 누락
    COUNT(CASE WHEN measure_clean IS NULL OR measure_clean = '' THEN 1 END) as measure_clean_null_count,
    ROUND(COUNT(CASE WHEN measure_clean IS NULL OR measure_clean = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_clean_null_rate_percent,
    
    -- Measure_abbreviation 누락
    COUNT(CASE WHEN measure_abbreviation IS NULL OR measure_abbreviation = '' THEN 1 END) as measure_abbreviation_null_count,
    ROUND(COUNT(CASE WHEN measure_abbreviation IS NULL OR measure_abbreviation = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_abbreviation_null_rate_percent,
    
    -- Time_value_main 누락
    COUNT(CASE WHEN time_value_main IS NULL THEN 1 END) as time_value_main_null_count,
    ROUND(COUNT(CASE WHEN time_value_main IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as time_value_main_null_rate_percent,
    
    -- Time_unit_main 누락
    COUNT(CASE WHEN time_unit_main IS NULL THEN 1 END) as time_unit_main_null_count,
    ROUND(COUNT(CASE WHEN time_unit_main IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as time_unit_main_null_rate_percent
    
FROM outcome_normalized n
LEFT JOIN study_party_raw sp ON n.nct_id = sp.nct_id AND sp.party_type = 'ORGANIZATION'
LEFT JOIN study_party_raw sp_lead ON n.nct_id = sp_lead.nct_id AND sp_lead.party_type = 'LEAD_SPONSOR';

-- ============================================================================
-- 2-1. 누락 필드 비율 상세 (Phase별, Outcome Type별)
-- ============================================================================
SELECT 
    COALESCE(n.phase, 'NA') as phase,
    n.outcome_type,
    COUNT(*) as total_outcomes,
    
    -- Timeframe 누락
    COUNT(CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN 1 END) as timeframe_null_count,
    ROUND(COUNT(CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as timeframe_null_rate_percent,
    
    -- Measure_raw 누락
    COUNT(CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN 1 END) as measure_raw_null_count,
    ROUND(COUNT(CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as measure_raw_null_rate_percent,
    
    -- Description_raw 누락
    COUNT(CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN 1 END) as description_raw_null_count,
    ROUND(COUNT(CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN 1 END)::numeric / COUNT(*) * 100, 2) as description_raw_null_rate_percent,
    
    -- Phase 누락
    COUNT(CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN 1 END) as phase_null_or_na_count,
    ROUND(COUNT(CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN 1 END)::numeric / COUNT(*) * 100, 2) as phase_null_or_na_rate_percent,
    
    -- LEAD_SPONSOR 누락
    COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END) as lead_sponsor_null_count,
    ROUND(COUNT(CASE WHEN sp.nct_id IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as lead_sponsor_null_rate_percent
    
FROM outcome_normalized n
LEFT JOIN study_party_raw sp ON n.nct_id = sp.nct_id AND sp.party_type = 'LEAD_SPONSOR'
GROUP BY COALESCE(n.phase, 'NA'), n.outcome_type
ORDER BY COALESCE(n.phase, 'NA'), n.outcome_type;

-- ============================================================================
-- 2-2. 누락 필드 비율 (NCT ID 기준 - Study 단위)
-- ============================================================================
SELECT 
    COUNT(DISTINCT n.nct_id) as total_nct_id_count,
    
    -- Timeframe 누락이 있는 Study 수
    COUNT(DISTINCT CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN n.nct_id END) as timeframe_null_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN n.time_frame_raw IS NULL OR n.time_frame_raw = '' THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as timeframe_null_nct_id_rate_percent,
    
    -- Measure_raw 누락이 있는 Study 수
    COUNT(DISTINCT CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN n.nct_id END) as measure_raw_null_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN n.measure_raw IS NULL OR n.measure_raw = '' THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as measure_raw_null_nct_id_rate_percent,
    
    -- Description_raw 누락이 있는 Study 수
    COUNT(DISTINCT CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN n.nct_id END) as description_raw_null_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN n.description_raw IS NULL OR n.description_raw = '' THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as description_raw_null_nct_id_rate_percent,
    
    -- Phase 누락이 있는 Study 수
    COUNT(DISTINCT CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN n.nct_id END) as phase_null_or_na_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN n.phase IS NULL OR n.phase = 'NA' THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as phase_null_or_na_nct_id_rate_percent,
    
    -- LEAD_SPONSOR 누락이 있는 Study 수
    COUNT(DISTINCT CASE WHEN sp.nct_id IS NULL THEN n.nct_id END) as lead_sponsor_null_nct_id_count,
    ROUND(COUNT(DISTINCT CASE WHEN sp.nct_id IS NULL THEN n.nct_id END)::numeric / COUNT(DISTINCT n.nct_id) * 100, 2) as lead_sponsor_null_nct_id_rate_percent
    
FROM outcome_normalized n
LEFT JOIN study_party_raw sp ON n.nct_id = sp.nct_id AND sp.party_type = 'LEAD_SPONSOR';


