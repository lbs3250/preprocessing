-- 재전처리 완료된 항목의 검증 상태 초기화 쿼리
-- updated_at이 2026-01-02인 항목 (재전처리 완료된 항목)

-- 1. 통계 확인
SELECT 
    COUNT(*) as total_reprocessed,
    COUNT(*) FILTER (WHERE llm_validation_status IS NOT NULL) as with_validation_status,
    COUNT(*) FILTER (WHERE validation_consistency_score IS NOT NULL) as with_consistency_score,
    COUNT(*) FILTER (WHERE needs_manual_review IS NOT NULL) as with_manual_review
FROM inclusion_exclusion_llm_preprocessed
WHERE llm_status = 'SUCCESS'
  AND DATE(updated_at) = '2026-01-02';

-- 2. 검증 상태 초기화 (실행 전 위 쿼리로 확인 후 실행)
UPDATE inclusion_exclusion_llm_preprocessed
SET 
    llm_validation_status = NULL,
    llm_validation_confidence = NULL,
    llm_validation_notes = NULL,
    validation_consistency_score = NULL,
    validation_count = NULL,
    needs_manual_review = NULL,
    avg_validation_confidence = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE llm_status = 'SUCCESS'
  AND DATE(updated_at) = '2026-01-02'
  AND llm_validation_status IS NOT NULL;

-- 3. 검증 이력 삭제 (선택사항)
DELETE FROM inclusion_exclusion_llm_validation_history
WHERE nct_id IN (
    SELECT nct_id
    FROM inclusion_exclusion_llm_preprocessed
    WHERE llm_status = 'SUCCESS'
      AND DATE(updated_at) = '2026-01-02'
);

-- 4. llm_notes 기준으로 찾는 방법 (대안)
-- updated_at 대신 llm_notes에 '[REPROCESS]' 또는 '재전처리'가 포함된 경우
UPDATE inclusion_exclusion_llm_preprocessed
SET 
    llm_validation_status = NULL,
    llm_validation_confidence = NULL,
    llm_validation_notes = NULL,
    validation_consistency_score = NULL,
    validation_count = NULL,
    needs_manual_review = NULL,
    avg_validation_confidence = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE llm_status = 'SUCCESS'
  AND (llm_notes LIKE '%[REPROCESS]%' OR llm_notes LIKE '%재전처리%')
  AND llm_validation_status IS NOT NULL;

-- 5. 특정 시간 범위로 찾는 방법 (시간까지 포함하려면)
-- 예: 2026-01-02 00:00:00 ~ 2026-01-02 23:59:59
UPDATE inclusion_exclusion_llm_preprocessed
SET 
    llm_validation_status = NULL,
    llm_validation_confidence = NULL,
    llm_validation_notes = NULL,
    validation_consistency_score = NULL,
    validation_count = NULL,
    needs_manual_review = NULL,
    avg_validation_confidence = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE llm_status = 'SUCCESS'
  AND updated_at >= '2026-01-02 00:00:00'
  AND updated_at < '2026-01-03 00:00:00'
  AND llm_validation_status IS NOT NULL;

