-- ============================================================================
-- Phase 정보 추가를 위한 스키마 업데이트
-- ============================================================================

-- outcome_raw 테이블에 phase 컬럼 추가
ALTER TABLE outcome_raw 
ADD COLUMN IF NOT EXISTS phase VARCHAR(50);

-- outcome_normalized 테이블에 phase 컬럼 추가 (이미 있을 수 있지만 확인)
-- 참고: time_phase는 time_frame에서 추출한 phase 정보이고, 
-- phase는 study 레벨의 phase 정보입니다.
ALTER TABLE outcome_normalized 
ADD COLUMN IF NOT EXISTS phase VARCHAR(50);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_outcome_raw_phase ON outcome_raw(phase);
CREATE INDEX IF NOT EXISTS idx_outcome_normalized_phase ON outcome_normalized(phase);

