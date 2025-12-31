"""
전체 데이터 LLM 전처리 스크립트

outcome_raw 테이블의 모든 데이터를 LLM으로 전처리하여 
outcome_llm_preprocessed 테이블에 저장합니다.
"""

import os
import json
import time
from typing import Dict, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
from llm_config import (
    get_api_keys, GEMINI_MODEL,
    MAX_REQUESTS_PER_MINUTE, BATCH_SIZE, MAX_RETRIES, RETRY_DELAY
)
from llm_prompts import get_preprocess_initial_prompt

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def call_gemini_api(prompt: str) -> Optional[Dict]:
    """Gemini API 호출 (여러 API 키를 순차적으로 시도, 429 에러 시 자동 전환)"""
    api_keys = get_api_keys()
    if not api_keys:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        return None
    
    # 현재 전역 키 인덱스부터 시작
    import llm_config
    start_key_index = llm_config._current_key_index
    
    last_error = None
    
    # 모든 키를 시도
    for attempt in range(len(api_keys)):
        key_index = (start_key_index + attempt) % len(api_keys)
        
        try:
            # 특정 키로 클라이언트 생성
            from google import genai
            client = genai.Client(api_key=api_keys[key_index])
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            
            # 성공 시 전역 인덱스 업데이트
            if llm_config._current_key_index != key_index:
                llm_config._previous_key_index = llm_config._current_key_index
                llm_config._current_key_index = key_index
            else:
                llm_config._current_key_index = key_index
            
            # 응답 텍스트 추출
            content = response.text.strip()
            
            # 코드 블록 제거 (```json 또는 ```로 감싸진 경우)
            if '```' in content:
                # ```json 또는 ```로 시작하는 블록 찾기
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
                return parsed
            except json.JSONDecodeError as e:
                # JSON 파싱 실패 시 부분 파싱 시도
                print(f"[WARN] JSON 파싱 실패 (키 {key_index + 1}/{len(api_keys)}): {e}")
                print(f"  응답 내용 (처음 500자): {content[:500]}")
                
                # 잘린 JSON 복구 시도
                try:
                    import re
                    # 중첩된 JSON 객체를 포함한 패턴 (더 정교한 매칭)
                    # 각 객체를 찾되, 중첩된 구조도 처리
                    parsed_items = []
                    brace_count = 0
                    start_pos = -1
                    current_obj = ""
                    
                    # '{'와 '}'를 추적하여 완전한 JSON 객체 찾기
                    for i, char in enumerate(content):
                        if char == '{':
                            if brace_count == 0:
                                start_pos = i
                            brace_count += 1
                            current_obj += char
                        elif char == '}':
                            current_obj += char
                            brace_count -= 1
                            if brace_count == 0:
                                # 완전한 객체 발견
                                try:
                                    obj = json.loads(current_obj)
                                    if isinstance(obj, dict) and 'outcome_id' in obj:
                                        parsed_items.append(obj)
                                except json.JSONDecodeError:
                                    pass
                                current_obj = ""
                                start_pos = -1
                        elif start_pos >= 0:
                            current_obj += char
                    
                    # 정규식으로도 시도 (간단한 경우)
                    if not parsed_items:
                        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                        for obj_str in json_objects:
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict) and 'outcome_id' in obj:
                                    parsed_items.append(obj)
                            except json.JSONDecodeError:
                                continue
                    
                    if parsed_items:
                        print(f"  [복구] {len(parsed_items)}개 항목을 부분 파싱하여 복구했습니다.")
                        # 복구된 항목에 복구 표시 추가
                        for item in parsed_items:
                            if 'notes' in item:
                                item['notes'] = f"[PARTIAL_RECOVERED] {item.get('notes', '')}"
                            else:
                                item['notes'] = '[PARTIAL_RECOVERED] JSON 파싱 실패 후 부분 복구 성공.'
                        return parsed_items
                except Exception as recover_error:
                    print(f"  [복구 실패] {recover_error}")
                
                # 복구 실패 시 None 반환
                return None
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            # 429 에러 (RESOURCE_EXHAUSTED) 체크
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


