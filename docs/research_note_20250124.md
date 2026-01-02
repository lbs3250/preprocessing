# 연구노트 - 2025년 1월 24일

## 작업 개요

오늘은 Inclusion/Exclusion Criteria의 LLM 검증 작업을 진행하고, 검증 스크립트를 수정하며, 전처리 및 검증된 항목들을 정리했습니다.

---

## 1. Inclusion/Exclusion LLM 검증 진행

### 1.1 검증 현황

- **전처리 성공 항목**: 1,361개
- **검증 완료 항목**: 247개 (18.1%)
- **검증 진행률**: 약 18% 완료

### 1.2 검증 스크립트 수정 사항

#### 1.2.1 API 키 소진 처리 개선

**문제점**: API 키가 모두 소진되었을 때 무한 루프 발생

**해결 방법**:
- `llm_config._all_keys_exhausted` 플래그 확인 로직 추가
- `validate_batch_single_run` 함수 시작 부분과 API 호출 후 체크
- `validate_batch_eligibility` 함수에서 각 검증 run 전후 체크
- 모든 키가 소진되면 `UNCERTAIN` 상태로 반환하고 검증 중단

**수정 위치**:
```python
# llm/llm_validate_inclusion_exclusion.py
# validate_batch_single_run 함수
if llm_config._all_keys_exhausted:
    print(f"[WARN] 모든 API 키가 소진되어 검증 중단")
    return {item['nct_id']: {'status': 'UNCERTAIN', 'confidence': 0.0, 'notes': 'API 키 소진'} 
            for item in eligibility_list}
```

#### 1.2.2 부분 JSON 파싱 강화

**문제점**: LLM 응답이 잘려서 JSON 파싱 실패 ("Unterminated string" 에러)

**해결 방법**:
- `call_gemini_api` 함수에 부분 JSON 파싱 로직 추가
- 중괄호/대괄호 카운팅 방식으로 완전한 JSON 객체 추출
- 정규표현식을 통한 JSON 배열 추출
- 배치 크기 축소 권장 (응답 길이 감소)

**수정 내용**:
```python
# llm/llm_validate_inclusion_exclusion.py
# call_gemini_api 함수 내부
# 중괄호 카운팅으로 완전한 JSON 추출
brace_count = 0
bracket_count = 0
json_end = -1
for i, char in enumerate(content):
    if char == '[':
        bracket_count += 1
    elif char == ']':
        bracket_count -= 1
    if bracket_count == 0 and i > 0:
        json_end = i + 1
        break
```

#### 1.2.3 Temperature 설정

**목적**: 검증 결과의 일관성 향상

**수정 내용**:
- `call_gemini_api` 함수에서 `temperature=0.0` 설정
- 결정론적 출력을 위해 최소값 설정
- `TypeError` 발생 시 기본 호출로 fallback

```python
try:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        temperature=0.0  # 결정론적 출력
    )
except TypeError:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
```

---

## 2. LLM 전처리된 항목 정리

### 2.1 Inclusion/Exclusion 전처리 통계

**전체 현황**:
- **전체 레코드**: 1,320개
- **전처리 성공 (SUCCESS)**: 1,270개 (96.21%)
- **전처리 실패**: 50개 (3.79%)
  - Inclusion 실패: 0개
  - Exclusion 실패: 0개
  - 둘 다 실패: 20개 (1.52%)
  - API 실패: 30개 (2.27%)

**Criteria 추출 통계**:
- **평균 Inclusion Criteria 개수**: 10.8개
- **평균 Exclusion Criteria 개수**: 15.6개
- **최대 Inclusion Criteria 개수**: 76개
- **최대 Exclusion Criteria 개수**: 106개

**주요 Feature 분포 (상위 10개)**:
1. patient: 6,026회
2. age: 1,360회
3. gender: 647회
4. MMSE score: 512회
5. MMSE: 473회
6. diagnosis: 407회
7. BMI: 392회
8. subject: 363회
9. caregiver: 290회
10. medication: 245회

### 2.2 전처리 결과 특징

**성공적인 구조화**:
- 각 criterion이 `feature`, `operator`, `value` 형태로 정확히 추출됨
- 범위 조건이 두 개의 별도 criterion으로 분리됨 (예: "MMSE 10-22" → `>= 10`과 `<= 22`)
- 복잡한 조건도 구조화되어 저장됨

