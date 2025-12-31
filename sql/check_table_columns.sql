-- ============================================
-- outcome_normalized 테이블 컬럼 확인
-- ============================================

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'outcome_normalized'
ORDER BY ordinal_position;