def determine_llm_status(measure_code, time_value, time_unit, notes: str = None, has_time_frame_raw: bool = True) -> tuple:
    """
    LLM 처리 결과를 기반으로 상태와 실패 이유 결정
    
    Args:
        measure_code: 추출된 measure_code
        time_value: 추출된 time_value
        time_unit: 추출된 time_unit
        notes: LLM 응답의 notes
        has_time_frame_raw: 원본에 time_frame_raw가 있는지 여부
    
    Returns:
        (llm_status, failure_reason, formatted_notes, time_value, time_unit)
    """
    has_measure = measure_code is not None and measure_code != ''
    has_time = time_value is not None and time_unit is not None
    
    # notes 형식화
    formatted_notes = notes or ''
    
    # time_frame_raw가 없는 경우: time_value=0, time_unit=null로 처리하되 SUCCESS로 처리
    if has_measure and not has_time_frame_raw:
        status = 'SUCCESS'
        failure_reason = None
        time_value = 0
        time_unit = None
        if not formatted_notes:
            formatted_notes = '[SUCCESS] measure_code 추출 성공. time_frame 정보 없음 (time_value=0).'
        return status, failure_reason, formatted_notes, time_value, time_unit
    
    if has_measure and has_time:
        status = 'SUCCESS'
        failure_reason = None
        if not formatted_notes:
            formatted_notes = '[SUCCESS] measure_code와 time 정보 모두 추출 성공.'
    elif not has_measure and not has_time:
        status = 'BOTH_FAILED'
        failure_reason = 'BOTH_FAILED'
        if not formatted_notes:
            formatted_notes = '[BOTH_FAILED] measure_code와 time 정보 모두 추출 실패.'
    elif not has_measure:
        status = 'MEASURE_FAILED'
        failure_reason = 'MEASURE_FAILED'
        if not formatted_notes:
            formatted_notes = '[MEASURE_FAILED] measure_code 추출 실패.'
    else:  # not has_time
        status = 'TIMEFRAME_FAILED'
        failure_reason = 'TIMEFRAME_FAILED'
        if not formatted_notes:
            formatted_notes = '[TIMEFRAME_FAILED] time 정보 추출 실패.'
    
    return status, failure_reason, formatted_notes, time_value, time_unit


