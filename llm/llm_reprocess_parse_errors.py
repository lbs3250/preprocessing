"""
PARSE_ERROR 항목 재처리 스크립트

llm_notes = '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.'인 항목들을
재처리하여 outcome_llm_preprocessed 테이블을 UPDATE합니다.
"""

import os
import json
import time
import sys
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

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
            else:
                json_start = content.find('{')
                if json_start >= 0:
                    content = '[' + content[json_start:]
                    json_end = content.rfind('}')
                    if json_end >= 0:
                        content = content[:json_end + 1] + ']'
            
            # JSON 파싱 시도
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError as e:
                # 부분 복구 시도: 개별 JSON 객체 찾기
                import re
                json_objects = []
                brace_count = 0
                current_obj = ''
                
                for char in content:
                    current_obj += char
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                obj = json.loads(current_obj.strip())
                                json_objects.append(obj)
                            except:
                                pass
                            current_obj = ''
                
                if json_objects:
                    return json_objects
                
                # 마지막 시도: 정규식으로 JSON 객체 찾기
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                matches = re.findall(json_pattern, content)
                if matches:
                    objects = []
                    for match in matches:
                        try:
                            obj = json.loads(match)
                            objects.append(obj)
                        except:
                            pass
                    if objects:
                        return objects
                
                print(f"[WARN] JSON 파싱 실패: {str(e)[:100]}")
                print(f"[WARN] 응답 일부: {content[:200]}...")
                return None
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            # 429 에러인 경우 다음 키로 전환
            if '429' in error_str or 'quota' in error_str.lower() or 'rate limit' in error_str.lower():
                print(f"[WARN] API 키 {key_index + 1}/{len(api_keys)}에서 429 에러 발생. 다음 키로 전환...")
                llm_config._current_key_index = (key_index + 1) % len(api_keys)
                time.sleep(2)  # 짧은 대기 후 재시도
                continue
            
            # 다른 에러인 경우
            print(f"[WARN] API 키 {key_index + 1}/{len(api_keys)}에서 에러 발생: {error_str[:100]}")
            time.sleep(1)
    
    print(f"[ERROR] 모든 API 키({len(api_keys)}개) 시도 실패. 마지막 에러: {str(last_error)}")
    llm_config._all_keys_exhausted = True
    return None


def determine_llm_status(measure_code, time_value, time_unit, notes: str = None) -> tuple:
    """
    LLM 처리 결과를 기반으로 상태와 실패 이유 결정
    
    Returns:
        (llm_status, failure_reason, formatted_notes)
    """
    has_measure = measure_code is not None and measure_code != ''
    has_time = time_value is not None and time_unit is not None
    
    formatted_notes = notes or ''
    
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
    
    return status, failure_reason, formatted_notes


