-- LLM 전처리 결과 저장용 테이블 생성
-- inclusion_exclusion_raw의 모든 데이터를 LLM으로 전처리한 결과를 저장

DROP TABLE IF EXISTS inclusion_exclusion_llm_preprocessed CASCADE;

CREATE TABLE inclusion_exclusion_llm_preprocessed (
    -- 원본 데이터 (inclusion_exclusion_raw에서 복사)
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,  -- 원본 텍스트
    phase VARCHAR(50),
    
    -- LLM 전처리 결과: Inclusion Criteria (JSONB 배열)
    inclusion_criteria JSONB,  -- Inclusion 항목 배열
    
    -- LLM 전처리 결과: Exclusion Criteria (JSONB 배열)
    exclusion_criteria JSONB,  -- Exclusion 항목 배열
    
    -- 메타데이터
    llm_confidence NUMERIC(3,2),  -- LLM 신뢰도 (0.00 ~ 1.00)
    llm_notes TEXT,  -- LLM 처리 노트
    parsing_method VARCHAR(20) DEFAULT 'LLM',  -- 파싱 방법 (LLM)
    llm_status VARCHAR(20),  -- LLM 처리 상태: SUCCESS, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED, API_FAILED
    failure_reason VARCHAR(50),  -- 실패 이유 (llm_status가 FAILED인 경우)
    
    -- 검증 결과 (LLM으로 검증한 결과)
    llm_validation_status VARCHAR(20),  -- 검증 상태: VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED
    llm_validation_confidence NUMERIC(3,2),  -- 검증 신뢰도 (0.00 ~ 1.00)
    llm_validation_notes TEXT,  -- 검증 노트
    
    -- 다중 검증 관련 (검증 단계에서 추가)
    validation_consistency_score NUMERIC(3,2),  -- 검증 일관성 점수 (0.00 ~ 1.00)
    validation_count INTEGER,  -- 검증 실행 횟수
    needs_manual_review BOOLEAN,  -- 수동 검토 필요 여부
    avg_validation_confidence NUMERIC(3,2),  -- 평균 검증 신뢰도
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_inclusion_exclusion_llm UNIQUE (nct_id)
);

-- 인덱스 생성
CREATE INDEX idx_inclusion_exclusion_llm_nct_id ON inclusion_exclusion_llm_preprocessed(nct_id);
CREATE INDEX idx_inclusion_exclusion_llm_phase ON inclusion_exclusion_llm_preprocessed(phase);
CREATE INDEX idx_inclusion_exclusion_llm_status ON inclusion_exclusion_llm_preprocessed(llm_status);
CREATE INDEX idx_inclusion_exclusion_llm_validation_status ON inclusion_exclusion_llm_preprocessed(llm_validation_status);
CREATE INDEX idx_inclusion_exclusion_llm_inclusion ON inclusion_exclusion_llm_preprocessed USING GIN (inclusion_criteria);
CREATE INDEX idx_inclusion_exclusion_llm_exclusion ON inclusion_exclusion_llm_preprocessed USING GIN (exclusion_criteria);
CREATE INDEX idx_inclusion_exclusion_llm_consistency_score ON inclusion_exclusion_llm_preprocessed(validation_consistency_score);
CREATE INDEX idx_inclusion_exclusion_llm_needs_review ON inclusion_exclusion_llm_preprocessed(needs_manual_review);

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_inclusion_exclusion_llm_preprocessed_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_inclusion_exclusion_llm_preprocessed_updated_at 
    BEFORE UPDATE ON inclusion_exclusion_llm_preprocessed 
    FOR EACH ROW 
    EXECUTE FUNCTION update_inclusion_exclusion_llm_preprocessed_updated_at();

-- 코멘트 추가
COMMENT ON TABLE inclusion_exclusion_llm_preprocessed IS 'LLM으로 전처리한 Inclusion/Exclusion 데이터 (inclusion_exclusion_raw 전체 데이터 처리)';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.inclusion_criteria IS 'Inclusion 항목 배열 (JSONB): [{"criterion_id": 1, "feature": "AGE", "operator": ">=", "value": 50, ...}, ...]';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.exclusion_criteria IS 'Exclusion 항목 배열 (JSONB): [{"criterion_id": 1, "feature": "AGE", "operator": "<", "value": 50, ...}, ...]';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_confidence IS 'LLM 처리 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_notes IS 'LLM 처리 노트';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_status IS 'LLM 처리 상태: SUCCESS, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED, API_FAILED';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.failure_reason IS '실패 이유 (llm_status가 FAILED인 경우)';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_validation_status IS 'LLM 검증 상태: VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_validation_confidence IS 'LLM 검증 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.llm_validation_notes IS 'LLM 검증 노트';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.validation_consistency_score IS '검증 일관성 점수 (0.00 ~ 1.00): 동일한 결과가 나온 비율';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.validation_count IS '검증 실행 횟수';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.needs_manual_review IS '수동 검토 필요 여부';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.avg_validation_confidence IS '평균 검증 신뢰도';
COMMENT ON COLUMN inclusion_exclusion_llm_preprocessed.parsing_method IS '파싱 방법 (LLM)';

