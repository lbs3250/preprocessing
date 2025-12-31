-- ============================================
-- Time Frame 패턴 분석 쿼리
-- ============================================
-- 
-- time_frame_raw의 패턴별로 어떻게 파싱되었는지 확인
-- ============================================

-- ============================================
-- 0. 파싱 결과별 원본 패턴 분석 (핵심)
-- ============================================

-- 0-1. timeFrame 패턴별 성공 빈도수 (파싱 성공한 경우)
-- 변환된 결과(time_value_main + time_unit_main)를 기준으로 그룹화
-- 같은 숫자+단위 조합은 하나로 집계됨
SELECT 
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_timepoints_count,
    STRING_AGG(DISTINCT time_frame_raw, ' | ' ORDER BY time_frame_raw) as sample_raw_texts
FROM outcome_normalized
WHERE time_value_main IS NOT NULL 
  AND time_unit_main IS NOT NULL
GROUP BY time_value_main, time_unit_main, change_from_baseline_flag
ORDER BY frequency DESC;

-- 0-2. 파싱 성공 케이스 중 time_points가 있는 경우
SELECT 
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    jsonb_array_length(time_points::jsonb) as timepoint_count,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT time_frame_raw, ' | ' ORDER BY time_frame_raw) as sample_raw_texts
FROM outcome_normalized
WHERE time_value_main IS NOT NULL 
  AND time_unit_main IS NOT NULL
  AND time_points IS NOT NULL
GROUP BY time_value_main, time_unit_main, change_from_baseline_flag, jsonb_array_length(time_points::jsonb)
ORDER BY frequency DESC;

-- 0-3. 파싱 성공 케이스 중 time_points가 없는 경우 (단일 시점만 추출)
SELECT 
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    STRING_AGG(DISTINCT time_frame_raw, ' | ' ORDER BY time_frame_raw) as sample_raw_texts
FROM outcome_normalized
WHERE time_value_main IS NOT NULL 
  AND time_unit_main IS NOT NULL
  AND time_points IS NULL
GROUP BY time_value_main, time_unit_main, change_from_baseline_flag
ORDER BY frequency DESC;

-- ============================================
-- 1. Time Frame 패턴별 분류 및 통계
-- ============================================

-- 1-1. Baseline 포함 패턴 분석
SELECT 
    'Baseline 포함' as pattern_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN change_from_baseline_flag = TRUE THEN 1 END) as baseline_flag_set,
    COUNT(CASE WHEN time_value_main IS NOT NULL THEN 1 END) as parsed_success,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_time_points
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%';

-- 1-2. "and" 구분자 패턴 (Baseline and Week N 등)
SELECT 
    'and 구분자 패턴' as pattern_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN time_value_main IS NOT NULL THEN 1 END) as parsed_success,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_time_points
FROM outcome_normalized
WHERE time_frame_raw ILIKE '% and %';

-- 1-3. 쉼표로 구분된 복수 시점 패턴
SELECT 
    '쉼표 구분 복수 시점' as pattern_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN time_value_main IS NOT NULL THEN 1 END) as parsed_success,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_time_points
FROM outcome_normalized
WHERE time_frame_raw ~ ',\s*(week|day|month|year)';

-- 1-4. 괄호 포함 패턴 (Baseline (Week 0) 등)
SELECT 
    '괄호 포함 패턴' as pattern_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN time_value_main IS NOT NULL THEN 1 END) as parsed_success,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_time_points
FROM outcome_normalized
WHERE time_frame_raw ~ '\(.*\)';

-- ============================================
-- 2. 패턴별 상세 샘플 데이터
-- ============================================

-- 2-1. Baseline and Week 패턴 샘플
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    CASE 
        WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN '파싱 성공'
        ELSE '파싱 실패'
    END as parse_status
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%' 
  AND time_frame_raw ILIKE '%week%'
  AND time_frame_raw ILIKE '%and%'
ORDER BY time_frame_raw
LIMIT 30;

-- 2-2. Baseline, 복수 시점 패턴 샘플
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    CASE 
        WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN '파싱 성공'
        ELSE '파싱 실패'
    END as parse_status
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%'
  AND time_frame_raw ~ ',\s*(week|day|month|year)'
ORDER BY time_frame_raw
LIMIT 30;

-- 2-3. 괄호 포함 패턴 샘플 (Baseline (Week 0) 등)
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    CASE 
        WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN '파싱 성공'
        ELSE '파싱 실패'
    END as parse_status
FROM outcome_normalized
WHERE time_frame_raw ~ '\(.*week.*\)|\(.*day.*\)|\(.*month.*\)|\(.*year.*\)'
ORDER BY time_frame_raw
LIMIT 30;

