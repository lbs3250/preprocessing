-- Inclusion/Exclusion 다중 검증 시스템을 위한 검증 이력 테이블 생성

CREATE TABLE IF NOT EXISTS inclusion_exclusion_llm_validation_history (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    validation_run INTEGER NOT NULL,
    validation_status VARCHAR(20),  -- VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED
    validation_confidence NUMERIC(3,2),
    validation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nct_id) REFERENCES inclusion_exclusion_llm_preprocessed(nct_id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_inclusion_exclusion_validation_history_nct_id 
ON inclusion_exclusion_llm_validation_history(nct_id);

CREATE INDEX IF NOT EXISTS idx_inclusion_exclusion_validation_history_status 
ON inclusion_exclusion_llm_validation_history(validation_status);

CREATE INDEX IF NOT EXISTS idx_inclusion_exclusion_validation_history_run 
ON inclusion_exclusion_llm_validation_history(nct_id, validation_run);

-- 코멘트 추가
COMMENT ON TABLE inclusion_exclusion_llm_validation_history IS 'LLM 검증 이력 (다중 검증 결과 저장)';
COMMENT ON COLUMN inclusion_exclusion_llm_validation_history.nct_id IS '검증 대상 study의 nct_id';
COMMENT ON COLUMN inclusion_exclusion_llm_validation_history.validation_run IS '검증 실행 횟수 (1, 2, 3, ...)';
COMMENT ON COLUMN inclusion_exclusion_llm_validation_history.validation_status IS '해당 검증 실행의 상태';
COMMENT ON COLUMN inclusion_exclusion_llm_validation_history.validation_confidence IS '해당 검증 실행의 신뢰도';

