-- ============================================================================
-- 기관별 실패율 높은 순 상위 50개 쿼리
-- ============================================================================
-- LEAD_SPONSOR별 정규화 실패율을 계산하여 실패율이 높은 순으로 50개 조회
-- ============================================================================

SELECT 
    sp.name_raw as sponsor_name,
    sp.class_raw as sponsor_class,
    COUNT(*) as total_outcomes,
    
    -- 실패 통계
    COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END) as failed_count,
    
    -- 실패율 (Outcome 기준)
    ROUND(COUNT(CASE WHEN n.failure_reason IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate_percent,
    
    -- 실패 유형별 분포
    COUNT(CASE WHEN n.failure_reason = 'MEASURE_CODE_FAILED' THEN 1 END) as measure_code_failed,
    COUNT(CASE WHEN n.failure_reason = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed,
    COUNT(CASE WHEN n.failure_reason = 'BOTH_FAILED' THEN 1 END) as both_failed,
    
    -- 성공 통계 (참고용)
    COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END) as success_count,
    ROUND(COUNT(CASE WHEN n.measure_code IS NOT NULL AND n.failure_reason IS NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
    
FROM outcome_normalized n
INNER JOIN study_party_raw sp ON n.nct_id = sp.nct_id
WHERE sp.party_type = 'LEAD_SPONSOR'
GROUP BY sp.name_raw, sp.class_raw
HAVING COUNT(*) >= 10  -- 최소 10건 이상인 기관만 표시
ORDER BY failure_rate_percent DESC, total_outcomes DESC
LIMIT 50;