-- 2-4. 복수 시점이지만 time_points가 없는 케이스 (파싱 실패)
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    '파싱 실패 또는 단일 시점만 추출' as parse_status
FROM outcome_normalized
WHERE time_frame_raw ~ ',\s*(week|day|month|year)'
  AND (time_points IS NULL OR jsonb_array_length(time_points::jsonb) <= 1)
ORDER BY time_frame_raw
LIMIT 30;

-- ============================================
-- 3. 패턴별 파싱 성공률 분석
-- ============================================

-- 3-1. 주요 패턴별 파싱 성공률
SELECT 
    CASE 
        WHEN time_frame_raw ILIKE '%baseline%' AND time_frame_raw ILIKE '%and%' THEN 'Baseline and 시점'
        WHEN time_frame_raw ILIKE '%baseline%' AND time_frame_raw ~ ',\s*(week|day|month|year)' THEN 'Baseline, 복수시점'
        WHEN time_frame_raw ~ '\(.*week.*\)|\(.*day.*\)|\(.*month.*\)|\(.*year.*\)' THEN '괄호 포함 패턴'
        WHEN time_frame_raw ~ ',\s*(week|day|month|year)' THEN '쉼표 구분 복수시점'
        WHEN time_frame_raw ILIKE '%baseline%' THEN 'Baseline 포함 (기타)'
        ELSE '기타 패턴'
    END as pattern_category,
    COUNT(*) as total_count,
    COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as parsed_success,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_time_points,
    ROUND(COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as success_rate_percent
FROM outcome_normalized
WHERE time_frame_raw IS NOT NULL
GROUP BY pattern_category
ORDER BY total_count DESC;

-- 3-2. time_points 개수별 분포
SELECT 
    timepoint_count,
    total_count,
    unique_patterns
FROM (
    SELECT 
        CASE 
            WHEN time_points IS NULL THEN 'time_points 없음'
            WHEN jsonb_array_length(time_points::jsonb) = 1 THEN '단일 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 2 THEN '2개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 3 THEN '3개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 4 THEN '4개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 5 THEN '5개 시점'
            WHEN jsonb_array_length(time_points::jsonb) >= 6 THEN '6개 이상 시점'
        END as timepoint_count,
        COUNT(*) as total_count,
        COUNT(DISTINCT time_frame_raw) as unique_patterns
    FROM outcome_normalized
    GROUP BY 
        CASE 
            WHEN time_points IS NULL THEN 'time_points 없음'
            WHEN jsonb_array_length(time_points::jsonb) = 1 THEN '단일 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 2 THEN '2개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 3 THEN '3개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 4 THEN '4개 시점'
            WHEN jsonb_array_length(time_points::jsonb) = 5 THEN '5개 시점'
            WHEN jsonb_array_length(time_points::jsonb) >= 6 THEN '6개 이상 시점'
        END
) subquery
ORDER BY 
    CASE timepoint_count
        WHEN 'time_points 없음' THEN 0
        WHEN '단일 시점' THEN 1
        WHEN '2개 시점' THEN 2
        WHEN '3개 시점' THEN 3
        WHEN '4개 시점' THEN 4
        WHEN '5개 시점' THEN 5
        WHEN '6개 이상 시점' THEN 6
    END;

-- ============================================
-- 4. 문제가 있는 패턴 분석
-- ============================================

-- 4-1. Baseline이 time_points에 포함되지 않은 케이스
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    'Baseline이 time_points에 없음' as issue
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%'
  AND time_points IS NOT NULL
  AND time_points::text NOT ILIKE '%"value":\s*0%'
ORDER BY time_frame_raw
LIMIT 30;

-- 4-2. time_value_main과 time_points의 최대값이 다른 케이스
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    time_points::text as time_points_json,
    'time_value_main과 time_points 불일치' as issue
FROM outcome_normalized
WHERE time_points IS NOT NULL
  AND time_value_main IS NOT NULL
  AND (
    -- time_points에서 최대값 추출하여 비교
    (SELECT MAX((point->>'value')::numeric) 
     FROM jsonb_array_elements(time_points::jsonb) AS point) != time_value_main
  )
ORDER BY time_frame_raw
LIMIT 30;

-- 4-3. 복수 시점이지만 time_points에 일부만 포함된 케이스
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    time_points::text as time_points_json,
    jsonb_array_length(time_points::jsonb) as timepoint_count,
    '일부 시점만 추출됨' as issue
FROM outcome_normalized
WHERE time_frame_raw ~ ',\s*(week|day|month|year)'
  AND time_points IS NOT NULL
  AND (
    -- 원본에 있는 숫자 개수와 time_points 개수 비교 (대략적)
    (LENGTH(time_frame_raw) - LENGTH(REPLACE(time_frame_raw, ',', ''))) + 1 > jsonb_array_length(time_points::jsonb)
  )
ORDER BY time_frame_raw
LIMIT 30;

-- ============================================
-- 5. 패턴별 빈도수 분석
-- ============================================

-- 5-1. time_frame_raw 패턴별 빈도수 (Top 50)
SELECT 
    time_frame_raw,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL THEN 1 END) as parsed_success_count,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_timepoints_count,
    STRING_AGG(DISTINCT 
        CASE 
            WHEN time_value_main IS NOT NULL AND time_unit_main IS NOT NULL 
            THEN time_value_main::text || ' ' || time_unit_main
            ELSE '파싱 실패'
        END, 
        ' | '
    ) as parsed_values
