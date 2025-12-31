-- ============================================================================
-- 정규화 결과 조회 쿼리 (패턴 기반 빈도수)
-- ============================================================================
-- 성공 기준: time frame 파싱 성공 (measure 약어 추출은 선택사항)
-- ============================================================================

-- ============================================================================
-- 0. 패턴 총합 통계
-- ============================================================================
SELECT 
    구분,
    패턴수,
    총빈도수,
    총Study수
FROM (
    -- 전체 패턴 수
    SELECT 
        '전체' as 구분,
        COUNT(DISTINCT (time_value_main, time_unit_main, change_from_baseline_flag)) as 패턴수,
        COUNT(*) as 총빈도수,
        COUNT(DISTINCT nct_id) as 총Study수,
        0 as sort_order
    FROM outcome_normalized_success
    WHERE time_value_main IS NOT NULL 
      AND time_unit_main IS NOT NULL

    UNION ALL

    -- 단위별 패턴 수
    SELECT 
        time_unit_main as 구분,
        COUNT(DISTINCT (time_value_main, time_unit_main, change_from_baseline_flag)) as 패턴수,
        COUNT(*) as 총빈도수,
        COUNT(DISTINCT nct_id) as 총Study수,
        1 as sort_order
    FROM outcome_normalized_success
    WHERE time_value_main IS NOT NULL 
      AND time_unit_main IS NOT NULL
    GROUP BY time_unit_main
) t
ORDER BY sort_order, 총빈도수 DESC;

-- ============================================================================
-- 1. timeFrame 패턴별 성공 빈도수 (time frame 파싱 성공)
-- ============================================================================
-- 변환된 결과(time_value_main + time_unit_main)를 기준으로 그룹화
-- 같은 숫자+단위 조합은 하나로 집계됨 (예: "26 weeks", "26 weeks ", "26weeks" 모두 동일하게 카운트)
SELECT 
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT time_frame_raw, ' | ' ORDER BY time_frame_raw) as sample_raw_texts
FROM outcome_normalized_success
WHERE time_value_main IS NOT NULL 
  AND time_unit_main IS NOT NULL
  AND measure_abbreviation IS NOT NULL
GROUP BY time_value_main, time_unit_main, change_from_baseline_flag
ORDER BY frequency DESC;

