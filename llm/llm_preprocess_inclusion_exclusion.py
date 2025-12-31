"""
전체 데이터 LLM 전처리 스크립트 (Inclusion/Exclusion)

inclusion_exclusion_raw 테이블의 모든 데이터를 LLM으로 전처리하여 
inclusion_exclusion_llm_preprocessed 테이블에 저장합니다.
"""

import os
import json
import time
from typing import Dict, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
from llm_config import (
    get_api_keys, get_client, switch_to_next_api_key, GEMINI_MODEL,
    MAX_REQUESTS_PER_MINUTE, BATCH_SIZE, MAX_RETRIES, RETRY_DELAY
)
from llm_prompts import get_inclusion_exclusion_preprocess_prompt

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


def call_gemini_api(prompt: str, nct_id_list: List[str] = None) -> Optional[List]:
    """Gemini API 호출 (여러 API 키를 순차적으로 시도, 429 에러 시 자동 전환)"""
    api_keys = get_api_keys()
    if not api_keys:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        return None
    
    # 현재 전역 키 인덱스부터 시작
    import llm_config
    start_key_index = llm_config._current_key_index
    
    last_error = None
    
    # 현재 키부터 시작 (429 에러 시에만 다음 키로 전환)
    key_index = start_key_index
    api_key = api_keys[key_index]
    
    try:
        client = get_client(api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={'temperature': 0.0}  # 전처리는 deterministic하게
        )
        
        content = response.text.strip()
        
        # 코드 블록 제거 (```json 또는 ```로 감싸진 경우)
        if '```' in content:
            import re
            # 코드 블록 패턴 매칭
            code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
            match = re.search(code_block_pattern, content, re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                # 단순히 ``` 제거
                content = re.sub(r'```(?:json)?', '', content).strip()
        
        # JSON 배열 시작 부분 찾기 (첫 번째 '[' 위치)
        json_start = content.find('[')
        if json_start >= 0:
            content = content[json_start:]
        else:
            # '['가 없으면 JSON 객체로 시작하는지 확인
            json_start = content.find('{')
            if json_start >= 0:
                # 단일 객체를 배열로 감싸기
                content = '[' + content[json_start:]
                # 마지막 '}' 뒤에 ']' 추가
                json_end = content.rfind('}')
                if json_end >= 0:
                    content = content[:json_end + 1] + ']'
        
        # JSON 배열 끝 부분 찾기 (마지막 ']' 위치)
        json_end = content.rfind(']')
        if json_end >= 0:
            content = content[:json_end + 1]
        
        # 앞뒤 공백 및 불필요한 텍스트 제거
        content = content.strip()
        
        try:
            parsed = json.loads(content)
            # 배열이 아닌 경우 배열로 변환
            if not isinstance(parsed, list):
                parsed = [parsed]
            # 성공 시 현재 키 인덱스 업데이트
            llm_config._current_key_index = key_index
            return parsed
        except json.JSONDecodeError as e:
            # "Extra data" 에러의 경우 첫 번째 JSON을 추출 시도
            if "Extra data" in str(e) or "Expecting" in str(e):
                try:
                    import re
                    # 첫 번째 완전한 JSON 배열만 추출 (더 robust한 패턴)
                    # 중괄호와 대괄호 균형을 고려하여 완전한 배열 추출
                    bracket_count = 0
                    brace_count = 0
                    array_start = -1
                    array_end = -1
                    
                    for i, char in enumerate(content):
                        if char == '[':
                            if bracket_count == 0:
                                array_start = i
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0 and array_start >= 0:
                                array_end = i
                                break
                        elif char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                    
                    if array_start >= 0 and array_end >= 0:
                        first_json = content[array_start:array_end + 1]
                        parsed = json.loads(first_json)
                        if not isinstance(parsed, list):
                            parsed = [parsed]
                        print(f"  [복구] Extra data/Expecting 에러에서 첫 번째 JSON 배열 추출 성공 ({len(parsed)}개 항목)")
                        # 복구 성공 시 현재 키 인덱스 유지
                        llm_config._current_key_index = key_index
                        return parsed
                except Exception as extra_data_error:
                    print(f"  [Extra data 복구 실패] {extra_data_error}")
            
            # JSON 파싱 실패 시 부분 파싱 시도
            print(f"[WARN] JSON 파싱 실패 (키 {key_index + 1}/{len(api_keys)}): {e}")
            print(f"  응답 내용 (처음 500자): {content[:500]}")
            
            # 잘린 JSON 복구 시도
            try:
                import re
                parsed_items = []
                
                # 방법 1: 배열의 각 요소를 추출 (최상위 레벨 객체만)
                # '{'와 '}'를 추적하여 완전한 최상위 레벨 JSON 객체 찾기
                brace_count = 0
                bracket_count = 0  # 배열 레벨 추적
                start_pos = -1
                current_obj = ""
                in_array = False
                
                for i, char in enumerate(content):
                    if char == '[':
                        bracket_count += 1
                        if bracket_count == 1:
                            in_array = True
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            in_array = False
                    elif char == '{':
                        if brace_count == 0 and in_array:
                            start_pos = i
                        brace_count += 1
                        if start_pos >= 0:
                            current_obj += char
                    elif char == '}':
                        if start_pos >= 0:
                            current_obj += char
                        brace_count -= 1
                        if brace_count == 0 and start_pos >= 0:
                            # 완전한 최상위 레벨 객체 발견
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
                
                # 방법 2: 정규식으로 최상위 레벨 객체 찾기 (중첩 구조 고려)
                if not parsed_items:
                    # 배열 내부의 최상위 객체만 매칭 (중괄호 균형 추적)
                    pattern = r'\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}'
                    json_objects = re.findall(pattern, content, re.DOTALL)
                    for obj_str in json_objects:
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict):
                                    # nct_id가 있고 유효한 경우만 추가
                                    nct_id = obj.get('nct_id')
                                    if nct_id and isinstance(nct_id, str):
                                        # 중복 체크
                                        if not any(item.get('nct_id') == nct_id for item in parsed_items):
                                            parsed_items.append(obj)
                            except json.JSONDecodeError:
                                continue
                
                # 방법 3: 배열 시작부터 순차적으로 파싱 시도 (점진적 파싱)
                if not parsed_items:
                    # '[' 이후의 각 객체를 개별적으로 파싱 시도
                    array_start = content.find('[')
                    if array_start >= 0:
                        remaining = content[array_start + 1:]
                        brace_count = 0
                        obj_start = -1
                        obj_content = ""
                        
                        for i, char in enumerate(remaining):
                            if char == '{':
                                if brace_count == 0:
                                    obj_start = i
                                brace_count += 1
                                if obj_start >= 0:
                                    obj_content += char
                            elif char == '}':
                                if obj_start >= 0:
                                    obj_content += char
                                brace_count -= 1
                                if brace_count == 0 and obj_start >= 0:
                                    try:
                                        obj = json.loads(obj_content)
                                        if isinstance(obj, dict):
                                            # nct_id가 있고 유효한 경우만 추가
                                            nct_id = obj.get('nct_id')
                                            if nct_id and isinstance(nct_id, str):
                                                # 중복 체크
                                                if not any(item.get('nct_id') == nct_id for item in parsed_items):
                                                    parsed_items.append(obj)
                                    except json.JSONDecodeError:
                                        pass
                                    obj_content = ""
                                    obj_start = -1
                            elif obj_start >= 0:
                                obj_content += char
                
                if parsed_items:
                    print(f"  [복구] {len(parsed_items)}개 항목을 부분 파싱하여 복구했습니다.")
                    # 복구된 항목에 복구 표시 추가 및 nct_id 검증/복구
                    valid_items = []
                    for idx, item in enumerate(parsed_items):
                        nct_id = item.get('nct_id')
                        # nct_id가 없거나 유효하지 않으면 순서 기반으로 복구 시도
                        if not nct_id or not isinstance(nct_id, str) or not nct_id.strip():
                            # nct_id_list가 전달된 경우 순서 기반 복구
                            if nct_id_list and idx < len(nct_id_list):
                                nct_id = nct_id_list[idx]
                                item['nct_id'] = nct_id
                                print(f"  [복구] nct_id 누락 항목을 순서 기반으로 복구: {nct_id} (인덱스 {idx})")
                            else:
                                print(f"  [경고] 복구된 항목에서 유효하지 않은 nct_id 발견 (인덱스 {idx}): {nct_id}")
                                continue
                        
                        if nct_id and isinstance(nct_id, str) and nct_id.strip():
                            if 'llm_notes' in item:
                                item['llm_notes'] = f"[PARTIAL_RECOVERED] {item.get('llm_notes', '')}"
                            else:
                                item['llm_notes'] = '[PARTIAL_RECOVERED] JSON 파싱 실패 후 부분 복구 성공.'
                            valid_items.append(item)
                    # 복구 성공 시 현재 키 인덱스 유지
                    llm_config._current_key_index = key_index
                    return valid_items if valid_items else None
            except Exception as recover_error:
                print(f"  [복구 실패] {recover_error}")
            
            # JSON 파싱 실패는 API 호출 성공이므로 같은 키를 계속 사용
            # 키 인덱스를 업데이트하지 않고 None 반환
            print(f"  [INFO] JSON 파싱 실패했지만 API 호출은 성공. 같은 키({key_index + 1}/{len(api_keys)})를 계속 사용합니다.")
            return None
    
    except Exception as e:
        error_str = str(e)
        last_error = e
        
        # 429 에러 (RESOURCE_EXHAUSTED) 체크 - 이 경우에만 다음 키로 전환
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str.upper():
            print(f"⚠️  API 키 {key_index + 1}/{len(api_keys)}에서 429 에러 발생: {error_str}")
            
            # 모든 키를 시도
            for attempt in range(len(api_keys)):
                next_key_index = (key_index + attempt + 1) % len(api_keys)
                next_api_key = api_keys[next_key_index]
                
                try:
                    print(f"🔄 다음 API 키로 전환합니다 (키 {next_key_index + 1}/{len(api_keys)})")
                    client = get_client(next_api_key)
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config={'temperature': 0.0}
                    )
                    
                    content = response.text.strip()
                    
                    # 코드 블록 제거
                    if '```' in content:
                        import re
                        code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
                        match = re.search(code_block_pattern, content, re.DOTALL)
                        if match:
                            content = match.group(1).strip()
                        else:
                            content = re.sub(r'```(?:json)?', '', content).strip()
                    
                    # JSON 배열 시작/끝 찾기
                    json_start = content.find('[')
                    if json_start >= 0:
                        content = content[json_start:]
                    else:
                        json_start = content.find('{')
                        if json_start >= 0:
                            content = '[' + content[json_start:]
                            json_end = content.rfind('}')
                            if json_end >= 0:
                                content = content[:json_end + 1] + ']'
                    
                    json_end = content.rfind(']')
                    if json_end >= 0:
                        content = content[:json_end + 1]
                    
                    content = content.strip()
                    
                    try:
                        parsed = json.loads(content)
                        if not isinstance(parsed, list):
                            parsed = [parsed]
                        # 성공 시 키 인덱스 업데이트
                        llm_config._current_key_index = next_key_index
                        return parsed
                    except json.JSONDecodeError:
                        # JSON 파싱 실패는 같은 키 계속 사용
                        llm_config._current_key_index = next_key_index
                        return None
                        
                except Exception as next_e:
                    next_error_str = str(next_e)
                    if "429" in next_error_str or "RESOURCE_EXHAUSTED" in next_error_str.upper():
                        if attempt == len(api_keys) - 1:
                            print(f"[ERROR] 모든 API 키({len(api_keys)}개)가 소진되었습니다.")
                            llm_config._previous_key_index = llm_config._current_key_index
                            llm_config._current_key_index = next_key_index
                            llm_config._all_keys_exhausted = True
                            return None
                        continue
                    else:
                        print(f"[ERROR] Gemini API 오류 (키 {next_key_index + 1}/{len(api_keys)}): {next_error_str}")
                        return None
            
            print(f"[ERROR] 모든 API 키({len(api_keys)}개) 시도 실패.")
            llm_config._all_keys_exhausted = True
            return None
        else:
            print(f"[ERROR] Gemini API 오류 (키 {key_index + 1}/{len(api_keys)}): {error_str}")
            return None


