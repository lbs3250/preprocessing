-- ============================================
-- 스키마 업데이트 스크립트
-- outcome_normalized 테이블에 measure_abbreviation, failure_reason 컬럼 추가
-- outcome_normalized_excluded 테이블 제거
-- parsing_method 컬럼 추가 (RULE_BASED / LLM 구분)
-- ============================================

-- 1. outcome_normalized 테이블에 컬럼 추가
-- measure_abbreviation 컬럼 추가 (이미 있으면 스킵)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'measure_abbreviation'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN measure_abbreviation TEXT;
        
        RAISE NOTICE 'measure_abbreviation 컬럼 추가 완료';
    ELSE
        RAISE NOTICE 'measure_abbreviation 컬럼이 이미 존재합니다';
    END IF;
END $$;

-- failure_reason 컬럼 추가 (이미 있으면 스킵)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'failure_reason'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN failure_reason VARCHAR(50);
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_outcome_normalized_failure_reason 
        ON outcome_normalized(failure_reason);
        
        RAISE NOTICE 'failure_reason 컬럼 추가 완료';
    ELSE
        RAISE NOTICE 'failure_reason 컬럼이 이미 존재합니다';
    END IF;
END $$;

-- parsing_method 컬럼 추가 (이미 있으면 스킵)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'parsing_method'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN parsing_method VARCHAR(20) DEFAULT 'RULE_BASED' 
        CHECK (parsing_method IN ('RULE_BASED', 'LLM'));
        
        -- 기존 데이터는 모두 RULE_BASED로 설정
        UPDATE outcome_normalized
        SET parsing_method = 'RULE_BASED'
        WHERE parsing_method IS NULL;
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_outcome_normalized_parsing_method 
        ON outcome_normalized(parsing_method);
        
        RAISE NOTICE 'parsing_method 컬럼 추가 완료';
    ELSE
        RAISE NOTICE 'parsing_method 컬럼이 이미 존재합니다';
    END IF;
END $$;

-- match_type, match_keyword 컬럼 추가 (이미 있으면 스킵)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'match_type'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN match_type VARCHAR(20) 
        CHECK (match_type IN ('MEASURE_CODE', 'ABBREVIATION', 'KEYWORD', 'CANONICAL_NAME'));
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_outcome_normalized_match_type 
        ON outcome_normalized(match_type);
        
        RAISE NOTICE 'match_type 컬럼 추가 완료';
    ELSE
        RAISE NOTICE 'match_type 컬럼이 이미 존재합니다';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'match_keyword'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN match_keyword TEXT;
        
        RAISE NOTICE 'match_keyword 컬럼 추가 완료';
    ELSE
        RAISE NOTICE 'match_keyword 컬럼이 이미 존재합니다';
    END IF;
END $$;

-- 2. outcome_normalized_excluded 테이블 제거 (더 이상 사용하지 않음)
DROP TABLE IF EXISTS outcome_normalized_excluded CASCADE;

-- 3. 기존 데이터가 있다면 failure_reason 업데이트
-- measure_abbreviation과 time_frame 파싱 결과를 기반으로 failure_reason 설정
UPDATE outcome_normalized
SET failure_reason = CASE
    WHEN measure_abbreviation IS NULL 
         AND (time_value_main IS NULL OR time_unit_main IS NULL) 
    THEN 'BOTH_FAILED'
    WHEN measure_abbreviation IS NULL 
    THEN 'MEASURE_FAILED'
    WHEN time_value_main IS NULL OR time_unit_main IS NULL 
    THEN 'TIMEFRAME_FAILED'
    ELSE NULL  -- 성공 케이스
END
WHERE failure_reason IS NULL;

-- 4. measure_abbreviation 업데이트 (기존 데이터가 있다면)
-- measure_raw에서 괄호 안 약어 추출
UPDATE outcome_normalized
SET measure_abbreviation = (
    SELECT (regexp_match(measure_raw, '\([A-Za-z][A-Za-z0-9\-+\s/]+\)'))[1]
)
WHERE measure_abbreviation IS NULL
  AND measure_raw IS NOT NULL
  AND measure_raw ~ '\([A-Za-z][A-Za-z0-9\-+\s/]+\)';

-- 5. 통계 확인
SELECT 
    '전체 데이터' as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
UNION ALL
SELECT 
    '성공 (failure_reason IS NULL)' as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
WHERE failure_reason IS NULL
UNION ALL
SELECT 
    'MEASURE_FAILED' as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
WHERE failure_reason = 'MEASURE_FAILED'
UNION ALL
SELECT 
    'TIMEFRAME_FAILED' as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
WHERE failure_reason = 'TIMEFRAME_FAILED'
UNION ALL
SELECT 
    'BOTH_FAILED' as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
WHERE failure_reason = 'BOTH_FAILED';

-- 6. parsing_method 통계 확인
SELECT 
    parsing_method as 구분,
    COUNT(*) as 건수
FROM outcome_normalized
GROUP BY parsing_method
ORDER BY parsing_method;

-- 7. match_type 통계 확인
SELECT 
    COALESCE(match_type, 'NULL') as 구분,
    COUNT(*) as 건수,
    COUNT(DISTINCT measure_code) as unique_measure_codes
FROM outcome_normalized
WHERE measure_code IS NOT NULL
GROUP BY match_type
ORDER BY match_type;