FROM outcome_normalized
WHERE time_frame_raw IS NOT NULL
GROUP BY time_frame_raw
ORDER BY frequency DESC
LIMIT 50;

-- 5-2. Baseline 포함 패턴별 빈도수
SELECT 
    time_frame_raw,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(CASE WHEN change_from_baseline_flag = TRUE THEN 1 END) as baseline_flag_count,
    COUNT(CASE WHEN time_points IS NOT NULL THEN 1 END) as has_timepoints_count
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%'
GROUP BY time_frame_raw
ORDER BY frequency DESC
LIMIT 30;

-- ============================================
-- 6. 파싱 결과 검증
-- ============================================

-- 6-1. time_points에 Baseline(0)이 포함되어야 하는데 없는 케이스
SELECT 
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_points::text as time_points_json,
    'Baseline(0) 누락' as validation_issue
FROM outcome_normalized
WHERE time_frame_raw ILIKE '%baseline%'
  AND time_frame_raw ILIKE '%0%'
  AND time_points IS NOT NULL
  AND time_points::text NOT ILIKE '%"value":\s*0%'
ORDER BY time_frame_raw
LIMIT 20;

-- 6-2. time_value_main이 time_points의 최대값과 일치하는지 확인
SELECT 
    CASE 
        WHEN time_value_main = (
            SELECT MAX((point->>'value')::numeric) 
            FROM jsonb_array_elements(time_points::jsonb) AS point
        ) THEN '일치'
        ELSE '불일치'
    END as value_match_status,
    COUNT(*) as count
FROM outcome_normalized
WHERE time_points IS NOT NULL
  AND time_value_main IS NOT NULL
GROUP BY value_match_status;

-- 6-3. time_unit_main이 time_points의 단위와 일치하는지 확인
SELECT 
    CASE 
        WHEN time_unit_main = (
            SELECT point->>'unit'
            FROM jsonb_array_elements(time_points::jsonb) AS point
            ORDER BY (point->>'value')::numeric DESC
            LIMIT 1
        ) THEN '일치'
        ELSE '불일치'
    END as unit_match_status,
    COUNT(*) as count
FROM outcome_normalized
WHERE time_points IS NOT NULL
  AND time_unit_main IS NOT NULL
GROUP BY unit_match_status;

-- ============================================
-- 7. time_points가 있는 모든 레코드 조회
-- ============================================

-- 7-1. time_points가 비어있지 않은 모든 레코드 (time_points distinct)
SELECT DISTINCT ON (time_points)
    nct_id,
    outcome_type,
    outcome_order,
    time_frame_raw,
    time_value_main,
    time_unit_main,
    change_from_baseline_flag,
    time_phase,
    time_points::text as time_points_json,
    jsonb_array_length(time_points::jsonb) as timepoint_count,
    measure_raw,
    measure_code,
    failure_reason
FROM outcome_normalized
WHERE time_points IS NOT NULL
ORDER BY time_points, nct_id, outcome_type, outcome_order;
-- DISTINCT ON (time_points) - 같은 time_points 값은 하나만 표시

-- 7-2. time_points가 있는 레코드 통계
SELECT 
    COUNT(*) as total_count,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT time_frame_raw) as unique_patterns,
    AVG(jsonb_array_length(time_points::jsonb)) as avg_timepoint_count,
    MIN(jsonb_array_length(time_points::jsonb)) as min_timepoint_count,
    MAX(jsonb_array_length(time_points::jsonb)) as max_timepoint_count
FROM outcome_normalized
WHERE time_points IS NOT NULL;

-- 7-3. time_points 개수별 상세 통계
SELECT 
    jsonb_array_length(time_points::jsonb) as timepoint_count,
    COUNT(*) as frequency,
    COUNT(DISTINCT nct_id) as study_count,
    COUNT(DISTINCT time_frame_raw) as unique_patterns
FROM outcome_normalized
WHERE time_points IS NOT NULL
GROUP BY jsonb_array_length(time_points::jsonb)
ORDER BY timepoint_count;