def preprocess_batch_outcomes(outcomes: List[Dict]) -> List[Dict]:
    """배치 단위로 outcome들을 LLM으로 전처리"""
    if not outcomes:
        return []
    
    # 배치 프롬프트 생성
    items = []
    for outcome in outcomes:
        oid = outcome.get('id')  # outcome_raw는 id 사용
        mr = outcome.get('measure_raw', '') or ''
        dr = outcome.get('description_raw', '') or ''
        tr = outcome.get('time_frame_raw', '') or ''
        # 빈 값 생략하여 더 짧게
        parts = [f"{oid}"]
        if mr: parts.append(f"M:{mr}")
        if dr: parts.append(f"D:{dr}")
        if tr: parts.append(f"T:{tr}")
        item_str = "|".join(parts)
        items.append(item_str)
    
    # 프롬프트 생성
    items_text = '\n'.join(items)
    prompt = get_preprocess_initial_prompt(items_text)
    
    result = call_gemini_api(prompt)
    
    if not result:
        # API 실패 시 모두 null 처리
        return [{
            'outcome_id': outcome.get('id'),
            'llm_measure_code': None,
            'llm_time_value': None,
            'llm_time_unit': None,
            'llm_time_points': None,
            'llm_confidence': None,
            'llm_notes': '[API_FAILED] LLM API 호출 실패.',
            'llm_status': 'API_FAILED',
            'failure_reason': 'API_FAILED'
        } for outcome in outcomes]
    
    # 결과 파싱 (배열로 응답 받음)
    results = []
    if isinstance(result, list):
        # outcome_id로 매핑
        result_map = {r.get('outcome_id'): r for r in result if 'outcome_id' in r}
        for outcome in outcomes:
            outcome_id = outcome.get('id')
            if outcome_id in result_map:
                r = result_map[outcome_id]
                # time_points를 JSONB로 변환
                time_points = r.get('time_points')
                if time_points and isinstance(time_points, list):
                    time_points_json = json.dumps(time_points)
                else:
                    time_points_json = None
                
                measure_code = r.get('measure_code')
                time_value = r.get('time_value')
                time_unit = r.get('time_unit')
                notes = r.get('notes', '')
                
                # time_frame_raw 존재 여부 확인
                time_frame_raw = outcome.get('time_frame_raw') or ''
                has_time_frame_raw = bool(time_frame_raw and time_frame_raw.strip())
                
                # 상태 및 실패 이유 결정
                status, failure_reason, formatted_notes, final_time_value, final_time_unit = determine_llm_status(
                    measure_code, time_value, time_unit, notes, has_time_frame_raw
                )
                
                results.append({
                    'outcome_id': outcome_id,
                    'llm_measure_code': measure_code,
                    'llm_time_value': final_time_value,
                    'llm_time_unit': final_time_unit,
                    'llm_time_points': time_points_json,
                    'llm_confidence': r.get('confidence'),
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
            else:
                # 응답에 outcome_id가 없는 경우
                time_frame_raw = outcome.get('time_frame_raw') or ''
                has_time_frame_raw = bool(time_frame_raw and time_frame_raw.strip())
                status, failure_reason, formatted_notes, final_time_value, final_time_unit = determine_llm_status(
                    None, None, None, '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.', has_time_frame_raw
                )
                results.append({
                    'outcome_id': outcome_id,
                    'llm_measure_code': None,
                    'llm_time_value': final_time_value,
                    'llm_time_unit': final_time_unit,
                    'llm_time_points': None,
                    'llm_confidence': None,
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
    else:
        # 단일 응답인 경우 (하위 호환성)
        if outcomes:
            outcome = outcomes[0]
            time_points = result.get('time_points')
            if time_points and isinstance(time_points, list):
                time_points_json = json.dumps(time_points)
            else:
                time_points_json = None
            
            measure_code = result.get('measure_code')
            time_value = result.get('time_value')
            time_unit = result.get('time_unit')
            notes = result.get('notes', '')
            
            # time_frame_raw 존재 여부 확인
            time_frame_raw = outcome.get('time_frame_raw') or ''
            has_time_frame_raw = bool(time_frame_raw and time_frame_raw.strip())
            
            # 상태 및 실패 이유 결정
            status, failure_reason, formatted_notes, final_time_value, final_time_unit = determine_llm_status(
                measure_code, time_value, time_unit, notes, has_time_frame_raw
            )
            
            results.append({
                'outcome_id': outcome.get('id'),
                'llm_measure_code': measure_code,
                'llm_time_value': final_time_value,
                'llm_time_unit': final_time_unit,
                'llm_time_points': time_points_json,
                'llm_confidence': result.get('confidence'),
                'llm_notes': formatted_notes,
                'llm_status': status,
                'failure_reason': failure_reason
            })
    
    return results


def insert_llm_results(conn, outcomes: List[Dict], results: List[Dict]):
    """LLM 전처리 결과를 outcome_llm_preprocessed 테이블에 삽입"""
    if not results or not outcomes:
        return
    
    # outcome과 result를 outcome_id로 매핑
    result_map = {r['outcome_id']: r for r in results}
    
    insert_data = []
    for outcome in outcomes:
        outcome_id = outcome.get('id')
        result = result_map.get(outcome_id, {})
        
        # VARCHAR 길이 제한 적용
        llm_time_unit = result.get('llm_time_unit')
        if llm_time_unit and len(llm_time_unit) > 20:
            llm_time_unit = llm_time_unit[:20]
        
        llm_status = result.get('llm_status')
        if llm_status and len(llm_status) > 20:
            llm_status = llm_status[:20]
        
        failure_reason = result.get('failure_reason')
        if failure_reason and len(failure_reason) > 50:
            failure_reason = failure_reason[:50]
        
        llm_measure_code = result.get('llm_measure_code')
        if llm_measure_code and len(llm_measure_code) > 50:
            llm_measure_code = llm_measure_code[:50]
        
        insert_data.append({
            'nct_id': outcome.get('nct_id'),
            'outcome_type': outcome.get('outcome_type'),
            'outcome_order': outcome.get('outcome_order'),
            'measure_raw': outcome.get('measure_raw'),
            'description_raw': outcome.get('description_raw'),
            'time_frame_raw': outcome.get('time_frame_raw'),
            'phase': outcome.get('phase'),
            'llm_measure_code': llm_measure_code,
            'llm_time_value': result.get('llm_time_value'),
            'llm_time_unit': llm_time_unit,
            'llm_time_points': result.get('llm_time_points'),
            'llm_confidence': result.get('llm_confidence'),
            'llm_notes': result.get('llm_notes'),
            'llm_status': llm_status,
            'failure_reason': failure_reason
        })
    
    insert_sql = """
        INSERT INTO outcome_llm_preprocessed (
            nct_id, outcome_type, outcome_order,
            measure_raw, description_raw, time_frame_raw, phase,
            llm_measure_code, llm_time_value, llm_time_unit, llm_time_points,
            llm_confidence, llm_notes, llm_status, failure_reason, parsing_method
        ) VALUES (
            %(nct_id)s, %(outcome_type)s, %(outcome_order)s,
            %(measure_raw)s, %(description_raw)s, %(time_frame_raw)s, %(phase)s,
            %(llm_measure_code)s, %(llm_time_value)s, %(llm_time_unit)s, 
            %(llm_time_points)s::jsonb, %(llm_confidence)s, %(llm_notes)s, 
            %(llm_status)s, %(failure_reason)s, 'LLM'
        )
        ON CONFLICT (nct_id, outcome_type, outcome_order) 
        DO UPDATE SET
            llm_measure_code = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_measure_code
                ELSE EXCLUDED.llm_measure_code
            END,
            llm_time_value = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_time_value
                ELSE EXCLUDED.llm_time_value
            END,
            llm_time_unit = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_time_unit
                ELSE EXCLUDED.llm_time_unit
            END,
            llm_time_points = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_time_points
                ELSE EXCLUDED.llm_time_points
            END,
            llm_confidence = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_confidence
                ELSE EXCLUDED.llm_confidence
            END,
            llm_notes = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_notes
                ELSE EXCLUDED.llm_notes
            END,
            llm_status = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.llm_status
                ELSE EXCLUDED.llm_status
            END,
            failure_reason = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.failure_reason
                ELSE EXCLUDED.failure_reason
            END,
            updated_at = CASE 
                WHEN outcome_llm_preprocessed.llm_status = 'SUCCESS' THEN outcome_llm_preprocessed.updated_at
                ELSE CURRENT_TIMESTAMP
            END
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, insert_data, page_size=100)
        conn.commit()


def create_table_if_not_exists(conn):
    """outcome_llm_preprocessed 테이블 생성 (없는 경우)"""
    with conn.cursor() as cur:
        # 테이블 존재 여부 확인
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'outcome_llm_preprocessed'
            )
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            print("[INFO] outcome_llm_preprocessed 테이블이 없습니다. 생성합니다...")
            # SQL 파일 읽기
            sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql', 'create_outcome_llm_preprocessed.sql')
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
            print("[INFO] outcome_llm_preprocessed 테이블이 이미 존재합니다.")


def main():
    """메인 함수"""
    import sys
    
    print("=" * 80)
    print("[START] 전체 데이터 LLM 전처리 시작")
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
    # 사용법: python llm_preprocess_full.py [limit] [batch_size] [start_batch] [--failed-only|--missing-only|--all]
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
        
        # 처리할 항목 조회 (outcome_raw에서 전체 데이터)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if mode == 'failed-only':
                # 실패한 항목만 재처리 (SUCCESS 제외)
                query = """
                    SELECT 
                        or_data.id,
                        or_data.nct_id,
                        or_data.outcome_type,
                        or_data.outcome_order,
                        or_data.measure_raw,
                        or_data.description_raw,
                        or_data.time_frame_raw,
                        or_data.phase
                    FROM outcome_raw or_data
                    INNER JOIN outcome_llm_preprocessed olp
                        ON or_data.nct_id = olp.nct_id
                        AND or_data.outcome_type = olp.outcome_type
                        AND or_data.outcome_order = olp.outcome_order
                    WHERE olp.llm_status != 'SUCCESS'
                    ORDER BY or_data.id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                outcomes = cur.fetchall()
                
            elif mode == 'missing-only':
                # 누락된 항목만 처리 (outcome_llm_preprocessed에 없는 항목)
                query = """
                    SELECT 
                        or_data.id,
                        or_data.nct_id,
                        or_data.outcome_type,
                        or_data.outcome_order,
                        or_data.measure_raw,
                        or_data.description_raw,
                        or_data.time_frame_raw,
                        or_data.phase
                    FROM outcome_raw or_data
                    LEFT JOIN outcome_llm_preprocessed olp
                        ON or_data.nct_id = olp.nct_id
                        AND or_data.outcome_type = olp.outcome_type
                        AND or_data.outcome_order = olp.outcome_order
                    WHERE olp.nct_id IS NULL
                    ORDER BY or_data.id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                outcomes = cur.fetchall()
                
            else:  # mode == 'all'
                # 전체 처리 (기존 SUCCESS 항목은 건드리지 않음 - INSERT 시 CASE 문으로 처리)
                query = """
                    SELECT 
                        id,
                        nct_id,
                        outcome_type,
                        outcome_order,
                        measure_raw,
                        description_raw,
                        time_frame_raw,
                        phase
                    FROM outcome_raw
                    ORDER BY id
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                outcomes = cur.fetchall()
        
        total_count = len(outcomes)
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
        partial_recovered_count = 0
        
        # 배치 단위로 처리
        for batch_start in range(0, total_count, actual_batch_size):
            batch_end = min(batch_start + actual_batch_size, total_count)
            batch_outcomes = outcomes[batch_start:batch_end]
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
            batch_results = preprocess_batch_outcomes(batch_outcomes)
            
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
                elif status == 'PARTIAL_RECOVERED':
                    partial_recovered_count += 1
                    failed_count += 1  # 부분 복구도 실패로 카운트
                else:
                    failed_count += 1
            
            # Rate limiting
            time.sleep(60 / MAX_REQUESTS_PER_MINUTE)
            
            # 배치마다 DB 저장
            if batch_results:
                print(f"  배치 {batch_num} 결과 저장 중... ({len(batch_results)}개)")
                insert_llm_results(conn, batch_outcomes, batch_results)
            
            # 모든 키가 소진되었으면 배치 루프도 중단
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 배치 처리 중단합니다.")
                break
        
        print(f"\n[INFO] 처리 완료:")
        print(f"  전체: {total_count:,}개")
        print(f"  성공 (measure_code + time 파싱): {success_count:,}개 ({success_count/total_count*100:.1f}%)")
        print(f"  실패: {failed_count:,}개 ({failed_count/total_count*100:.1f}%)")
        if partial_recovered_count > 0:
            print(f"  부분 복구: {partial_recovered_count:,}개")
        
        # 최종 통계
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN llm_status = 'SUCCESS' THEN 1 END) as success,
                    COUNT(CASE WHEN llm_status = 'MEASURE_FAILED' THEN 1 END) as measure_failed,
                    COUNT(CASE WHEN llm_status = 'TIMEFRAME_FAILED' THEN 1 END) as timeframe_failed,
                    COUNT(CASE WHEN llm_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                    COUNT(CASE WHEN llm_status = 'API_FAILED' THEN 1 END) as api_failed,
                    COUNT(CASE WHEN llm_status = 'PARTIAL_RECOVERED' THEN 1 END) as partial_recovered,
                    COUNT(llm_measure_code) as with_measure,
                    COUNT(llm_time_value) as with_time,
                    COUNT(CASE WHEN llm_measure_code IS NOT NULL AND llm_time_value IS NOT NULL THEN 1 END) as complete
                FROM outcome_llm_preprocessed
            """)
            stats = cur.fetchone()
            print(f"\n[최종 통계]")
            print(f"  저장된 항목: {stats['total']:,}개")
            print(f"\n[상태별 통계]")
            print(f"  성공 (SUCCESS): {stats['success']:,}개 ({stats['success']/stats['total']*100:.1f}%)")
            print(f"  Measure 실패: {stats['measure_failed']:,}개 ({stats['measure_failed']/stats['total']*100:.1f}%)")
            print(f"  Timeframe 실패: {stats['timeframe_failed']:,}개 ({stats['timeframe_failed']/stats['total']*100:.1f}%)")
            print(f"  모두 실패: {stats['both_failed']:,}개 ({stats['both_failed']/stats['total']*100:.1f}%)")
            print(f"  API 실패: {stats['api_failed']:,}개 ({stats['api_failed']/stats['total']*100:.1f}%)")
            if stats['partial_recovered'] > 0:
                print(f"  부분 복구: {stats['partial_recovered']:,}개 ({stats['partial_recovered']/stats['total']*100:.1f}%)")
            print(f"\n[추출 통계]")
            print(f"  measure_code 추출: {stats['with_measure']:,}개 ({stats['with_measure']/stats['total']*100:.1f}%)")
            print(f"  time 추출: {stats['with_time']:,}개 ({stats['with_time']/stats['total']*100:.1f}%)")
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

