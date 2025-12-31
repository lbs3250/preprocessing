# 일일 작업 로그 (2025-01-24)

## 1. LLM 검증 고도화 및 검증 진행

### 작업 내용

- **다중 검증 시스템 구현**: LLM 검증의 non-deterministic 특성을 고려한 robust 검증 프로세스 구현
- **Majority Voting**: 3회 검증 후 가장 많이 나온 결과를 최종 상태로 결정
- **Consistency Score**: 동일한 결과가 나온 비율 계산 (0.00 ~ 1.00)
- **Confidence + Consistency 기반 필터링**:
  - Consistency ≥ 0.67 & Avg Confidence ≥ 0.80: 자동 수용
  - Consistency ≥ 0.67 & Avg Confidence 0.50~0.80: 추가 검증
  - Consistency < 0.67 또는 Avg Confidence < 0.50: 수동 검토
- **검증 이력 관리**: `outcome_llm_validation_history` 테이블에 개별 검증 실행 결과 저장
- **재검증 지원**: 기존 검증 이력과 새로운 검증 결과를 합쳐서 분석
- **배치 처리**: 전처리와 동일한 방식으로 배치 단위 검증 및 DB 업데이트 (100개 단위)

### 진행 상황

- **검증 진행률**: 약 1/3 정도 완료
- **제약사항**: API 토큰 제약으로 인해 전체 검증 완료하지 못함

### 관련 파일

- `llm/llm_validate_preprocessed_success.py`: 다중 검증 로직 구현
- `sql/add_multi_validation_schema.sql`: 검증 이력 테이블 및 스키마 확장
- `docs/llm_validation_reference_guide.md`: 검증 방법론 문서
- `docs/llm_validation_usage_guide.md`: 사용 가이드

---

## 2. Inclusion/Exclusion 데이터 수집 및 전처리 준비

### 작업 내용

#### 2.1 데이터 수집 스크립트 개발

- **`preprocessing/collect_inclusion_exclusion.py`**: ClinicalTrials.gov API에서 eligibilityCriteria 수집
- **Drug Only 필터 적용**:
  - API 필터: `AREA[InterventionType]Drug` (drug 포함된 study)
  - 추가 필터: `is_drug_only_study()` 함수로 drug만 단독으로 있는 study만 수집 (biomarker 등 제외)
- **NULL 처리**: eligibilityCriteria가 없는 경우도 수집하되 NULL로 저장
- **재수집 지원**: 수집 시작 전 기존 데이터 전체 삭제 후 재수집

#### 2.2 데이터베이스 스키마 구성

- **`sql/create_inclusion_exclusion_raw.sql`**: 원본 데이터 저장 테이블
  - `nct_id`, `eligibility_criteria_raw`, `phase`, `source_version`, `raw_json`
- **`sql/create_inclusion_exclusion_llm_preprocessed.sql`**: LLM 전처리 결과 테이블
  - `inclusion_criteria` (JSONB): Inclusion 항목 배열
  - `exclusion_criteria` (JSONB): Exclusion 항목 배열
  - LLM 메타데이터: `llm_confidence`, `llm_notes`, `llm_status`, `failure_reason`
  - 검증 메타데이터: `llm_validation_status`, `validation_consistency_score`, `validation_count`, `needs_manual_review` 등
- **`sql/create_inclusion_exclusion_validation_history.sql`**: 검증 이력 테이블
  - 개별 검증 실행 결과 저장 (다중 검증 지원)

#### 2.3 전처리 전략 수립

- **Feature-Operator-Value 패턴**:
  - Feature: AGE, GENDER, CONDITION, LAB_VALUE 등 카테고리
  - Operator: >=, <=, >, <, =, !=, BETWEEN, IN, PRESENT, ABSENT 등
  - Value: 숫자, 문자열, 배열, NULL
- **논리 연산자 지원**: AND/OR를 통한 복합 조건 처리
  - 단일 조건: `logic_operator: null`
  - 복합 조건: `logic_operator: "AND"` 또는 `"OR"`, `conditions: [...]`
- **유연한 구조**: 값이 없는 경우도 처리 (카테고리만 있는 경우)
- **JSONB 활용**: PostgreSQL JSONB 타입으로 복잡한 중첩 구조 저장

#### 2.4 LLM 프롬프트 개발

- **전처리 프롬프트**: `get_inclusion_exclusion_preprocess_prompt()`
  - Inclusion/Exclusion 분리
  - Feature 분류 규칙
  - Operator 추출 규칙
  - 논리 연산자 처리
- **검증 프롬프트**: `get_inclusion_exclusion_validation_prompt()`
  - 원본 텍스트와 전처리 결과 비교
  - 검증 상태: VERIFIED, UNCERTAIN, INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED

#### 2.5 전처리 및 검증 스크립트 준비

- **`llm/llm_preprocess_inclusion_exclusion.py`**: LLM 전처리 스크립트 (구현 완료, 실행 전)
  - 배치 처리 지원
  - API 키 로테이션
  - 재시작 기능 (`start_batch` 옵션)
  - 실패 항목 재처리 모드 (`--failed-only`, `--missing-only`, `--all`)
- **`llm/llm_validate_inclusion_exclusion.py`**: LLM 검증 스크립트 (구현 완료, 실행 전)
  - 다중 검증 (기본 3회)
  - Majority Voting
  - Consistency Score 계산
  - 배치 처리 및 이력 관리

### 진행 상황

- ✅ 데이터 수집 스크립트 개발 완료
- ✅ 데이터베이스 스키마 구성 완료
- ✅ 전처리 전략 수립 완료
- ✅ LLM 프롬프트 개발 완료
- ✅ 전처리 및 검증 스크립트 구현 완료
- ⏳ **전처리 실행**: 아직 진행하지 않음

### 관련 파일

- `preprocessing/collect_inclusion_exclusion.py`: 데이터 수집 스크립트
- `sql/create_inclusion_exclusion_raw.sql`: 원본 데이터 테이블
- `sql/create_inclusion_exclusion_llm_preprocessed.sql`: 전처리 결과 테이블
- `sql/create_inclusion_exclusion_validation_history.sql`: 검증 이력 테이블
- `llm/llm_prompts.py`: Inclusion/Exclusion 프롬프트 함수 추가
- `llm/llm_preprocess_inclusion_exclusion.py`: 전처리 스크립트
- `llm/llm_validate_inclusion_exclusion.py`: 검증 스크립트
- `docs/inclusion_exclusion_table_design.md`: 테이블 설계 문서
- `docs/inclusion_exclusion_implementation_plan.md`: 구현 계획 문서

---

## 다음 작업 예정

1. **LLM 검증 완료**: API 토큰 제약 해소 후 나머지 2/3 검증 진행
2. **Inclusion/Exclusion 전처리 실행**: 수집된 데이터를 LLM으로 전처리
3. **전처리 결과 검증**: 전처리된 데이터의 품질 검증