def determine_llm_status(inclusion_result, exclusion_result, notes: str = None) -> tuple:
    """
    LLM 처리 결과를 기반으로 상태와 실패 이유 결정
    
    Args:
        inclusion_result: Inclusion Criteria 구조화 결과 (배열 또는 None)
        exclusion_result: Exclusion Criteria 구조화 결과 (배열 또는 None)
        notes: LLM 응답의 notes
    
    Returns:
        (llm_status, failure_reason, formatted_notes)
    """
    has_inclusion = inclusion_result is not None and (
        (isinstance(inclusion_result, list) and len(inclusion_result) > 0) or
        (isinstance(inclusion_result, dict))
    )
    # exclusion이 빈 배열([])인 경우는 정상으로 처리 (원본에 exclusion이 없을 수 있음)
    has_exclusion = exclusion_result is not None and (
        (isinstance(exclusion_result, list)) or  # 빈 배열도 정상
        (isinstance(exclusion_result, dict))
    )
    
    # notes 형식화
    formatted_notes = notes or ''
    
    if has_inclusion and has_exclusion:
        status = 'SUCCESS'
        failure_reason = None
        if not formatted_notes:
            exclusion_count = len(exclusion_result) if isinstance(exclusion_result, list) else 0
            if exclusion_count == 0:
                formatted_notes = '[SUCCESS] Inclusion 구조화 성공. Exclusion 없음 (정상).'
            else:
                formatted_notes = '[SUCCESS] Inclusion과 Exclusion 모두 구조화 성공.'
    elif not has_inclusion and not has_exclusion:
        status = 'BOTH_FAILED'
        failure_reason = 'BOTH_FAILED'
        if not formatted_notes:
            formatted_notes = '[BOTH_FAILED] Inclusion과 Exclusion 모두 구조화 실패.'
    elif not has_inclusion:
        status = 'INCLUSION_FAILED'
        failure_reason = 'INCLUSION_FAILED'
        if not formatted_notes:
            formatted_notes = '[INCLUSION_FAILED] Inclusion 구조화 실패.'
    else:  # has_inclusion but not has_exclusion (exclusion_result가 None인 경우만 실패)
        # exclusion_result가 빈 배열([])인 경우는 이미 has_exclusion=True로 처리됨
        status = 'EXCLUSION_FAILED'
        failure_reason = 'EXCLUSION_FAILED'
        if not formatted_notes:
            formatted_notes = '[EXCLUSION_FAILED] Exclusion 구조화 실패.'
    
    return status, failure_reason, formatted_notes


