-- ============================================
-- outcome_raw에 intervention_json 컬럼 추가
-- ============================================

-- 컬럼 추가
ALTER TABLE outcome_raw 
ADD COLUMN IF NOT EXISTS intervention_json JSONB;

-- JSONB 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_outcome_raw_intervention 
ON outcome_raw USING GIN (intervention_json);

-- 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'outcome_raw' 
AND column_name = 'intervention_json';

