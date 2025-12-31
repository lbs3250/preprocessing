-- ============================================
-- ClinicalTrials.gov Outcomes 정규화 스키마
-- PostgreSQL DDL
-- ============================================

-- 기존 테이블 삭제 (있는 경우)
DROP TABLE IF EXISTS outcome_normalized CASCADE;
DROP TABLE IF EXISTS outcome_raw CASCADE;
DROP TABLE IF EXISTS study_party_raw CASCADE;
DROP TABLE IF EXISTS outcome_measure_dict CASCADE;

-- 함수 삭제 (있는 경우)
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- 1. outcome_raw: 원본 outcomes 보존용 테이블
CREATE TABLE outcome_raw (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    outcome_type VARCHAR(10) NOT NULL CHECK (outcome_type IN ('PRIMARY', 'SECONDARY')),
    outcome_order INTEGER NOT NULL,
    measure_raw TEXT,
    description_raw TEXT,
    time_frame_raw TEXT,
    phase VARCHAR(50),  -- Phase 정보 (예: "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA" 등)
    source_version VARCHAR(50),
    raw_json JSONB,  -- 원본 outcome JSON
    intervention_json JSONB,  -- 해당 study의 intervention 정보 (원본 JSON 배열)
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_outcome_raw UNIQUE (nct_id, outcome_type, outcome_order)
);

CREATE INDEX idx_outcome_raw_nct_id ON outcome_raw(nct_id);
CREATE INDEX idx_outcome_raw_type ON outcome_raw(outcome_type);
CREATE INDEX idx_outcome_raw_phase ON outcome_raw(phase);
CREATE INDEX idx_outcome_raw_intervention ON outcome_raw USING GIN (intervention_json);  -- JSONB 인덱스

-- 2. outcome_measure_dict: Measure 사전 테이블 (외래키 참조를 위해 먼저 생성)
CREATE TABLE outcome_measure_dict (
    measure_code VARCHAR(50) PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    abbreviation VARCHAR(100),
    keywords TEXT,  -- 세미콜론으로 구분된 키워드 리스트
    domain VARCHAR(100),
    typical_role VARCHAR(50),  -- PRIMARY, SECONDARY, BOTH, SUPPORTIVE 등
    unit_type VARCHAR(50),  -- (선택적, 나중에 추가 가능)
    score_direction VARCHAR(100),  -- "Higher = worse", "Higher = better" 등 (선택적, 나중에 추가 가능)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_measure_dict_domain ON outcome_measure_dict(domain);
CREATE INDEX idx_measure_dict_abbreviation ON outcome_measure_dict(abbreviation);

-- 3. outcome_normalized: 정규화된 outcomes 테이블 (outcome_measure_dict 참조)
CREATE TABLE outcome_normalized (
    outcome_id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    outcome_type VARCHAR(10) NOT NULL CHECK (outcome_type IN ('PRIMARY', 'SECONDARY')),
    outcome_order INTEGER NOT NULL,
    measure_raw TEXT,
    measure_clean TEXT,
    measure_abbreviation TEXT,        -- 괄호 안 약어 추출 결과
    measure_norm VARCHAR(200),
    measure_code VARCHAR(50),
    match_type VARCHAR(20),              -- 매칭 타입: 'MEASURE_CODE', 'ABBREVIATION', 'KEYWORD', 'CANONICAL_NAME'
    match_keyword TEXT,                   -- 매칭에 사용된 키워드/텍스트
    domain VARCHAR(100),
    time_frame_raw TEXT,
    time_value_main NUMERIC,
    time_unit_main VARCHAR(20),
    time_points JSONB,
    time_phase VARCHAR(50),
    phase VARCHAR(50),  -- Phase 정보 (예: "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA" 등)
    change_from_baseline_flag BOOLEAN DEFAULT FALSE,
    description_raw TEXT,
    description_norm TEXT,
    failure_reason VARCHAR(50),      -- 실패 원인: 'MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED', NULL(성공)
    parsing_method VARCHAR(20) DEFAULT 'RULE_BASED' CHECK (parsing_method IN ('RULE_BASED', 'LLM')),  -- 파싱 방법 구분
    num_arms INTEGER,
    pattern_code VARCHAR(20),        -- Timeframe 정규화 패턴 코드 (PATTERN1, PATTERN2 등)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_outcome_normalized_measure 
        FOREIGN KEY (measure_code) 
        REFERENCES outcome_measure_dict(measure_code) 
        ON DELETE SET NULL
);

CREATE INDEX idx_outcome_normalized_nct_id ON outcome_normalized(nct_id);
CREATE INDEX idx_outcome_normalized_type ON outcome_normalized(outcome_type);
CREATE INDEX idx_outcome_normalized_measure_code ON outcome_normalized(measure_code);
CREATE INDEX idx_outcome_normalized_domain ON outcome_normalized(domain);
CREATE INDEX idx_outcome_normalized_time_value ON outcome_normalized(time_value_main, time_unit_main);
CREATE INDEX idx_outcome_normalized_parsing_method ON outcome_normalized(parsing_method);
CREATE INDEX idx_outcome_normalized_match_type ON outcome_normalized(match_type);
CREATE INDEX idx_outcome_normalized_phase ON outcome_normalized(phase);
CREATE INDEX idx_outcome_normalized_pattern_code ON outcome_normalized(pattern_code);

-- 4. study_party_raw: 기관/담당자/시설 정보 테이블
CREATE TABLE study_party_raw (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    party_type VARCHAR(20) NOT NULL CHECK (party_type IN (
        'LEAD_SPONSOR', 
        'ORGANIZATION', 
        'OFFICIAL'
    )),
    name_raw TEXT,
    affiliation_raw TEXT,
    role_raw VARCHAR(100),
    class_raw VARCHAR(50),
    location_raw JSONB,
    source_path TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_study_party_raw UNIQUE (nct_id, party_type, name_raw)
);

CREATE INDEX idx_study_party_raw_nct_id ON study_party_raw(nct_id);
CREATE INDEX idx_study_party_raw_type ON study_party_raw(party_type);

-- ============================================
-- 초기 사전 데이터
-- ============================================
-- dic.csv 파일을 사용하여 import_dictionary_from_csv.py 스크립트로 데이터를 import하세요
-- 예: python import_dictionary_from_csv.py

-- ============================================
-- 업데이트 트리거 (updated_at 자동 갱신)
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

CREATE TRIGGER update_outcome_normalized_updated_at 
    BEFORE UPDATE ON outcome_normalized 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outcome_measure_dict_updated_at 
    BEFORE UPDATE ON outcome_measure_dict 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

