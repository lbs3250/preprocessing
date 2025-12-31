-- Inclusion/Exclusion 원본 데이터 저장용 테이블 생성
-- ClinicalTrials.gov API에서 eligibilityCriteria를 수집하여 저장

DROP TABLE IF EXISTS inclusion_exclusion_raw CASCADE;

CREATE TABLE inclusion_exclusion_raw (
    id BIGSERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL,
    eligibility_criteria_raw TEXT,  -- 전체 eligibilityCriteria 텍스트
    phase VARCHAR(50),  -- Phase 정보 (예: "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA" 등)
    source_version VARCHAR(50),
    raw_json JSONB,  -- 원본 study JSON
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_inclusion_exclusion_raw UNIQUE (nct_id)
);

-- 인덱스 생성
CREATE INDEX idx_inclusion_exclusion_raw_nct_id ON inclusion_exclusion_raw(nct_id);
CREATE INDEX idx_inclusion_exclusion_raw_phase ON inclusion_exclusion_raw(phase);

-- 코멘트 추가
COMMENT ON TABLE inclusion_exclusion_raw IS 'Inclusion/Exclusion 원본 데이터 (ClinicalTrials.gov API에서 수집)';
COMMENT ON COLUMN inclusion_exclusion_raw.eligibility_criteria_raw IS '전체 eligibilityCriteria 텍스트 (Inclusion Criteria와 Exclusion Criteria 포함)';
COMMENT ON COLUMN inclusion_exclusion_raw.phase IS 'Phase 정보 (PHASE1, PHASE2, PHASE3, PHASE4, NA 등)';
COMMENT ON COLUMN inclusion_exclusion_raw.raw_json IS '원본 study JSON (전체)';
COMMENT ON COLUMN inclusion_exclusion_raw.source_version IS '데이터 소스 버전 (derivedSection.miscInfoModule.versionHolder)';