**주요 개선 사항**:
- `feature` 필드에 카테고리가 아닌 구체적인 항목명 사용 (예: "MMSE", "age", "schizophrenia")
- `operator` 필드에 표준 수학 연산자 사용 (`=`, `!=`, `<`, `<=`, `>`, `>=`)
- `value` 필드에 항상 값이 포함됨 (null 없음)

---

## 3. Outcome 검증된 항목 정리

### 3.1 Outcome 전처리 통계

- **전처리 성공 항목**: 8,912개
- **전처리 성공률**: 98.69% (전체 9,030개 중)

### 3.2 Outcome 검증 통계

**검증 완료 현황**:
- **검증 완료 항목**: 8,414개 (94.4%)
- **검증 미완료 항목**: 498개 (5.6%)

**검증 결과 분포** (검증 완료 항목 기준):
- **VERIFIED**: 대부분 (정확한 통계는 추가 확인 필요)
- **UNCERTAIN**: 소수
- **FAILED**: 소수 (MEASURE_FAILED, TIMEFRAME_FAILED, BOTH_FAILED)

**검증 완료 항목 중 수동 검토 필요 여부**:
- `needs_manual_review = FALSE`: 자동 검증 통과 (대부분)
- `needs_manual_review = TRUE`: 수동 검토 필요 (소수)

### 3.3 검증 품질 지표

**일관성 점수 (Consistency Score)**:
- 여러 번의 검증 실행에서 동일한 결과가 나온 비율
- 높을수록 검증 결과가 안정적임

**평균 신뢰도 (Average Confidence)**:
- LLM이 검증 결과에 대해 가지는 신뢰도
- 높을수록 검증 결과가 신뢰할 만함

---

## 4. 검증 스크립트 사용법 정리

### 4.1 Inclusion/Exclusion 검증 스크립트

**기본 실행**:
```bash
python llm/llm_validate_inclusion_exclusion.py
```

**옵션**:
- `limit`: 처리할 항목 수 제한
- `num_validations`: 각 항목당 검증 횟수 (기본: 3회)
- `batch_size`: 배치 크기 (기본: 100개)
- `start_batch`: 시작 배치 번호 (중단 후 재개 시 사용)

**예시**:
```bash
# 50개만 검증, 배치 크기 20개
python llm/llm_validate_inclusion_exclusion.py 50 3 20

# 10번째 배치부터 재개
python llm/llm_validate_inclusion_exclusion.py None 3 100 10
```

### 4.2 Outcome 검증 스크립트

**기본 실행**:
```bash
python llm/llm_validate_preprocessed_success.py
```

**옵션**: Inclusion/Exclusion 검증과 동일한 구조

---

## 5. 다음 작업 계획

### 5.1 Inclusion/Exclusion 검증 완료

- 현재 247개 완료 (18.1%)
- 남은 1,114개 항목 검증 진행
- API 토큰 제약 고려하여 배치 처리 계속 진행

### 5.2 검증 결과 분석

- VERIFIED 항목 중 수동 검토 필요 항목 비율 확인
- 검증 실패 항목의 원인 분석
- 일관성 점수 및 신뢰도 분포 분석

### 5.3 Outcome 검증 완료

- 남은 498개 항목 검증 진행 (5.6%)
- 검증 완료 후 최종 통계 정리

---

## 6. 기술적 개선 사항

### 6.1 API 키 관리

- 여러 API 키 순환 사용
- 키 소진 시 자동 전환
- 모든 키 소진 시 안전하게 중단

### 6.2 에러 처리

- 부분 JSON 파싱으로 응답 잘림 문제 해결
- nct_id 누락 시 순서 기반 복구
- API 에러 시 자동 재시도 및 키 전환

### 6.3 배치 처리 최적화

- 배치 크기 조정으로 응답 길이 제어
- 중단 후 재개 기능으로 장시간 실행 지원
- 배치 단위 DB 업데이트로 성능 향상

---

## 7. 참고 자료

- `docs/inclusion_exclusion_preprocessing_report.md`: Inclusion/Exclusion 전처리 상세 보고서
- `docs/inclusion_exclusion_validation_usage_guide.md`: Inclusion/Exclusion 검증 사용 가이드
- `docs/llm_validation_usage_guide.md`: Outcome 검증 사용 가이드
- `llm/llm_validate_inclusion_exclusion.py`: Inclusion/Exclusion 검증 스크립트
- `llm/llm_validate_preprocessed_success.py`: Outcome 검증 스크립트

---

**작성일**: 2025년 1월 24일  
**작성자**: 연구팀

