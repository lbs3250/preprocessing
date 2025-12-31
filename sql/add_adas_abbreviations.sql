-- ADAS-Cog 관련 약어 추가
-- 기존 ADAS_COG 항목의 keywords에 추가 약어들을 포함하도록 업데이트

UPDATE outcome_measure_dict
SET keywords = keywords || ';adas-cog11;adas-cog-11;adas-cog11;adas-cog14;adas-cog-14;adas-cog14;adas-cog-13;adas-cog13;adas;adas-cog'
WHERE measure_code = 'ADAS_COG';

-- keywords에 추가된 약어들:
-- - adas-cog11, adas-cog-11 (ADAS-Cog11)
-- - adas-cog14, adas-cog-14 (ADAS-Cog14)
-- - adas-cog-13, adas-cog13 (ADAS-Cog-13)
-- - adas (ADAS)
-- - adas-cog (일반적인 약어)

-- ADAS-COG-숫자 형식도 커버하기 위해 정규식 패턴을 keywords에 추가할 수 없으므로,
-- 매칭 로직에서 처리하거나, 각 숫자별로 별도 항목을 만들 수 있습니다.
-- 하지만 일반적으로는 기존 ADAS_COG 항목으로 매칭되도록 keywords에 추가하는 것이 좋습니다.

-- 확인 쿼리
SELECT measure_code, canonical_name, abbreviation, keywords 
FROM outcome_measure_dict 
WHERE measure_code = 'ADAS_COG';