def truncate_string(value: str, max_length: int) -> str:
    """문자열을 최대 길이로 자르기"""
    if value is None:
        return None
    if len(value) > max_length:
        return value[:max_length]
    return value


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
                
                # 상태 및 실패 이유 결정
                status, failure_reason, formatted_notes = determine_llm_status(
                    measure_code, time_value, time_unit, notes
                )
                
                # 문자열 길이 제한
                measure_code = truncate_string(measure_code, 20)
                time_unit = truncate_string(time_unit, 20)
                failure_reason = truncate_string(failure_reason, 20)
                
                results.append({
                    'outcome_id': outcome_id,
                    'llm_measure_code': measure_code,
                    'llm_time_value': time_value,
                    'llm_time_unit': time_unit,
                    'llm_time_points': time_points_json,
                    'llm_confidence': r.get('confidence'),
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
            else:
                # 응답에 outcome_id가 없는 경우
                status, failure_reason, formatted_notes = determine_llm_status(
                    None, None, None, '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.'
                )
                failure_reason = truncate_string(failure_reason, 20)
                results.append({
                    'outcome_id': outcome_id,
                    'llm_measure_code': None,
                    'llm_time_value': None,
                    'llm_time_unit': None,
                    'llm_time_points': None,
                    'llm_confidence': None,
                    'llm_notes': formatted_notes,
                    'llm_status': status,
                    'failure_reason': failure_reason
                })
    else:
        # 단일 응답인 경우 (하위 호환성)
        if outcomes:
            time_points = result.get('time_points')
            if time_points and isinstance(time_points, list):
                time_points_json = json.dumps(time_points)
            else:
                time_points_json = None
            
            measure_code = result.get('measure_code')
            time_value = result.get('time_value')
            time_unit = result.get('time_unit')
            notes = result.get('notes', '')
            
            status, failure_reason, formatted_notes = determine_llm_status(
                measure_code, time_value, time_unit, notes
            )
            
            measure_code = truncate_string(measure_code, 20)
            time_unit = truncate_string(time_unit, 20)
            failure_reason = truncate_string(failure_reason, 20)
            
            results.append({
                'outcome_id': outcomes[0].get('id'),
                'llm_measure_code': measure_code,
                'llm_time_value': time_value,
                'llm_time_unit': time_unit,
                'llm_time_points': time_points_json,
                'llm_confidence': result.get('confidence'),
                'llm_notes': formatted_notes,
                'llm_status': status,
                'failure_reason': failure_reason
            })
    
    return results


def update_llm_results(conn, outcomes: List[Dict], results: List[Dict]):
    """LLM 처리 결과를 outcome_llm_preprocessed 테이블에 UPDATE"""
    if not results:
        return
    
    # outcome_id로 매핑
    result_map = {r['outcome_id']: r for r in results}
    
    update_data = []
    for outcome in outcomes:
        outcome_id = outcome['id']
        if outcome_id in result_map:
            r = result_map[outcome_id]
            update_data.append({
                'nct_id': outcome['nct_id'],
                'outcome_type': outcome['outcome_type'],
                'outcome_order': outcome['outcome_order'],
                'llm_measure_code': r['llm_measure_code'],
                'llm_time_value': r['llm_time_value'],
                'llm_time_unit': r['llm_time_unit'],
                'llm_time_points': r['llm_time_points'],
                'llm_confidence': r['llm_confidence'],
                'llm_notes': r['llm_notes'],
                'llm_status': r['llm_status'],
                'failure_reason': r['failure_reason']
            })
    
    if not update_data:
        return
    
    update_sql = """
        UPDATE outcome_llm_preprocessed
        SET
            llm_measure_code = %(llm_measure_code)s,
            llm_time_value = %(llm_time_value)s,
            llm_time_unit = %(llm_time_unit)s,
            llm_time_points = %(llm_time_points)s::jsonb,
            llm_confidence = %(llm_confidence)s,
            llm_notes = %(llm_notes)s,
            llm_status = %(llm_status)s,
            failure_reason = %(failure_reason)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE nct_id = %(nct_id)s
          AND outcome_type = %(outcome_type)s
          AND outcome_order = %(outcome_order)s
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, update_sql, update_data, page_size=100)
        conn.commit()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] PARSE_ERROR 항목 재처리 시작")
    print("=" * 80)
    
    api_keys = get_api_keys()
    if not api_keys:
        print("\n[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        print("환경변수에 GEMINI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        sys.exit(1)
    
    print(f"\n[INFO] 사용 가능한 API 키: {len(api_keys)}개")
    print(f"[INFO] 사용 모델: {GEMINI_MODEL}")
    
    # 명령줄 인자 파싱
    # 사용법: python llm_reprocess_parse_errors.py [batch_size] [start_batch]
    custom_batch_size = 100
    start_batch = 1
    
    if len(sys.argv) > 1:
        try:
            custom_batch_size = int(sys.argv[1])
            if custom_batch_size <= 0:
                custom_batch_size = 100
        except ValueError:
            pass
    
    if len(sys.argv) > 2:
        try:
            start_batch = int(sys.argv[2])
            if start_batch < 1:
                start_batch = 1
        except ValueError:
            pass
    
    # 배치 크기 조정
    if custom_batch_size:
        import llm_config
        llm_config.BATCH_SIZE = custom_batch_size
        print(f"[INFO] 배치 크기: {custom_batch_size}개")
    
    if start_batch > 1:
        print(f"[INFO] 배치 {start_batch}번부터 시작합니다.")
    
    try:
        conn = get_db_connection()
        
        # PARSE_ERROR 항목 조회
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) as total_count
                FROM outcome_llm_preprocessed
                WHERE llm_notes = '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.'
            """)
            total_count = cur.fetchone()['total_count']
            
            if total_count == 0:
                print("\n[INFO] 재처리할 항목이 없습니다.")
                conn.close()
                return
            
            print(f"\n[INFO] 재처리 대상: {total_count:,}건")
            
            # outcome_id 목록 조회
            cur.execute("""
                SELECT DISTINCT
                    olp.nct_id,
                    olp.outcome_type,
                    olp.outcome_order
                FROM outcome_llm_preprocessed olp
                WHERE olp.llm_notes = '[PARSE_ERROR] LLM 응답에 outcome_id가 없음.'
                ORDER BY olp.nct_id, olp.outcome_type, olp.outcome_order
            """)
            parse_error_items = cur.fetchall()
            
            print(f"[INFO] 조회된 항목: {len(parse_error_items):,}건")
        
        # 원본 데이터 조회를 위한 outcome_id 매핑
        nct_outcome_map = {}
        for item in parse_error_items:
            key = (item['nct_id'], item['outcome_type'], item['outcome_order'])
            nct_outcome_map[key] = item
        
        # outcome_raw에서 원본 데이터 조회
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            placeholders = []
            params = []
            for item in parse_error_items:
                placeholders.append("(nct_id = %s AND outcome_type = %s AND outcome_order = %s)")
                params.extend([item['nct_id'], item['outcome_type'], item['outcome_order']])
            
            query = f"""
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
                WHERE ({' OR '.join(placeholders)})
                ORDER BY nct_id, outcome_type, outcome_order
            """
            cur.execute(query, params)
            outcomes = cur.fetchall()
            
            print(f"[INFO] 원본 데이터 조회: {len(outcomes):,}건")
        
        if not outcomes:
            print("\n[WARN] 원본 데이터를 찾을 수 없습니다.")
            conn.close()
            return
        
        # 배치 처리
        total_batches = (len(outcomes) + custom_batch_size - 1) // custom_batch_size
        print(f"\n[INFO] 총 배치 수: {total_batches}개")
        print("=" * 80)
        
        success_count = 0
        failed_count = 0
        
        for batch_num in range(start_batch, total_batches + 1):
            start_idx = (batch_num - 1) * custom_batch_size
            end_idx = min(start_idx + custom_batch_size, len(outcomes))
            batch_outcomes = outcomes[start_idx:end_idx]
            
            print(f"\n[배치 {batch_num}/{total_batches}] 처리 중... ({len(batch_outcomes)}건)")
            
            try:
                # LLM 전처리
                results = preprocess_batch_outcomes(batch_outcomes)
                
                if results:
                    # DB 업데이트
                    update_llm_results(conn, batch_outcomes, results)
                    
                    # 통계
                    batch_success = sum(1 for r in results if r['llm_status'] == 'SUCCESS')
                    batch_failed = len(results) - batch_success
                    success_count += batch_success
                    failed_count += batch_failed
                    
                    print(f"  [OK] 성공: {batch_success}건, 실패: {batch_failed}건")
                else:
                    print(f"  [WARN] 결과가 없습니다.")
                    failed_count += len(batch_outcomes)
                
                # Rate limiting
                if batch_num < total_batches:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  [ERROR] 배치 처리 중 오류: {e}")
                import traceback
                traceback.print_exc()
                failed_count += len(batch_outcomes)
                continue
        
        print("\n" + "=" * 80)
        print("[OK] 재처리 완료!")
        print("=" * 80)
        print(f"\n[통계]")
        print(f"  성공: {success_count:,}건")
        print(f"  실패: {failed_count:,}건")
        print(f"  총 처리: {success_count + failed_count:,}건")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

