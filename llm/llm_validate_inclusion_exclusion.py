"""
LLM 전처리 성공 항목 검증 스크립트 (Inclusion/Exclusion)

inclusion_exclusion_llm_preprocessed 테이블에서 llm_status = 'SUCCESS'인 항목들을
LLM으로 검증하여 문서화합니다.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
from llm_config import (
    get_api_keys, GEMINI_MODEL,
    MAX_REQUESTS_PER_MINUTE, BATCH_SIZE, MAX_RETRIES, RETRY_DELAY
)
from llm_prompts import get_inclusion_exclusion_validation_prompt

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def call_gemini_api(prompt: str) -> Optional[List]:
    """Gemini API 호출 (여러 API 키를 순차적으로 시도, 429 에러 시 자동 전환)"""
    api_keys = get_api_keys()
    if not api_keys:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        return None
    
    import llm_config
    start_key_index = llm_config._current_key_index
    last_error = None
    
    for attempt in range(len(api_keys)):
        key_index = (start_key_index + attempt) % len(api_keys)
        
        try:
            from google import genai
            client = genai.Client(api_key=api_keys[key_index])
            # 검증 시 Temperature를 0.0으로 설정하여 변동성 최소화
            # generate_content에 temperature 파라미터 직접 전달 시도
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    temperature=0.0  # 결정론적 출력을 위해 최소값 설정
                )
            except TypeError:
                # temperature 파라미터가 지원되지 않는 경우 기본 호출
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
            
            if llm_config._current_key_index != key_index:
                llm_config._previous_key_index = llm_config._current_key_index
                llm_config._current_key_index = key_index
            else:
                llm_config._current_key_index = key_index
            
            content = response.text.strip()
            
            # JSON 추출 (코드 블록 제거)
            if '```' in content:
                import re
                code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
                match = re.search(code_block_pattern, content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                else:
                    content = re.sub(r'```(?:json)?', '', content).strip()
            
            # JSON 배열 시작 부분 찾기
            json_start = content.find('[')
            if json_start >= 0:
                content = content[json_start:]
            
            json_end = content.rfind(']')
            if json_end >= 0:
                content = content[:json_end + 1]
            
            content = content.strip()
            
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, list):
                    parsed = [parsed]
                return parsed
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON 파싱 실패 (키 {key_index + 1}/{len(api_keys)}): {e}")
                print(f"  응답 내용 (처음 500자): {content[:500]}")
                
                # 부분 파싱 시도: 완전한 JSON 객체들만 추출
                try:
                    import re
                    parsed_items = []
                    
                    # 완전한 JSON 객체 패턴 찾기 (중첩 구조 지원)
                    # { ... } 형태의 완전한 객체를 찾음
                    brace_count = 0
                    start_pos = -1
                    current_obj = ""
                    
                    for i, char in enumerate(content):
                        if char == '{':
                            if brace_count == 0:
                                start_pos = i
                            brace_count += 1
                            current_obj += char
                        elif char == '}':
                            current_obj += char
                            brace_count -= 1
                            if brace_count == 0 and start_pos >= 0:
                                # 완전한 객체 발견
                                try:
                                    obj = json.loads(current_obj)
                                    if isinstance(obj, dict) and 'nct_id' in obj:
                                        parsed_items.append(obj)
                                except json.JSONDecodeError:
                                    pass
                                current_obj = ""
                                start_pos = -1
                        elif start_pos >= 0:
                            current_obj += char
                    
                    if parsed_items:
                        print(f"  [복구] {len(parsed_items)}개 항목을 부분 파싱하여 복구했습니다.")
                        return parsed_items
                    else:
                        # 정규식으로도 시도
                        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                        for obj_str in json_objects:
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict) and 'nct_id' in obj:
                                    parsed_items.append(obj)
                            except json.JSONDecodeError:
                                continue
                        
                        if parsed_items:
                            print(f"  [복구] {len(parsed_items)}개 항목을 정규식으로 복구했습니다.")
                            return parsed_items
                        
                except Exception as recover_error:
                    print(f"  [복구 실패] {recover_error}")
                
                return None
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str.upper():
                print(f"⚠️  API 키 {key_index + 1}/{len(api_keys)}에서 429 에러 발생 (시도 {attempt + 1}/{len(api_keys)}): {error_str}")
                
                if attempt == len(api_keys) - 1:
                    print(f"[ERROR] 모든 API 키({len(api_keys)}개)가 소진되었습니다.")
                    llm_config._previous_key_index = llm_config._current_key_index
                    llm_config._current_key_index = key_index
                    llm_config._all_keys_exhausted = True
                    return None
                else:
                    next_key_index = (start_key_index + attempt + 1) % len(api_keys)
                    print(f"🔄 다음 API 키로 전환합니다 (키 {next_key_index + 1}/{len(api_keys)})")
                    continue
            else:
                print(f"[ERROR] Gemini API 오류 (키 {key_index + 1}/{len(api_keys)}): {error_str}")
                return None
    
    print(f"[ERROR] 모든 API 키({len(api_keys)}개) 시도 실패. 마지막 에러: {str(last_error)}")
    llm_config._all_keys_exhausted = True
    return None


def format_criteria(criteria) -> str:
    """inclusion/exclusion criteria를 문자열로 변환"""
    if not criteria:
        return ''
    try:
        if isinstance(criteria, str):
            criteria = json.loads(criteria)
        if isinstance(criteria, list):
            return json.dumps(criteria, ensure_ascii=False)
    except:
        pass
    return str(criteria)


def validate_batch_single_run(eligibility_list: List[Dict]) -> Dict[str, Dict]:
    """
    배치 단위로 eligibilityCriteria를 LLM으로 검증 (1회 실행)
    
    Args:
        eligibility_list: 검증할 eligibility 리스트
    
    Returns:
        {nct_id: {status, confidence, notes}} 형태의 딕셔너리
    """
    if not eligibility_list:
        return {}
    
    # 모든 키가 소진되었는지 확인
    import llm_config
    if llm_config._all_keys_exhausted:
        # 모든 키가 소진된 경우 UNCERTAIN 반환
        return {
            eligibility.get('nct_id'): {
                'status': 'UNCERTAIN',
                'confidence': None,
                'notes': '[API_KEYS_EXHAUSTED] 모든 API 키가 소진되었습니다.'
            }
            for eligibility in eligibility_list if eligibility.get('nct_id')
        }
    
    # 배치 프롬프트 생성
    items = []
    nct_id_map = {}  # nct_id -> eligibility 매핑
    
    for eligibility in eligibility_list:
        nct_id = eligibility.get('nct_id')
        criteria_raw = eligibility.get('eligibility_criteria_raw', '')
        inclusion_criteria = format_criteria(eligibility.get('inclusion_criteria'))
        exclusion_criteria = format_criteria(eligibility.get('exclusion_criteria'))
        
        parts = [f"{nct_id}"]
        if criteria_raw:
            parts.append(f"RAW:{criteria_raw}")
        if inclusion_criteria:
            parts.append(f"INC:{inclusion_criteria}")
        if exclusion_criteria:
            parts.append(f"EXC:{exclusion_criteria}")
        item_str = "|".join(parts)
        items.append(item_str)
        nct_id_map[nct_id] = eligibility
    
    # 배치 프롬프트 생성
    items_text = '\n'.join(items)
    prompt = get_inclusion_exclusion_validation_prompt(items_text)
    
    result = call_gemini_api(prompt)
    
    # 모든 키가 소진되었는지 다시 확인
    if llm_config._all_keys_exhausted:
        # 모든 키가 소진된 경우 UNCERTAIN 반환
        return {
            nct_id: {
                'status': 'UNCERTAIN',
                'confidence': None,
                'notes': '[API_KEYS_EXHAUSTED] 모든 API 키가 소진되었습니다.'
            }
            for nct_id in nct_id_map.keys()
        }
    
    if not result:
        # API 실패 시 모두 UNCERTAIN 처리
        return {
            nct_id: {
                'status': 'UNCERTAIN',
                'confidence': None,
                'notes': '[API_FAILED] LLM API 호출 실패.'
            }
            for nct_id in nct_id_map.keys()
        }
    
    # 결과 파싱
    results_map = {}
    if isinstance(result, list):
        for r in result:
            nct_id = r.get('nct_id')
            if nct_id in nct_id_map:
                status = r.get('status', '').upper()
                valid_statuses = ['VERIFIED', 'UNCERTAIN', 'INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED']
                if status not in valid_statuses:
                    status = 'UNCERTAIN'
                results_map[nct_id] = {
                    'status': status,
                    'confidence': r.get('confidence'),
                    'notes': r.get('notes', '')
                }
        
        # 응답에 없는 항목은 UNCERTAIN 처리
        for nct_id in nct_id_map.keys():
            if nct_id not in results_map:
                results_map[nct_id] = {
                    'status': 'UNCERTAIN',
                    'confidence': None,
                    'notes': '[PARSE_ERROR] LLM 응답에 nct_id가 없음.'
                }
    else:
        # 단일 응답인 경우 (하위 호환성)
        if eligibility_list:
            eligibility = eligibility_list[0]
            nct_id = eligibility.get('nct_id')
            status = result.get('status', '').upper()
            valid_statuses = ['VERIFIED', 'UNCERTAIN', 'INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED']
            if status not in valid_statuses:
                status = 'UNCERTAIN'
            results_map[nct_id] = {
                'status': status,
                'confidence': result.get('confidence'),
                'notes': result.get('notes', '')
            }
    
    return results_map


def calculate_consistency_score(validation_results: List[Dict]) -> float:
    """일관성 점수 계산: 동일한 결과가 나온 비율"""
    if not validation_results:
        return 0.0
    
    status_counts = {}
    for result in validation_results:
        status = result.get('status', '')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    if not status_counts:
        return 0.0
    
    # 가장 많이 나온 결과의 비율
    max_count = max(status_counts.values())
    return max_count / len(validation_results)


def majority_voting(validation_results: List[Dict]) -> Dict:
    """Majority Voting: 가장 많이 나온 검증 상태를 최종 결과로 선택"""
    if not validation_results:
        return {
            'status': 'UNCERTAIN',
            'confidence': None,
            'notes': '검증 결과가 없습니다.'
        }
    
    status_counts = {}
    confidences_by_status = {}
    
    for result in validation_results:
        status = result.get('status', '')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status not in confidences_by_status:
            confidences_by_status[status] = []
        confidences_by_status[status].append(result.get('confidence'))
    
    if not status_counts:
        return {
            'status': 'UNCERTAIN',
            'confidence': None,
            'notes': '유효한 검증 결과가 없습니다.'
        }
    
    # 가장 많이 나온 상태 선택
    max_count = max(status_counts.values())
    final_statuses = [s for s, count in status_counts.items() if count == max_count]
    
    # 동률 발생 시 보수적으로 UNCERTAIN 처리
    if len(final_statuses) > 1:
        final_status = 'UNCERTAIN'
        notes = f'[TIE] 동률 발생: {", ".join(final_statuses)}. 보수적으로 UNCERTAIN 처리.'
    else:
        final_status = final_statuses[0]
        notes = f'[MAJORITY] {max_count}/{len(validation_results)}회 일치'
    
    # 평균 신뢰도 계산
    if final_status in confidences_by_status:
        confidences = [float(c) for c in confidences_by_status[final_status] if c is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None
    else:
        # 최종 상태의 신뢰도가 없으면 전체 평균
        all_confidences = [float(r.get('confidence')) for r in validation_results if r.get('confidence') is not None]
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else None
    
    return {
        'status': final_status,
        'confidence': avg_confidence,
        'notes': notes
    }


def apply_confidence_consistency_filtering(
    final_result: Dict,
    consistency_score: float,
    high_consistency_threshold: float = 0.67,
    high_confidence_threshold: float = 0.80,
    low_confidence_threshold: float = 0.50
) -> Dict:
    """Confidence + Consistency 기반 필터링 적용"""
    confidence = final_result.get('confidence')
    if confidence is None:
        confidence = 0.0
    else:
        confidence = float(confidence)
    
    # 자동 수용: Consistency ≥ 0.67 & Avg Confidence ≥ 0.80
    if consistency_score >= high_consistency_threshold and confidence >= high_confidence_threshold:
        return {
            **final_result,
            'action': 'ACCEPT',
            'needs_manual_review': False
        }
    
    # 추가 검증: Consistency ≥ 0.67 & Avg Confidence 0.50~0.80
    if consistency_score >= high_consistency_threshold and low_confidence_threshold <= confidence < high_confidence_threshold:
        return {
            **final_result,
            'action': 'REVALIDATE',
            'needs_manual_review': False
        }
    
    # 수동 검토: Consistency < 0.67 또는 Avg Confidence < 0.50
    return {
        **final_result,
        'action': 'MANUAL_REVIEW',
        'needs_manual_review': True
    }


def validate_with_multi_run_for_eligibility(
    eligibility: Dict,
    validation_results_by_run: Dict[int, Dict],
    existing_results: List[Dict]
) -> Dict:
    """
    단일 eligibility에 대해 다중 검증 결과를 처리하는 함수
    
    Args:
        eligibility: 검증할 eligibility 데이터
        validation_results_by_run: {run_number: {nct_id: result}} 형태의 딕셔너리
        existing_results: 기존 검증 이력
    
    Returns:
        검증 결과 딕셔너리
    """
    nct_id = eligibility.get('nct_id')
    
    # 해당 eligibility의 검증 결과 수집
    new_validation_results = []
    for run_num in sorted(validation_results_by_run.keys()):
        run_results = validation_results_by_run[run_num]
        if nct_id in run_results:
            new_validation_results.append(run_results[nct_id])
    
    # 기존 결과와 새 결과 합치기
    all_validation_results = existing_results + new_validation_results
    
    if not all_validation_results:
        return {
            'nct_id': nct_id,
            'final_status': 'UNCERTAIN',
            'consistency_score': 0.0,
            'validation_results': [],
            'all_validation_results': [],
            'average_confidence': None,
            'validation_count': 0,
            'needs_manual_review': True,
            'action': 'MANUAL_REVIEW'
        }
    
    # 전체 결과로 Majority Voting
    final_result = majority_voting(all_validation_results)
    
    # 전체 결과로 일관성 점수 계산
    consistency_score = calculate_consistency_score(all_validation_results)
    
    # 전체 결과로 평균 신뢰도 계산
    all_confidences = [float(r.get('confidence')) for r in all_validation_results if r.get('confidence') is not None]
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else None
    
    # Confidence + Consistency 기반 필터링
    filtered_result = apply_confidence_consistency_filtering(
        final_result,
        consistency_score
    )
    
    return {
        'nct_id': nct_id,
        'final_status': filtered_result['status'],
        'consistency_score': consistency_score,
        'validation_results': new_validation_results,  # 새로 수행한 검증만
        'all_validation_results': all_validation_results,  # 전체 검증 결과
        'average_confidence': avg_confidence,
        'validation_count': len(all_validation_results),  # 전체 검증 횟수
        'needs_manual_review': filtered_result.get('needs_manual_review', False),
        'action': filtered_result.get('action', 'ACCEPT'),
        'llm_validation_confidence': filtered_result.get('confidence'),
        'llm_validation_notes': filtered_result.get('notes', '')
    }


def validate_batch_eligibility(eligibility_list: List[Dict], num_validations: int = 3, conn=None) -> tuple:
    """
    배치 단위로 eligibilityCriteria들을 다중 검증 (전처리와 동일한 방식)
    
    Args:
        eligibility_list: 검증할 eligibility 리스트
        num_validations: 각 eligibility당 검증 횟수 (기본값: 3)
        conn: 데이터베이스 연결 (재검증 시 기존 이력과 합치기 위해 필요)
    
    Returns:
        (results: List[Dict], validation_results_by_run: Dict[int, Dict])
        - results: 각 eligibility별 최종 검증 결과
        - validation_results_by_run: {run_number: {nct_id: result}} 형태의 검증 이력
    
    Note:
        배치 내 모든 항목을 한 번에 프롬프트로 만들어서 N회 검증합니다.
        전처리와 동일한 방식으로 배치 단위 API 호출을 수행합니다.
        재검증 시 기존 검증 이력과 합쳐서 Majority Voting을 수행합니다.
    """
    if not eligibility_list:
        return [], {}
    
    # 기존 검증 이력 조회 (재검증 시)
    existing_results_by_eligibility = {}
    if conn:
        for eligibility in eligibility_list:
            nct_id = eligibility.get('nct_id')
            if nct_id:
                existing_results = get_existing_validation_history(conn, nct_id)
                if existing_results:
                    existing_results_by_eligibility[nct_id] = existing_results
    
    # N회 검증 수행 (배치 단위로)
    validation_results_by_run = {}  # {run_number: {nct_id: result}}
    
    for run_num in range(1, num_validations + 1):
        # 모든 키가 소진되었는지 확인
        import llm_config
        if llm_config._all_keys_exhausted:
            print(f"[WARN] 모든 API 키가 소진되어 검증 중단 (run {run_num}/{num_validations})")
            break
        
        # 배치 단위로 1회 검증
        run_results = validate_batch_single_run(eligibility_list)
        validation_results_by_run[run_num] = run_results
        
        # 모든 키가 소진되었는지 다시 확인
        if llm_config._all_keys_exhausted:
            print(f"[WARN] 모든 API 키가 소진되어 검증 중단 (run {run_num}/{num_validations})")
            break
        
        # Rate limiting (마지막 검증 제외)
        if run_num < num_validations:
            time.sleep(60 / MAX_REQUESTS_PER_MINUTE)
    
    # 각 eligibility별로 결과 처리
    results = []
    for eligibility in eligibility_list:
        nct_id = eligibility.get('nct_id')
        existing_results = existing_results_by_eligibility.get(nct_id, [])
        
        result = validate_with_multi_run_for_eligibility(
            eligibility,
            validation_results_by_run,
            existing_results
        )
        results.append(result)
    
    return results, validation_results_by_run


def get_existing_validation_history(conn, nct_id: str) -> List[Dict]:
    """기존 검증 이력을 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                validation_status as status,
                validation_confidence as confidence,
                validation_notes as notes
            FROM inclusion_exclusion_llm_validation_history
            WHERE nct_id = %s
            ORDER BY validation_run
        """, (nct_id,))
        results = cur.fetchall()
        return [dict(r) for r in results]


def save_validation_history_batch(conn, validation_results_by_run: Dict[int, Dict]):
    """
    배치 단위로 검증 이력을 데이터베이스에 저장 (전처리와 동일한 방식)
    
    Args:
        conn: 데이터베이스 연결
        validation_results_by_run: {run_number: {nct_id: result}} 형태
    """
    if not validation_results_by_run:
        return
    
    # 모든 nct_id 수집
    all_nct_ids = set()
    for run_results in validation_results_by_run.values():
        all_nct_ids.update(run_results.keys())
    
    if not all_nct_ids:
        return
    
    # 각 nct_id별로 기존 이력의 최대 validation_run 조회 (배치로)
    nct_id_max_runs = {}
    with conn.cursor() as cur:
        placeholders = ','.join(['%s'] * len(all_nct_ids))
        cur.execute(f"""
            SELECT 
                nct_id,
                COALESCE(MAX(validation_run), 0) as max_run
            FROM inclusion_exclusion_llm_validation_history
            WHERE nct_id IN ({placeholders})
            GROUP BY nct_id
        """, list(all_nct_ids))
        
        for row in cur.fetchall():
            nct_id_max_runs[row[0]] = row[1]
    
    # nct_id별로 다음 run 번호 설정
    nct_id_next_runs = {}
    for nct_id in all_nct_ids:
        nct_id_next_runs[nct_id] = nct_id_max_runs.get(nct_id, 0) + 1
    
    # 모든 검증 이력 데이터 수집
    history_data = []
    for run_num in sorted(validation_results_by_run.keys()):
        run_results = validation_results_by_run[run_num]
        for nct_id, result in run_results.items():
            history_data.append({
                'nct_id': nct_id,
                'validation_run': nct_id_next_runs[nct_id],
                'validation_status': result.get('status'),
                'validation_confidence': result.get('confidence'),
                'validation_notes': result.get('notes', '')
            })
            # 다음 run 번호 증가
            nct_id_next_runs[nct_id] += 1
    
    if not history_data:
        return
    
    # 배치로 저장
    history_sql = """
        INSERT INTO inclusion_exclusion_llm_validation_history 
        (nct_id, validation_run, validation_status, validation_confidence, validation_notes)
        VALUES (%(nct_id)s, %(validation_run)s, %(validation_status)s, %(validation_confidence)s, %(validation_notes)s)
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, history_sql, history_data, page_size=100)
        conn.commit()


