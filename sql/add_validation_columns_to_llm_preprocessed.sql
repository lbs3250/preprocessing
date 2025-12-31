-- outcome_llm_preprocessed 테이블에 검증 결과 컬럼 추가

ALTER TABLE outcome_llm_preprocessed
ADD COLUMN IF NOT EXISTS llm_validation_status VARCHAR(20),
ADD COLUMN IF NOT EXISTS llm_validation_confidence NUMERIC(3,2),
ADD COLUMN IF NOT EXISTS llm_validation_notes TEXT;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_outcome_llm_validation_status 
ON outcome_llm_preprocessed(llm_validation_status);

-- 코멘트 추가
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_status IS 'LLM 검증 상태: VERIFIED, UNCERTAIN, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_confidence IS 'LLM 검증 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_notes IS 'LLM 검증 노트';

