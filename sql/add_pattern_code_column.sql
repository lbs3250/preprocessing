-- ============================================
-- pattern_code 컬럼 추가 마이그레이션 스크립트
-- ============================================

-- outcome_normalized 테이블에 pattern_code 컬럼 추가
ALTER TABLE outcome_normalized 
ADD COLUMN IF NOT EXISTS pattern_code VARCHAR(20);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_outcome_normalized_pattern_code 
ON outcome_normalized(pattern_code);

-- outcome_normalized_success 테이블에 pattern_code 컬럼 추가 (이미 생성된 경우)
ALTER TABLE outcome_normalized_success 
ADD COLUMN IF NOT EXISTS pattern_code VARCHAR(20);

-- outcome_normalized_failed 테이블에 pattern_code 컬럼 추가 (이미 생성된 경우)
ALTER TABLE outcome_normalized_failed 
ADD COLUMN IF NOT EXISTS pattern_code VARCHAR(20);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_outcome_normalized_success_pattern_code 
ON outcome_normalized_success(pattern_code);

CREATE INDEX IF NOT EXISTS idx_outcome_normalized_failed_pattern_code 
ON outcome_normalized_failed(pattern_code);

COMMENT ON COLUMN outcome_normalized.pattern_code IS 'Timeframe 정규화 패턴 코드 (PATTERN1, PATTERN2 등)';
COMMENT ON COLUMN outcome_normalized_success.pattern_code IS 'Timeframe 정규화 패턴 코드 (PATTERN1, PATTERN2 등)';
COMMENT ON COLUMN outcome_normalized_failed.pattern_code IS 'Timeframe 정규화 패턴 코드 (PATTERN1, PATTERN2 등)';

-- 참고: separate_normalized_data.py를 다시 실행하면 자동으로 포함되지만,
-- 이미 생성된 테이블의 경우 위의 ALTER TABLE 문으로 수동 추가가 필요합니다.