def update_validation_results(conn, results: List[Dict], validation_results_by_run: Dict[int, Dict] = None):
    """
    LLM 검증 결과를 데이터베이스에 업데이트 (다중 검증 결과 포함)
    전처리와 동일하게 배치 단위로 저장합니다.
    
    Args:
        conn: 데이터베이스 연결
        results: 검증 결과 리스트
        validation_results_by_run: {run_number: {nct_id: result}} 형태 (배치 검증 결과)
    """
    if not results:
        return
    
    # 검증 이력 저장 (배치 단위로)
    if validation_results_by_run:
        save_validation_history_batch(conn, validation_results_by_run)
    else:
        # 기존 방식 (개별 검증 결과) - 하위 호환성
        for result in results:
            nct_id = result.get('nct_id')
            validation_results = result.get('validation_results', [])
            if nct_id and validation_results:
                # 개별 저장 (하위 호환성)
                nct_id_max_runs = {}
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(MAX(validation_run), 0) as max_run
                        FROM inclusion_exclusion_llm_validation_history
                        WHERE nct_id = %s
                    """, (nct_id,))
                    result_row = cur.fetchone()
                    start_run = (result_row[0] if result_row else 0) + 1
                
                history_sql = """
                    INSERT INTO inclusion_exclusion_llm_validation_history 
                    (nct_id, validation_run, validation_status, validation_confidence, validation_notes)
                    VALUES (%(nct_id)s, %(validation_run)s, %(validation_status)s, %(validation_confidence)s, %(validation_notes)s)
                """
                
                history_data = []
                for idx, val_result in enumerate(validation_results, start_run):
                    history_data.append({
                        'nct_id': nct_id,
                        'validation_run': idx,
                        'validation_status': val_result.get('status'),
                        'validation_confidence': val_result.get('confidence'),
                        'validation_notes': val_result.get('notes', '')
                    })
                
                with conn.cursor() as cur:
                    execute_batch(cur, history_sql, history_data, page_size=100)
                    conn.commit()
    
    # 메인 테이블 업데이트
    update_sql = """
        UPDATE inclusion_exclusion_llm_preprocessed
        SET 
            llm_validation_status = %(final_status)s,
            llm_validation_confidence = %(llm_validation_confidence)s,
            llm_validation_notes = %(llm_validation_notes)s,
            validation_consistency_score = %(consistency_score)s,
            validation_count = %(validation_count)s,
            needs_manual_review = %(needs_manual_review)s,
            avg_validation_confidence = %(average_confidence)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE nct_id = %(nct_id)s
    """
    
    update_data = []
    for result in results:
        update_data.append({
            'nct_id': result.get('nct_id'),
            'final_status': result.get('final_status'),
            'llm_validation_confidence': result.get('llm_validation_confidence'),
            'llm_validation_notes': result.get('llm_validation_notes', ''),
            'consistency_score': result.get('consistency_score'),
            'validation_count': result.get('validation_count', 1),
            'needs_manual_review': result.get('needs_manual_review', False),
            'average_confidence': result.get('average_confidence')
        })
    
    with conn.cursor() as cur:
        execute_batch(cur, update_sql, update_data, page_size=100)
        conn.commit()


def generate_validation_report(conn, output_dir=None):
    """검증 결과 리포트 생성"""
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/inclusion_exclusion_validation_{timestamp}.md'
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total_success,
                COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') as verified,
                COUNT(*) FILTER (WHERE llm_validation_status = 'UNCERTAIN') as uncertain,
                COUNT(*) FILTER (WHERE llm_validation_status = 'INCLUSION_FAILED') as inclusion_failed,
                COUNT(*) FILTER (WHERE llm_validation_status = 'EXCLUSION_FAILED') as exclusion_failed,
                COUNT(*) FILTER (WHERE llm_validation_status = 'BOTH_FAILED') as both_failed,
                AVG(llm_validation_confidence) FILTER (WHERE llm_validation_status = 'VERIFIED') as avg_verified_confidence,
                AVG(llm_validation_confidence) as avg_confidence
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
        """)
        stats = cur.fetchone()
        
        # Study별 통계
        cur.execute("""
            SELECT 
                COUNT(DISTINCT nct_id) AS total_studies,
                COUNT(DISTINCT nct_id) FILTER (WHERE llm_validation_status = 'VERIFIED') AS verified_studies
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
        """)
        study_stats = cur.fetchone()
        
        # 상태별 상세 통계
        cur.execute("""
            SELECT 
                llm_validation_status,
                COUNT(*) as count,
                AVG(llm_validation_confidence) as avg_confidence,
                MIN(llm_validation_confidence) as min_confidence,
                MAX(llm_validation_confidence) as max_confidence,
                AVG(validation_consistency_score) as avg_consistency,
                MIN(validation_consistency_score) as min_consistency,
                MAX(validation_consistency_score) as max_consistency
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
            GROUP BY llm_validation_status
            ORDER BY count DESC
        """)
        status_stats = cur.fetchall()
        
        # 일관성 점수 통계
        cur.execute("""
            SELECT 
                AVG(validation_consistency_score) as avg_consistency,
                MIN(validation_consistency_score) as min_consistency,
                MAX(validation_consistency_score) as max_consistency,
                COUNT(*) FILTER (WHERE validation_consistency_score >= 0.67) as high_consistency_count,
                COUNT(*) FILTER (WHERE validation_consistency_score < 0.67 AND validation_consistency_score >= 0.33) as medium_consistency_count,
                COUNT(*) FILTER (WHERE validation_consistency_score < 0.33) as low_consistency_count,
                COUNT(*) FILTER (WHERE needs_manual_review = TRUE) as manual_review_count
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND validation_consistency_score IS NOT NULL
        """)
        consistency_stats = cur.fetchone()
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Inclusion/Exclusion LLM 전처리 성공 항목 검증 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        f.write('## 1. 전체 통계\n\n')
        if stats and stats['total_success'] > 0:
            total = stats['total_success']
            f.write(f'- **전체 SUCCESS 항목**: {total:,}개\n')
            f.write(f'- **VERIFIED**: {stats["verified"]:,}개 ({stats["verified"]/total*100:.2f}%)\n')
            f.write(f'- **UNCERTAIN**: {stats["uncertain"]:,}개 ({stats["uncertain"]/total*100:.2f}%)\n')
            f.write(f'- **INCLUSION_FAILED**: {stats["inclusion_failed"]:,}개 ({stats["inclusion_failed"]/total*100:.2f}%)\n')
            f.write(f'- **EXCLUSION_FAILED**: {stats["exclusion_failed"]:,}개 ({stats["exclusion_failed"]/total*100:.2f}%)\n')
            f.write(f'- **BOTH_FAILED**: {stats["both_failed"]:,}개 ({stats["both_failed"]/total*100:.2f}%)\n')
            if stats['avg_verified_confidence']:
                f.write(f'- **VERIFIED 평균 신뢰도**: {float(stats["avg_verified_confidence"]):.2f}\n')
            if stats['avg_confidence']:
                f.write(f'- **전체 평균 신뢰도**: {float(stats["avg_confidence"]):.2f}\n')
        f.write('\n')
        
        f.write('## 2. Study별 통계\n\n')
        if study_stats:
            total_studies = study_stats['total_studies'] or 0
            verified_studies = study_stats['verified_studies'] or 0
            if total_studies > 0:
                f.write(f'- **전체 Study**: {total_studies:,}개\n')
                f.write(f'- **VERIFIED Study**: {verified_studies:,}개 ({verified_studies/total_studies*100:.2f}%)\n')
        f.write('\n')
        
        f.write('## 3. 상태별 상세 통계\n\n')
        if status_stats:
            f.write('| 검증 상태 | 개수 | 비율 | 평균 신뢰도 | 최소 신뢰도 | 최대 신뢰도 | 평균 일관성 | 최소 일관성 | 최대 일관성 |\n')
            f.write('|----------|------|------|------------|------------|------------|------------|------------|------------|\n')
            total_validated = sum(s['count'] for s in status_stats)
            for stat in status_stats:
                percentage = stat['count'] / total_validated * 100 if total_validated > 0 else 0
                avg_conf = float(stat['avg_confidence']) if stat['avg_confidence'] else 0
                min_conf = float(stat['min_confidence']) if stat['min_confidence'] else 0
                max_conf = float(stat['max_confidence']) if stat['max_confidence'] else 0
                avg_cons = float(stat['avg_consistency']) if stat['avg_consistency'] else 0
                min_cons = float(stat['min_consistency']) if stat['min_consistency'] else 0
                max_cons = float(stat['max_consistency']) if stat['max_consistency'] else 0
                f.write(f"| {stat['llm_validation_status']} | {stat['count']:,} | {percentage:.2f}% | {avg_conf:.2f} | {min_conf:.2f} | {max_conf:.2f} | {avg_cons:.2f} | {min_cons:.2f} | {max_cons:.2f} |\n")
        f.write('\n')
        
        f.write('## 4. 일관성 점수 통계\n\n')
        if consistency_stats:
            total_with_consistency = (
                (consistency_stats['high_consistency_count'] or 0) +
                (consistency_stats['medium_consistency_count'] or 0) +
                (consistency_stats['low_consistency_count'] or 0)
            )
            if total_with_consistency > 0:
                f.write(f'- **평균 일관성 점수**: {float(consistency_stats["avg_consistency"]):.2f}\n')
                f.write(f'- **최소 일관성 점수**: {float(consistency_stats["min_consistency"]):.2f}\n')
                f.write(f'- **최대 일관성 점수**: {float(consistency_stats["max_consistency"]):.2f}\n')
                f.write(f'\n')
                f.write(f'- **높은 일관성 (≥0.67)**: {consistency_stats["high_consistency_count"]:,}개 ({consistency_stats["high_consistency_count"]/total_with_consistency*100:.2f}%)\n')
                f.write(f'- **중간 일관성 (0.33~0.67)**: {consistency_stats["medium_consistency_count"]:,}개 ({consistency_stats["medium_consistency_count"]/total_with_consistency*100:.2f}%)\n')
                f.write(f'- **낮은 일관성 (<0.33)**: {consistency_stats["low_consistency_count"]:,}개 ({consistency_stats["low_consistency_count"]/total_with_consistency*100:.2f}%)\n')
                f.write(f'\n')
                f.write(f'- **수동 검토 필요**: {consistency_stats["manual_review_count"]:,}개\n')
        f.write('\n')
        
        f.write('## 5. 검증 방법\n\n')
        f.write('1. `inclusion_exclusion_llm_preprocessed` 테이블에서 `llm_status = \'SUCCESS\'`인 항목들을 조회\n')
        f.write('2. 각 항목을 **다중 검증** (기본 3회) 수행\n')
        f.write('3. **Majority Voting**으로 최종 검증 상태 결정\n')
        f.write('4. **일관성 점수** 계산 (동일 결과가 나온 비율)\n')
        f.write('5. **Confidence + Consistency 기반 필터링** 적용:\n')
        f.write('   - Consistency ≥ 0.67 & Avg Confidence ≥ 0.80: 자동 수용\n')
        f.write('   - Consistency ≥ 0.67 & Avg Confidence 0.50~0.80: 추가 검증\n')
        f.write('   - Consistency < 0.67 또는 Avg Confidence < 0.50: 수동 검토\n')
        f.write('6. 검증 결과 및 이력을 데이터베이스에 저장\n')
        f.write('\n')
    
    print(f"[OK] 리포트 저장: {report_path}")
    return report_path


