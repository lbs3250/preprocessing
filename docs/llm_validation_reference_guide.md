1. 목적

LLM 검증의 구조적 한계를 설명하고 업계 및 연구 레퍼런스를 기반으로 합리적이고 신뢰 가능한 검증 프로세스를 정리한다.

2. 현재 LLM 검증 방식 요약 (As-Is)

대상: 전처리 성공(SUCCESS) outcome

방식: 항목당 1회 LLM 검증

결과:

검증 상태 (VERIFIED, UNCERTAIN, MEASURE_FAILED 등)

Confidence Score

검증 노트

한계점

동일 입력에도 검증 결과가 달라질 수 있음

결과의 일관성(consistency)을 측정할 수 없음

단일 결과를 그대로 신뢰하게 되는 구조

3. LLM 검증이 비결정론적인 이유

LLM은 생성 과정에서 확률적 샘플링을 사용하며,
Temperature, Top-p 등의 파라미터에 따라 동일 입력에도 서로 다른 출력이 발생할 수 있다.

Temperature를 낮추면 변동성은 감소

그러나 완전한 결정론은 보장되지 않음

따라서 단일 1회 검증 결과를 정답으로 간주하는 것은 적절하지 않음

4. LLM 검증에 대한 레퍼런스 기반 접근

신뢰도 높은 공식 문서 및 연구에서 공통적으로 제시하는 방향은 다음과 같다.

핵심 공통 원칙

단일 결과에 의존하지 말 것

반복 실행 후 집계된 결과를 사용할 것

신뢰도(confidence)와 일관성(consistency)을 함께 고려할 것

필요 시 인적 검토(human-in-the-loop)를 결합할 것

5. 제안하는 Robust 검증 프로세스 (To-Be)

5.1 다중 검증 (Multi-run Validation)

동일한 outcome을 여러 번(권장: 3회이상) 검증

각 실행 결과의 status / confidence 저장

5.2 Majority Voting (다수결)

가장 많이 나온 검증 상태를 최종 결과로 채택

동률 발생 시 보수적으로 UNCERTAIN 처리 또는 재검증

효과

단일 판단 오류 최소화

결과 안정성 향상

5.3 Consistency Score 도입

동일 결과가 나온 비율을 일관성 점수로 수치화

예시

3회 중 VERIFIED 2회 → Consistency = 0.67

의미

해당 outcome의 검증 결과가 얼마나 안정적인지 정량적으로 판단 가능

5.4 Confidence + Consistency 기반 운영 정책 (예시)

조건

처리

Consistency ≥ 0.67 & Avg Confidence ≥ 0.80

자동 수용

Consistency ≥ 0.67 & Avg Confidence 0.50~0.80

추가 검증

Consistency < 0.67 또는 Avg Confidence < 0.50

수동 검토

※ 임계값은 운영 데이터에 따라 조정 가능

5.5 결정론성 보완 전략

검증 단계에서 Temperature를 낮게 설정하여 변동성 완화

단, 반드시 다중 검증과 병행하여 사용

6. 기대 효과

정량적 효과

검증 결과 일관성 향상

False Positive / False Negative 감소

수동 검토 대상 자동 선별 → 운영 비용 절감

정성적 효과

검증 프로세스에 대한 신뢰성 확보

검증 품질을 수치로 설명 가능

관리/의사결정에 활용 가능한 근거 확보

7. 적용 권장 순서

다중 검증 + Majority Voting 도입

Consistency Score 산출 및 저장

Confidence 기반 자동 분기

일관성 리포트로 지속 모니터링
