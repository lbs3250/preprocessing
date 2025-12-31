"""
성공 항목 LLM 검증 스크립트

outcome_normalized_success 테이블에서 성공 항목을 추출하여
Gemini API를 사용하여 파싱 결과를 검증합니다.
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
from llm_prompts import get_validation_prompt

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
    
    # 모든 키를 시도 (6개 키면 0,1,2,3,4,5 총 6번)
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
            
            # 성공 시 전역 인덱스 업데이트 (키 변경 시 규칙 다시 보내기 위해)
            if llm_config._current_key_index != key_index:
                llm_config._previous_key_index = llm_config._current_key_index
            llm_config._current_key_index = key_index
            
            # 응답 텍스트 추출
            content = response.text.strip()
            
            # JSON 추출 (코드 블록 제거)
            if content.startswith('```'):
                # 코드 블록 제거
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
            
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON 파싱 실패 (키 {key_index + 1}/{len(api_keys)}): {e}")
                print(f"  응답 내용: {content[:200]}")
                return None
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            # 429 에러 (RESOURCE_EXHAUSTED) 체크
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str.upper():
                print(f"⚠️  API 키 {key_index + 1}/{len(api_keys)}에서 429 에러 발생 (시도 {attempt + 1}/{len(api_keys)}): {error_str}")
                
                # 마지막 시도(6개 키면 attempt==5)인 경우 종료
                if attempt == len(api_keys) - 1:
                    print(f"[ERROR] 모든 API 키({len(api_keys)}개)가 소진되었습니다.")
                    llm_config._current_key_index = key_index
                    llm_config._all_keys_exhausted = True
                    return None
                else:
                    next_key_index = (start_key_index + attempt + 1) % len(api_keys)
                    print(f"🔄 다음 API 키로 전환합니다 (키 {next_key_index + 1}/{len(api_keys)})")
                    continue  # 다음 키로 재시도
            else:
                # 429가 아닌 다른 에러는 현재 키에서 재시도하지 않고 반환
                print(f"[ERROR] Gemini API 오류 (키 {key_index + 1}/{len(api_keys)}): {error_str}")
                return None
    
    # 모든 키 시도 실패 (이 코드는 실행되지 않아야 함)
    print(f"[ERROR] 모든 API 키({len(api_keys)}개) 시도 실패. 마지막 에러: {str(last_error)}")
    llm_config._all_keys_exhausted = True
    return None


def format_time_points(time_points) -> str:
    """time_points를 문자열로 변환"""
    if not time_points:
        return ''
    try:
        if isinstance(time_points, str):
            time_points = json.loads(time_points)
        if isinstance(time_points, list):
            return ', '.join([f"{tp.get('value', '')} {tp.get('unit', '')}" for tp in time_points if tp])
    except:
        pass
    return str(time_points)


def validate_batch_outcomes(outcomes: List[Dict]) -> List[Dict]:
    """배치 단위로 outcome들을 LLM으로 검증 (규칙 캐싱 적용)"""
    if not outcomes:
        return []
    
    import llm_config
    
    # 배치 프롬프트 생성 (최소화)
    items = []
    for outcome in outcomes:
        oid = outcome['outcome_id']
        mr = outcome.get('measure_raw', '')
        tr = outcome.get('time_frame_raw', '')
        mc = outcome.get('measure_code', '')
        tv = outcome.get('time_value_main', '')
        tu = outcome.get('time_unit_main', '')
        tp = format_time_points(outcome.get('time_points'))
        # 빈 값 생략하여 더 짧게
        parts = [f"{oid}"]
        if mr: parts.append(f"M:{mr}")
        if tr: parts.append(f"T:{tr}")
        if mc: parts.append(f"C:{mc}")
        if tv and tu: parts.append(f"V:{tv}{tu}")
        if tp: parts.append(f"P:{tp}")
        item_str = "|".join(parts)
        items.append(item_str)
    
    # API 키가 변경되었는지 확인 (규칙 캐싱)
    current_key_idx = llm_config._current_key_index
    previous_key_idx = llm_config._previous_key_index
    include_rules = (current_key_idx != previous_key_idx or previous_key_idx == -1)
    
    # 키 인덱스 업데이트 (다음 호출을 위해)
    if include_rules:
        llm_config._previous_key_index = current_key_idx
    
    # 프롬프트 생성
    items_text = '\n'.join(items)
    prompt = get_validation_prompt(items_text)
    
    result = call_gemini_api(prompt)
    
    if not result:
        # API 실패 시 모두 UNCERTAIN 처리
        return [{
            'outcome_id': outcome['outcome_id'],
            'llm_validation_status': 'UNCERTAIN',
            'llm_validation_confidence': None,
            'llm_validation_notes': 'API 호출 실패'
        } for outcome in outcomes]
    
    # 결과 파싱 (배열로 응답 받음)
    results = []
    if isinstance(result, list):
        # outcome_id로 매핑
        result_map = {r.get('outcome_id'): r for r in result if 'outcome_id' in r}
        for outcome in outcomes:
            outcome_id = outcome['outcome_id']
            if outcome_id in result_map:
                r = result_map[outcome_id]
                status = r.get('status', '').upper()
                valid_statuses = ['VERIFIED', 'UNCERTAIN', 'MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED']
                if status not in valid_statuses:
                    status = 'UNCERTAIN'
                results.append({
                    'outcome_id': outcome_id,
                    'llm_validation_status': status,
                    'llm_validation_confidence': r.get('confidence'),
                    'llm_validation_notes': r.get('notes')
                })
            else:
                results.append({
                    'outcome_id': outcome_id,
                    'llm_validation_status': 'UNCERTAIN',
                    'llm_validation_confidence': None,
                    'llm_validation_notes': '응답에 outcome_id 없음'
                })
    else:
        # 단일 응답인 경우 (하위 호환성)
        status = result.get('status', '').upper()
        valid_statuses = ['VERIFIED', 'UNCERTAIN', 'MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED']
        if status not in valid_statuses:
            status = 'UNCERTAIN'
        if outcomes:
            results.append({
                'outcome_id': outcomes[0]['outcome_id'],
                'llm_validation_status': status,
                'llm_validation_confidence': result.get('confidence'),
                'llm_validation_notes': result.get('notes')
            })
    
    return results


def update_validation_results(conn, results: List[Dict]):
    """LLM 검증 결과를 데이터베이스에 업데이트"""
    if not results:
        return
    
    update_sql = """
        UPDATE outcome_normalized
        SET 
            llm_validation_status = %(llm_validation_status)s,
            llm_validation_confidence = %(llm_validation_confidence)s,
            llm_validation_notes = %(llm_validation_notes)s
        WHERE outcome_id = %(outcome_id)s
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, update_sql, results, page_size=100)
        conn.commit()


