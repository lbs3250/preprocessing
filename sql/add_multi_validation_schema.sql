-- 다중 검증 시스템을 위한 스키마 확장

-- 1. 검증 이력 테이블 생성
CREATE TABLE IF NOT EXISTS outcome_llm_validation_history (
    id SERIAL PRIMARY KEY,
    outcome_id INTEGER NOT NULL,
    validation_run INTEGER NOT NULL,
    validation_status VARCHAR(20),
    validation_confidence NUMERIC(3,2),
    validation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outcome_id) REFERENCES outcome_llm_preprocessed(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_validation_history_outcome_id 
ON outcome_llm_validation_history(outcome_id);

CREATE INDEX IF NOT EXISTS idx_validation_history_status 
ON outcome_llm_validation_history(validation_status);

-- 2. outcome_llm_preprocessed 테이블에 컬럼 추가
ALTER TABLE outcome_llm_preprocessed
ADD COLUMN IF NOT EXISTS validation_consistency_score NUMERIC(3,2),
ADD COLUMN IF NOT EXISTS validation_count INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS needs_manual_review BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS revalidation_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_validation_confidence NUMERIC(3,2);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_outcome_llm_consistency_score 
ON outcome_llm_preprocessed(validation_consistency_score);

CREATE INDEX IF NOT EXISTS idx_outcome_llm_needs_review 
ON outcome_llm_preprocessed(needs_manual_review);

-- 코멘트 추가
COMMENT ON TABLE outcome_llm_validation_history IS 'LLM 검증 이력 (다중 검증 결과 저장)';
COMMENT ON COLUMN outcome_llm_validation_history.outcome_id IS '검증 대상 outcome ID';
COMMENT ON COLUMN outcome_llm_validation_history.validation_run IS '검증 실행 횟수 (1, 2, 3, ...)';
COMMENT ON COLUMN outcome_llm_validation_history.validation_status IS '해당 검증 실행의 상태';
COMMENT ON COLUMN outcome_llm_validation_history.validation_confidence IS '해당 검증 실행의 신뢰도';

COMMENT ON COLUMN outcome_llm_preprocessed.validation_consistency_score IS '검증 일관성 점수 (0.00 ~ 1.00): 동일한 결과가 나온 비율';
COMMENT ON COLUMN outcome_llm_preprocessed.validation_count IS '검증 실행 횟수';
COMMENT ON COLUMN outcome_llm_preprocessed.needs_manual_review IS '수동 검토 필요 여부';
COMMENT ON COLUMN outcome_llm_preprocessed.revalidation_count IS '재검증 횟수';
COMMENT ON COLUMN outcome_llm_preprocessed.avg_validation_confidence IS '평균 검증 신뢰도';

