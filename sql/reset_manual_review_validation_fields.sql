-- manual_review가 필요한 항목들의 llm_validation 관련 필드 초기화
-- 재검증을 위해 검증 관련 필드들을 NULL로 리셋

-- outcome_llm_preprocessed 테이블의 검증 필드 초기화
UPDATE outcome_llm_preprocessed
SET 
    llm_validation_status = NULL,
    llm_validation_confidence = NULL,
    llm_validation_notes = NULL,
    validation_consistency_score = NULL,
    validation_count = NULL,
    needs_manual_review = FALSE,  -- 초기화 후 다시 검증하므로 FALSE로 설정
    avg_validation_confidence = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE needs_manual_review = TRUE;

-- 검증 이력도 삭제 (선택사항 - 필요시 주석 해제)
-- DELETE FROM outcome_llm_validation_history
-- WHERE outcome_id IN (
--     SELECT id FROM outcome_llm_preprocessed WHERE needs_manual_review = TRUE
-- );

-- 결과 확인
SELECT 
    COUNT(*) as reset_count,
    COUNT(*) FILTER (WHERE llm_validation_status IS NULL) as status_null_count,
    COUNT(*) FILTER (WHERE llm_validation_confidence IS NULL) as confidence_null_count,
    COUNT(*) FILTER (WHERE llm_validation_notes IS NULL) as notes_null_count,
    COUNT(*) FILTER (WHERE validation_consistency_score IS NULL) as consistency_null_count,
    COUNT(*) FILTER (WHERE validation_count IS NULL) as count_null_count,
    COUNT(*) FILTER (WHERE needs_manual_review = FALSE) as review_false_count
FROM outcome_llm_preprocessed
WHERE llm_validation_status IS NULL 
  AND llm_validation_confidence IS NULL
  AND llm_validation_notes IS NULL;

