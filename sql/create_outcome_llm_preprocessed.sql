-- LLM 전처리 결과 저장용 테이블 생성
-- outcome_raw의 모든 데이터를 LLM으로 전처리한 결과를 저장

DROP TABLE IF EXISTS outcome_llm_preprocessed CASCADE;

CREATE TABLE outcome_llm_preprocessed (
    -- 원본 데이터 (outcome_raw에서 복사)
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    outcome_type VARCHAR(50) NOT NULL,
    outcome_order INTEGER NOT NULL,
    measure_raw TEXT,
    description_raw TEXT,
    time_frame_raw TEXT,
    phase VARCHAR(50),
    
    -- LLM 전처리 결과
    llm_measure_code VARCHAR(50),  -- LLM이 추출한 measure_code
    llm_time_value NUMERIC,        -- LLM이 추출한 time_value
    llm_time_unit VARCHAR(20),     -- LLM이 추출한 time_unit (weeks, months, days 등)
    llm_time_points JSONB,         -- 복수 시점인 경우 JSON 배열 [{"value": 1, "unit": "weeks"}, ...]
    
    -- 메타데이터
    llm_confidence NUMERIC(3,2),  -- LLM 신뢰도 (0.00 ~ 1.00)
    llm_notes TEXT,                -- LLM 처리 노트 (일관된 형식)
    parsing_method VARCHAR(20) DEFAULT 'LLM',  -- 파싱 방법 (LLM)
    llm_status VARCHAR(20),       -- LLM 처리 상태: SUCCESS, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED, API_FAILED, PARTIAL_RECOVERED
    failure_reason VARCHAR(50),   -- 실패 이유 (llm_status가 FAILED인 경우)
    
    -- 검증 결과 (LLM으로 검증한 결과)
    llm_validation_status VARCHAR(20),  -- 검증 상태: VERIFIED, UNCERTAIN, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED
    llm_validation_confidence NUMERIC(3,2),  -- 검증 신뢰도 (0.00 ~ 1.00)
    llm_validation_notes TEXT,  -- 검증 노트
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 원본 데이터와의 관계
    CONSTRAINT unique_outcome_llm UNIQUE (nct_id, outcome_type, outcome_order)
);

-- 인덱스 생성
CREATE INDEX idx_outcome_llm_nct_id ON outcome_llm_preprocessed(nct_id);
CREATE INDEX idx_outcome_llm_type ON outcome_llm_preprocessed(outcome_type);
CREATE INDEX idx_outcome_llm_measure_code ON outcome_llm_preprocessed(llm_measure_code);
CREATE INDEX idx_outcome_llm_time_value ON outcome_llm_preprocessed(llm_time_value, llm_time_unit);
CREATE INDEX idx_outcome_llm_phase ON outcome_llm_preprocessed(phase);
CREATE INDEX idx_outcome_llm_parsing_method ON outcome_llm_preprocessed(parsing_method);
CREATE INDEX idx_outcome_llm_status ON outcome_llm_preprocessed(llm_status);
CREATE INDEX idx_outcome_llm_failure_reason ON outcome_llm_preprocessed(failure_reason);
CREATE INDEX idx_outcome_llm_validation_status ON outcome_llm_preprocessed(llm_validation_status);

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_outcome_llm_preprocessed_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_outcome_llm_preprocessed_updated_at 
    BEFORE UPDATE ON outcome_llm_preprocessed 
    FOR EACH ROW 
    EXECUTE FUNCTION update_outcome_llm_preprocessed_updated_at();

-- 코멘트 추가
COMMENT ON TABLE outcome_llm_preprocessed IS 'LLM으로 전처리한 outcome 데이터 (outcome_raw 전체 데이터 처리)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_measure_code IS 'LLM이 추출한 measure_code (dic.csv 기반)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_time_value IS 'LLM이 추출한 time_value (최대값 또는 단일값)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_time_unit IS 'LLM이 추출한 time_unit (weeks, months, days, years, hours, minutes)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_time_points IS '복수 시점인 경우 JSON 배열 [{"value": 숫자, "unit": "단위"}, ...]';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_confidence IS 'LLM 처리 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_notes IS 'LLM 처리 노트 (형식: [CATEGORY] 설명. 상세내용)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_status IS 'LLM 처리 상태: SUCCESS, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED, API_FAILED, PARTIAL_RECOVERED';
COMMENT ON COLUMN outcome_llm_preprocessed.failure_reason IS '실패 이유 (llm_status가 FAILED인 경우)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_status IS 'LLM 검증 상태: VERIFIED, UNCERTAIN, MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_confidence IS 'LLM 검증 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN outcome_llm_preprocessed.llm_validation_notes IS 'LLM 검증 노트';
COMMENT ON COLUMN outcome_llm_preprocessed.parsing_method IS '파싱 방법 (LLM)';

