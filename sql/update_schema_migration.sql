-- ============================================
-- 기존 DB 스키마 업데이트 스크립트
-- ============================================
-- 기존 테이블이 있는 경우 컬럼 추가/수정
-- ============================================

-- 1. outcome_raw에 intervention_json 컬럼이 없으면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'outcome_raw' 
        AND column_name = 'intervention_json'
    ) THEN
        ALTER TABLE outcome_raw 
        ADD COLUMN intervention_json JSONB;
        
        -- JSONB 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_outcome_raw_intervention 
        ON outcome_raw USING GIN (intervention_json);
        
        RAISE NOTICE 'Added intervention_json column to outcome_raw';
    ELSE
        RAISE NOTICE 'intervention_json column already exists in outcome_raw';
    END IF;
END $$;

-- 2. intervention_raw 테이블이 있으면 삭제 (더 이상 사용하지 않음)
DROP TABLE IF EXISTS intervention_raw CASCADE;

-- 3. outcome_measure_dict에 typical_role 컬럼이 없으면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'outcome_measure_dict' 
        AND column_name = 'typical_role'
    ) THEN
        ALTER TABLE outcome_measure_dict 
        ADD COLUMN typical_role VARCHAR(50);
        
        RAISE NOTICE 'Added typical_role column to outcome_measure_dict';
    ELSE
        RAISE NOTICE 'typical_role column already exists in outcome_measure_dict';
    END IF;
END $$;

-- 4. outcome_normalized에 num_arms 컬럼이 없으면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'outcome_normalized' 
        AND column_name = 'num_arms'
    ) THEN
        ALTER TABLE outcome_normalized 
        ADD COLUMN num_arms INTEGER;
        
        RAISE NOTICE 'Added num_arms column to outcome_normalized';
    ELSE
        RAISE NOTICE 'num_arms column already exists in outcome_normalized';
    END IF;
END $$;

-- 5. outcome_normalized_success, outcome_normalized_failed 테이블이 있으면
--    num_arms 컬럼 추가 (LIKE로 생성된 경우 자동으로 포함되지만, 확인용)
DO $$
BEGIN
    -- outcome_normalized_success
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'outcome_normalized_success') THEN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'outcome_normalized_success' 
            AND column_name = 'num_arms'
        ) THEN
            ALTER TABLE outcome_normalized_success 
            ADD COLUMN num_arms INTEGER;
            
            RAISE NOTICE 'Added num_arms column to outcome_normalized_success';
        END IF;
    END IF;
    
    -- outcome_normalized_failed
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'outcome_normalized_failed') THEN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'outcome_normalized_failed' 
            AND column_name = 'num_arms'
        ) THEN
            ALTER TABLE outcome_normalized_failed 
            ADD COLUMN num_arms INTEGER;
            
            RAISE NOTICE 'Added num_arms column to outcome_normalized_failed';
        END IF;
    END IF;
END $$;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'Schema update completed!';
END $$;