def main():
    """메인 함수"""
    import sys
    
    print("=" * 80)
    print("[START] 성공 항목 LLM 검증 시작")
    print("=" * 80)
    
    api_keys = get_api_keys()
    if not api_keys:
        print("\n[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        print("환경변수에 GEMINI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        print("여러 키를 사용하려면 GEMINI_API_KEY_2, GEMINI_API_KEY_3 등을 추가하세요")
        sys.exit(1)
    
    print(f"\n[INFO] 사용 가능한 API 키: {len(api_keys)}개")
    print(f"[INFO] 사용 모델: {GEMINI_MODEL}")
    
    # 처리할 항목 수 제한 (옵션)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    try:
        conn = get_db_connection()
        
        # 성공 항목 조회 (아직 검증하지 않은 항목) - 전체 조회
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    o.outcome_id,
                    o.measure_raw,
                    o.time_frame_raw,
                    o.measure_code,
                    o.time_value_main,
                    o.time_unit_main,
                    o.time_points
                FROM outcome_normalized_success o
                WHERE o.llm_validation_status IS NULL
                ORDER BY o.outcome_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            success_outcomes = cur.fetchall()
        
        total_count = len(success_outcomes)
        print(f"\n[INFO] 처리할 성공 항목: {total_count:,}개")
        
        if total_count == 0:
            print("[INFO] 처리할 항목이 없습니다.")
            conn.close()
            return
        
        # LLM 검증 (배치 처리)
        print("\n[STEP 1] LLM 검증 시작 (배치 크기: {})...".format(BATCH_SIZE))
        verified_count = 0
        uncertain_count = 0
        measure_failed_count = 0
        timeframe_failed_count = 0
        both_failed_count = 0
        
        # 배치 단위로 처리 (메모리에서 나누기)
        for batch_start in range(0, total_count, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_count)
            batch_outcomes = success_outcomes[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (total_count + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"  배치 {batch_num}/{total_batches} 처리 중: {batch_start + 1:,}~{batch_end:,}번째 항목")
            
            # 모든 키가 소진되었는지 확인
            import llm_config
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 처리 중단합니다.")
                break
            
            # 배치 단위로 한번에 API 호출
            batch_results = validate_batch_outcomes(batch_outcomes)
            
            # 모든 키가 소진되었는지 다시 확인 (호출 중에 소진될 수 있음)
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 처리 중단합니다.")
                break
            
            # 결과 집계
            for result in batch_results:
                status = result['llm_validation_status']
                if status == 'VERIFIED':
                    verified_count += 1
                elif status == 'UNCERTAIN':
                    uncertain_count += 1
                elif status == 'MEASURE_FAILED':
                    measure_failed_count += 1
                elif status == 'TIMEFRAME_FAILED':
                    timeframe_failed_count += 1
                elif status == 'BOTH_FAILED':
                    both_failed_count += 1
            
            # Rate limiting (배치당 1회 호출이므로 단순화)
            time.sleep(60 / MAX_REQUESTS_PER_MINUTE)  # 분당 요청 수 제한
            
            # 배치마다 DB 업데이트
            if batch_results:
                print(f"  배치 {batch_num} 결과 저장 중... ({len(batch_results)}개)")
                update_validation_results(conn, batch_results)
            
            print(f"  배치 {batch_num} 완료 (VERIFIED: {verified_count:,}, UNCERTAIN: {uncertain_count:,}, MEASURE_FAILED: {measure_failed_count:,}, TIMEFRAME_FAILED: {timeframe_failed_count:,}, BOTH_FAILED: {both_failed_count:,})")
            
            # 모든 키가 소진되었으면 배치 루프도 중단
            import llm_config
            if llm_config._all_keys_exhausted:
                print(f"\n[ERROR] 모든 API 키가 소진되어 배치 처리 중단합니다.")
                break
        
        print(f"\n[INFO] 처리 완료:")
        print(f"  전체: {total_count:,}개")
        print(f"  VERIFIED (완벽): {verified_count:,}개 ({verified_count/total_count*100:.1f}%)")
        print(f"  UNCERTAIN (애매): {uncertain_count:,}개 ({uncertain_count/total_count*100:.1f}%)")
        print(f"  MEASURE_FAILED (Measure 불일치): {measure_failed_count:,}개 ({measure_failed_count/total_count*100:.1f}%)")
        print(f"  TIMEFRAME_FAILED (Timeframe 불일치): {timeframe_failed_count:,}개 ({timeframe_failed_count/total_count*100:.1f}%)")
        print(f"  BOTH_FAILED (둘 다 불일치): {both_failed_count:,}개 ({both_failed_count/total_count*100:.1f}%)")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