def main():
    """메인 함수"""
    import sys
    
    print("=" * 80)
    print("[START] LLM 전처리 성공 항목 검증 시작 (Inclusion/Exclusion)")
    print("=" * 80)
    
    api_keys = get_api_keys()
    if not api_keys:
        print("\n[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        print("환경변수에 GEMINI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        sys.exit(1)
    
    # 명령줄 인자 파싱
    # 사용법: python llm_validate_inclusion_exclusion.py [limit] [num_validations] [batch_size] [start_batch]
    limit = None
    num_validations = 3  # 기본값: 3회
    custom_batch_size = None
    start_batch = 1
    
    num_args = []
    for arg in sys.argv[1:]:
        try:
            num_args.append(int(arg))
        except ValueError:
            pass
    
    if len(num_args) > 0:
        limit = num_args[0]
    if len(num_args) > 1:
        num_validations = num_args[1]
    if len(num_args) > 2:
        custom_batch_size = num_args[2]
    if len(num_args) > 3:
        start_batch = num_args[3]
        if start_batch < 1:
            start_batch = 1
    
    print(f"\n[INFO] 사용 가능한 API 키: {len(api_keys)}개")
    print(f"[INFO] 사용 모델: {GEMINI_MODEL}")
    print(f"[INFO] 다중 검증 횟수: {num_validations}회")
    
    # 배치 크기 조정
    if custom_batch_size and custom_batch_size > 0:
        import llm_config
        llm_config.BATCH_SIZE = custom_batch_size
        print(f"[INFO] 배치 크기를 {custom_batch_size}개로 조정했습니다.")
    
    if start_batch > 1:
        print(f"[INFO] 배치 {start_batch}번부터 시작합니다.")
    
    try:
        conn = get_db_connection()
        
        # SUCCESS 항목 조회 (재검증 포함)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    nct_id,
                    eligibility_criteria_raw,
                    inclusion_criteria,
                    exclusion_criteria
                FROM inclusion_exclusion_llm_preprocessed
                WHERE llm_status = 'SUCCESS'
                ORDER BY nct_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            eligibility_list = cur.fetchall()
        
        total_count = len(eligibility_list)
        print(f"\n[INFO] 처리할 SUCCESS 항목: {total_count:,}개")
        
        if total_count == 0:
            print("[INFO] 처리할 항목이 없습니다.")
            # 리포트만 생성
            print("\n[STEP] 검증 결과 리포트 생성 중...")
            generate_validation_report(conn)
            conn.close()
            return
        
        # LLM 다중 검증 (배치 처리)
        import llm_config
        actual_batch_size = llm_config.BATCH_SIZE
        print(f"\n[STEP 1] LLM 다중 검증 시작 (배치 크기: {actual_batch_size}, 항목당 {num_validations}회 검증)...")
        
        verified_count = 0
        uncertain_count = 0
        inclusion_failed_count = 0
        exclusion_failed_count = 0
        both_failed_count = 0
        manual_review_count = 0
        high_consistency_count = 0
        medium_consistency_count = 0
        low_consistency_count = 0
        
        # 배치 단위로 처리
        for batch_start in range(0, total_count, actual_batch_size):
            batch_end = min(batch_start + actual_batch_size, total_count)
            batch_eligibility = eligibility_list[batch_start:batch_end]
            batch_num = (batch_start // actual_batch_size) + 1
            total_batches = (total_count + actual_batch_size - 1) // actual_batch_size
            
            # start_batch 옵션: 지정된 배치부터 시작
            if batch_num < start_batch:
                print(f"  배치 {batch_num}/{total_batches} 건너뜀 (start_batch={start_batch})")
                continue
            
            print(f"  배치 {batch_num}/{total_batches} 처리 중: {batch_start + 1:,}~{batch_end:,}번째 항목")
            
            # 모든 키가 소진되었는지 확인
            import llm_config
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 처리 중단합니다.")
                break
            
            # 배치 단위로 다중 검증 수행 (기존 이력과 합치기 위해 conn 전달)
            batch_results, validation_results_by_run = validate_batch_eligibility(batch_eligibility, num_validations, conn)
            
            # 모든 키가 소진되었는지 다시 확인
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 처리 중단합니다.")
                break
            
            # 결과 집계
            for result in batch_results:
                status = result.get('final_status', '')
                consistency = result.get('consistency_score', 0.0)
                
                if status == 'VERIFIED':
                    verified_count += 1
                elif status == 'UNCERTAIN':
                    uncertain_count += 1
                elif status == 'INCLUSION_FAILED':
                    inclusion_failed_count += 1
                elif status == 'EXCLUSION_FAILED':
                    exclusion_failed_count += 1
                elif status == 'BOTH_FAILED':
                    both_failed_count += 1
                
                if result.get('needs_manual_review', False):
                    manual_review_count += 1
                
                if consistency >= 0.67:
                    high_consistency_count += 1
                elif consistency >= 0.33:
                    medium_consistency_count += 1
                else:
                    low_consistency_count += 1
            
            # Rate limiting (배치 간 대기)
            time.sleep(60 / MAX_REQUESTS_PER_MINUTE)
            
            # 배치마다 DB 저장
            if batch_results:
                print(f"  배치 {batch_num} 결과 저장 중... ({len(batch_results)}개)")
                update_validation_results(conn, batch_results, validation_results_by_run)
            
            # 모든 키가 소진되었으면 배치 루프도 중단
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 배치 처리 중단합니다.")
                break
        
        print(f"\n[INFO] 처리 완료:")
        print(f"  전체: {total_count:,}개")
        print(f"  VERIFIED: {verified_count:,}개 ({verified_count/total_count*100:.1f}%)")
        print(f"  UNCERTAIN: {uncertain_count:,}개 ({uncertain_count/total_count*100:.1f}%)")
        print(f"  INCLUSION_FAILED: {inclusion_failed_count:,}개 ({inclusion_failed_count/total_count*100:.1f}%)")
        print(f"  EXCLUSION_FAILED: {exclusion_failed_count:,}개 ({exclusion_failed_count/total_count*100:.1f}%)")
        print(f"  BOTH_FAILED: {both_failed_count:,}개 ({both_failed_count/total_count*100:.1f}%)")
        print(f"\n[INFO] 일관성 점수 분포:")
        print(f"  높은 일관성 (≥0.67): {high_consistency_count:,}개 ({high_consistency_count/total_count*100:.1f}%)")
        print(f"  중간 일관성 (0.33~0.67): {medium_consistency_count:,}개 ({medium_consistency_count/total_count*100:.1f}%)")
        print(f"  낮은 일관성 (<0.33): {low_consistency_count:,}개 ({low_consistency_count/total_count*100:.1f}%)")
        print(f"\n[INFO] 수동 검토 필요: {manual_review_count:,}개 ({manual_review_count/total_count*100:.1f}%)")
        
        # 리포트 생성
        print("\n[STEP 2] 검증 결과 리포트 생성 중...")
        generate_validation_report(conn)
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