def preprocess_batch_eligibility(eligibility_list: List[Dict]) -> List[Dict]:
    """배치 단위로 eligibilityCriteria를 LLM으로 전처리"""
    if not eligibility_list:
        return []
    
    # nct_id 목록 생성 (복구 시 사용)
    nct_id_list = [e.get('nct_id') for e in eligibility_list if e.get('nct_id')]
    
    # 배치 프롬프트 생성
    items = []
    for eligibility in eligibility_list:
        nct_id = eligibility.get('nct_id')
        criteria_raw = eligibility.get('eligibility_criteria_raw', '') or ''
        # 빈 값 생략하여 더 짧게
        parts = [f"{nct_id}"]
        if criteria_raw:
            parts.append(f"{criteria_raw}")
        item_str = "|".join(parts)
        items.append(item_str)
    
    # 프롬프트 생성
    items_text = '\n'.join(items)
    prompt = get_inclusion_exclusion_preprocess_prompt(items_text)
    
    result = call_gemini_api(prompt, nct_id_list)
    
    if not result:
        # API 실패 시 모두 null 처리
        return [{
            'nct_id': eligibility.get('nct_id'),
            'inclusion_criteria': None,
            'exclusion_criteria': None,
            'llm_confidence': None,
            'llm_notes': '[API_FAILED] LLM API 호출 실패.',
            'llm_status': 'API_FAILED',
            'failure_reason': 'API_FAILED'
        } for eligibility in eligibility_list]
    
    # 결과 파싱 (배열로 응답 받음)
    results = []
    if isinstance(result, list):
        # nct_id가 없는 항목들을 복구 시도
        for r in result:
            if not r.get('nct_id') or not isinstance(r.get('nct_id'), str):
                # nct_id가 없으면, 원본 데이터와 순서를 매칭 시도
                # (배치 내에서 순서가 유지된다고 가정)
                idx = result.index(r)
                if idx < len(nct_id_list):
                    r['nct_id'] = nct_id_list[idx]
                    print(f"  [복구] nct_id 누락 항목을 순서 기반으로 복구: {r['nct_id']}")
        
        # nct_id로 매핑 (nct_id가 있고 유효한 것만)
        result_map = {}
        unmatched_results = []  # nct_id가 없는 결과들
        for idx, r in enumerate(result):
            nct_id = r.get('nct_id')
            if nct_id and isinstance(nct_id, str):
                # 중복이 있으면 첫 번째 것만 사용
                if nct_id not in result_map:
                    result_map[nct_id] = r
                else:
                    print(f"  [경고] 중복된 nct_id 발견: {nct_id}, 첫 번째 항목 사용")
            else:
                # nct_id가 없으면 순서 기반으로 복구 시도
                if idx < len(nct_id_list):
                    recovered_nct_id = nct_id_list[idx]
                    r['nct_id'] = recovered_nct_id
                    result_map[recovered_nct_id] = r
                    print(f"  [복구] 매핑 단계에서 nct_id 복구: {recovered_nct_id} (인덱스 {idx})")
                else:
                    unmatched_results.append((idx, r))
        
        # 매핑되지 않은 결과가 있으면 순서 기반으로 추가 복구 시도
        if unmatched_results:
            used_indices = set()
            for idx, r in unmatched_results:
                # 이미 사용된 인덱스 제외하고 순서대로 할당
                for i, nct_id in enumerate(nct_id_list):
                    if i not in used_indices and nct_id not in result_map:
                        r['nct_id'] = nct_id
                        result_map[nct_id] = r
                        used_indices.add(i)
                        print(f"  [복구] 매핑 실패 항목을 순서 기반으로 복구: {nct_id} (인덱스 {i})")
                        break
        
        for eligibility in eligibility_list:
            nct_id = eligibility.get('nct_id')
            if nct_id in result_map:
                r = result_map[nct_id]
                # inclusion_criteria와 exclusion_criteria를 JSONB로 변환
                inclusion_criteria = r.get('inclusion_criteria')
                exclusion_criteria = r.get('exclusion_criteria')
                
                # 빈 배열도 JSON으로 변환 (None이 아닌 빈 배열로 저장)
                inclusion_json = json.dumps(inclusion_criteria) if inclusion_criteria is not None else None
                exclusion_json = json.dumps(exclusion_criteria) if exclusion_criteria is not None else None
                
                notes = r.get('notes', '')
                
                # 상태 및 실패 이유 결정
                status, failure_reason, formatted_notes = determine_llm_status(
                    inclusion_criteria, exclusion_criteria, notes
                )
                
                results.append({
                    'nct_id': nct_id,
                    'inclusion_criteria': inclusion_json,
                    'exclusion_criteria': exclusion_json,
                    'llm_confidence': r.get('confidence'),
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
            else:
                # 응답에 nct_id가 없는 경우 (모든 복구 시도 실패)
                status, failure_reason, formatted_notes = determine_llm_status(
                    None, None, '[PARSE_ERROR] LLM 응답에 nct_id가 없음. 모든 복구 시도 실패.'
                )
                results.append({
                    'nct_id': nct_id,
                    'inclusion_criteria': None,
                    'exclusion_criteria': None,
                    'llm_confidence': None,
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
    else:
        # 단일 응답인 경우 (하위 호환성)
        if eligibility_list:
            eligibility = eligibility_list[0]
            inclusion_criteria = result.get('inclusion_criteria')
            exclusion_criteria = result.get('exclusion_criteria')
            
            # 빈 배열도 JSON으로 변환 (None이 아닌 빈 배열로 저장)
            inclusion_json = json.dumps(inclusion_criteria) if inclusion_criteria is not None else None
            exclusion_json = json.dumps(exclusion_criteria) if exclusion_criteria is not None else None
            
            notes = result.get('notes', '')
            
            # 상태 및 실패 이유 결정
            status, failure_reason, formatted_notes = determine_llm_status(
                inclusion_criteria, exclusion_criteria, notes
            )
            
            results.append({
                'nct_id': eligibility.get('nct_id'),
                'inclusion_criteria': inclusion_json,
                'exclusion_criteria': exclusion_json,
                'llm_confidence': result.get('confidence'),
                'llm_notes': formatted_notes,
                'llm_status': status,
                'failure_reason': failure_reason
            })
    
    return results


def insert_llm_results(conn, eligibility_list: List[Dict], results: List[Dict]):
    """LLM 전처리 결과를 inclusion_exclusion_llm_preprocessed 테이블에 삽입"""
    if not results or not eligibility_list:
        return
    
    # eligibility와 result를 nct_id로 매핑
    result_map = {r['nct_id']: r for r in results}
    
    insert_data = []
    for eligibility in eligibility_list:
        nct_id = eligibility.get('nct_id')
        result = result_map.get(nct_id, {})
        
        # VARCHAR 길이 제한 적용
        llm_status = result.get('llm_status')
        if llm_status and len(llm_status) > 20:
            llm_status = llm_status[:20]
        
        failure_reason = result.get('failure_reason')
        if failure_reason and len(failure_reason) > 50:
            failure_reason = failure_reason[:50]
        
        insert_data.append({
            'nct_id': nct_id,
            'eligibility_criteria_raw': eligibility.get('eligibility_criteria_raw'),
            'phase': eligibility.get('phase'),
            'inclusion_criteria': result.get('inclusion_criteria'),
            'exclusion_criteria': result.get('exclusion_criteria'),
            'llm_confidence': result.get('llm_confidence'),
            'llm_notes': result.get('llm_notes'),
            'llm_status': llm_status,
            'failure_reason': failure_reason
        })
    
    insert_sql = """
        INSERT INTO inclusion_exclusion_llm_preprocessed (
            nct_id, eligibility_criteria_raw, phase,
            inclusion_criteria, exclusion_criteria,
            llm_confidence, llm_notes, llm_status, failure_reason, parsing_method
        ) VALUES (
            %(nct_id)s, %(eligibility_criteria_raw)s, %(phase)s,
            %(inclusion_criteria)s::jsonb, %(exclusion_criteria)s::jsonb,
            %(llm_confidence)s, %(llm_notes)s, %(llm_status)s, %(failure_reason)s, 'LLM'
        )
        ON CONFLICT (nct_id) 
        DO UPDATE SET
            inclusion_criteria = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.inclusion_criteria
                ELSE EXCLUDED.inclusion_criteria
            END,
            exclusion_criteria = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.exclusion_criteria
                ELSE EXCLUDED.exclusion_criteria
            END,
            llm_confidence = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.llm_confidence
                ELSE EXCLUDED.llm_confidence
            END,
            llm_notes = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.llm_notes
                ELSE EXCLUDED.llm_notes
            END,
            llm_status = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.llm_status
                ELSE EXCLUDED.llm_status
            END,
            failure_reason = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.failure_reason
                ELSE EXCLUDED.failure_reason
            END,
            updated_at = CASE 
                WHEN inclusion_exclusion_llm_preprocessed.llm_status = 'SUCCESS' THEN inclusion_exclusion_llm_preprocessed.updated_at
                ELSE CURRENT_TIMESTAMP
            END
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, insert_data, page_size=100)
        conn.commit()


def create_table_if_not_exists(conn):
    """inclusion_exclusion_llm_preprocessed 테이블 생성 (없는 경우)"""
    with conn.cursor() as cur:
        # 테이블 존재 여부 확인
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'inclusion_exclusion_llm_preprocessed'
            )
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            print("[INFO] inclusion_exclusion_llm_preprocessed 테이블이 없습니다. 생성합니다...")
            # SQL 파일 읽기
            sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql', 'create_inclusion_exclusion_llm_preprocessed.sql')
            if os.path.exists(sql_file):
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                cur.execute(sql_content)
                conn.commit()
                print("[OK] 테이블 생성 완료")
            else:
                print(f"[ERROR] SQL 파일을 찾을 수 없습니다: {sql_file}")
                raise FileNotFoundError(f"SQL 파일을 찾을 수 없습니다: {sql_file}")
        else:
            print("[INFO] inclusion_exclusion_llm_preprocessed 테이블이 이미 존재합니다.")


def main():
    """메인 함수"""
    import sys
    
    print("=" * 80)
    print("[START] 전체 데이터 LLM 전처리 시작 (Inclusion/Exclusion)")
    print("=" * 80)
    
    api_keys = get_api_keys()
    if not api_keys:
        print("\n[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        print("환경변수에 GEMINI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        sys.exit(1)
    
    print(f"\n[INFO] 사용 가능한 API 키: {len(api_keys)}개")
    print(f"[INFO] 사용 모델: {GEMINI_MODEL}")
    print(f"[INFO] 배치 크기: {BATCH_SIZE}개")
    
    # 명령줄 인자 파싱
    # 사용법: python llm_preprocess_inclusion_exclusion.py [limit] [batch_size] [start_batch] [--failed-only|--missing-only|--all]
    limit = None
    custom_batch_size = None
    start_batch = 1
    mode = 'missing'  # 기본값: 누락된 항목만 처리
    
    # 옵션 파싱 (--로 시작하는 인자 먼저 처리)
    for arg in sys.argv[1:]:
        if arg in ['--failed-only', '--missing-only', '--all']:
            mode = arg.replace('--', '')
            break
    
    # 숫자 인자 파싱 (옵션 제외)
    num_args = [arg for arg in sys.argv[1:] if arg not in ['--failed-only', '--missing-only', '--all']]
    
    if len(num_args) > 0:
        try:
            limit = int(num_args[0])
        except ValueError:
            pass
    
    if len(num_args) > 1:
        try:
            custom_batch_size = int(num_args[1])
        except ValueError:
            pass
    
    if len(num_args) > 2:
        try:
            start_batch = int(num_args[2])
            if start_batch < 1:
                start_batch = 1
        except ValueError:
            pass
    
    # 모드 출력
    mode_names = {
        'failed-only': '실패한 항목만 재처리',
        'missing-only': '누락된 항목만 처리',
        'all': '전체 처리 (기존 SUCCESS 항목은 보호됨)'
    }
    print(f"[INFO] 처리 모드: {mode_names.get(mode, mode)}")
    
    # 배치 크기 조정
    if custom_batch_size and custom_batch_size > 0:
        import llm_config
        llm_config.BATCH_SIZE = custom_batch_size
        print(f"[INFO] 배치 크기를 {custom_batch_size}개로 조정했습니다.")
    
    if start_batch > 1:
        print(f"[INFO] 배치 {start_batch}번부터 시작합니다.")
    
    try:
        conn = get_db_connection()
        
        # 테이블 생성 확인
        create_table_if_not_exists(conn)
        
        # 처리할 항목 조회 (inclusion_exclusion_raw에서 전체 데이터)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if mode == 'failed-only':
                # 실패한 항목만 재처리 (SUCCESS 제외)
                query = """
                    SELECT 
                        ier.nct_id,
                        ier.eligibility_criteria_raw,
                        ier.phase
                    FROM inclusion_exclusion_raw ier
                    INNER JOIN inclusion_exclusion_llm_preprocessed iep
                        ON ier.nct_id = iep.nct_id
                    WHERE iep.llm_status != 'SUCCESS'
                    ORDER BY ier.nct_id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                eligibility_list = cur.fetchall()
                
            elif mode == 'missing-only':
                # 누락된 항목만 처리 (inclusion_exclusion_llm_preprocessed에 없는 항목)
                query = """
                    SELECT 
                        ier.nct_id,
                        ier.eligibility_criteria_raw,
                        ier.phase
                    FROM inclusion_exclusion_raw ier
                    LEFT JOIN inclusion_exclusion_llm_preprocessed iep
                        ON ier.nct_id = iep.nct_id
                    WHERE iep.nct_id IS NULL
                    ORDER BY ier.nct_id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                eligibility_list = cur.fetchall()
                
            else:  # mode == 'all'
                # 전체 처리 (기존 SUCCESS 항목은 건드리지 않음 - INSERT 시 CASE 문으로 처리)
                query = """
                    SELECT 
                        nct_id,
                        eligibility_criteria_raw,
                        phase
                    FROM inclusion_exclusion_raw
                    ORDER BY nct_id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                eligibility_list = cur.fetchall()
        
        total_count = len(eligibility_list)
        print(f"\n[INFO] 처리할 항목: {total_count:,}개")
        
        if total_count == 0:
            print("[INFO] 처리할 항목이 없습니다.")
            conn.close()
            return
        
        # LLM 전처리 (배치 처리)
        import llm_config
        actual_batch_size = llm_config.BATCH_SIZE
        print(f"\n[STEP 1] LLM 전처리 시작 (배치 크기: {actual_batch_size})...")
        all_results = []
        success_count = 0
        failed_count = 0
        inclusion_failed_count = 0
        exclusion_failed_count = 0
        both_failed_count = 0
        
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
            
            # 배치 단위로 한번에 API 호출
            batch_results = preprocess_batch_eligibility(batch_eligibility)
            
            # 모든 키가 소진되었는지 다시 확인
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 처리 중단합니다.")
                break
            
            # 결과 집계
            for result in batch_results:
                all_results.append(result)
                status = result.get('llm_status', '')
                if status == 'SUCCESS':
                    success_count += 1
                elif status == 'INCLUSION_FAILED':
                    inclusion_failed_count += 1
                    failed_count += 1
                elif status == 'EXCLUSION_FAILED':
                    exclusion_failed_count += 1
                    failed_count += 1
                elif status == 'BOTH_FAILED':
                    both_failed_count += 1
                    failed_count += 1
                else:
                    failed_count += 1
            
            # Rate limiting
            time.sleep(60 / MAX_REQUESTS_PER_MINUTE)
            
            # 배치마다 DB 저장
            if batch_results:
                print(f"  배치 {batch_num} 결과 저장 중... ({len(batch_results)}개)")
                insert_llm_results(conn, batch_eligibility, batch_results)
            
            # 모든 키가 소진되었으면 배치 루프도 중단
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 배치 처리 중단합니다.")
                break
        
        print(f"\n[INFO] 처리 완료:")
        print(f"  전체: {total_count:,}개")
        print(f"  성공 (Inclusion + Exclusion): {success_count:,}개 ({success_count/total_count*100:.1f}%)")
        print(f"  실패: {failed_count:,}개 ({failed_count/total_count*100:.1f}%)")
        if inclusion_failed_count > 0:
            print(f"    - Inclusion만 실패: {inclusion_failed_count:,}개")
        if exclusion_failed_count > 0:
            print(f"    - Exclusion만 실패: {exclusion_failed_count:,}개")
        if both_failed_count > 0:
            print(f"    - 둘 다 실패: {both_failed_count:,}개")
        
        # 최종 통계
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN llm_status = 'SUCCESS' THEN 1 END) as success,
                    COUNT(CASE WHEN llm_status = 'INCLUSION_FAILED' THEN 1 END) as inclusion_failed,
                    COUNT(CASE WHEN llm_status = 'EXCLUSION_FAILED' THEN 1 END) as exclusion_failed,
                    COUNT(CASE WHEN llm_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                    COUNT(CASE WHEN llm_status = 'API_FAILED' THEN 1 END) as api_failed,
                    COUNT(inclusion_criteria) as with_inclusion,
                    COUNT(exclusion_criteria) as with_exclusion,
                    COUNT(CASE WHEN inclusion_criteria IS NOT NULL AND exclusion_criteria IS NOT NULL THEN 1 END) as complete
                FROM inclusion_exclusion_llm_preprocessed
            """)
            stats = cur.fetchone()
            print(f"\n[최종 통계]")
            print(f"  저장된 항목: {stats['total']:,}개")
            print(f"\n[상태별 통계]")
            print(f"  성공 (SUCCESS): {stats['success']:,}개 ({stats['success']/stats['total']*100:.1f}%)")
            print(f"  Inclusion 실패: {stats['inclusion_failed']:,}개 ({stats['inclusion_failed']/stats['total']*100:.1f}%)")
            print(f"  Exclusion 실패: {stats['exclusion_failed']:,}개 ({stats['exclusion_failed']/stats['total']*100:.1f}%)")
            print(f"  모두 실패: {stats['both_failed']:,}개 ({stats['both_failed']/stats['total']*100:.1f}%)")
            print(f"  API 실패: {stats['api_failed']:,}개 ({stats['api_failed']/stats['total']*100:.1f}%)")
            print(f"\n[추출 통계]")
            print(f"  Inclusion 추출: {stats['with_inclusion']:,}개 ({stats['with_inclusion']/stats['total']*100:.1f}%)")
            print(f"  Exclusion 추출: {stats['with_exclusion']:,}개 ({stats['with_exclusion']/stats['total']*100:.1f}%)")
            print(f"  완전 파싱: {stats['complete']:,}개 ({stats['complete']/stats['total']*100:.1f}%)")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

