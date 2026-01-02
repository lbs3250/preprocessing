"""
수동 검토 필요 항목 재전처리 스크립트 (Inclusion/Exclusion)

validation에서 needs_manual_review = TRUE인 항목들만 재전처리합니다.
validation_history에 validation_notes가 있는 항목을 확인하여 재전처리합니다.
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv

# 기존 전처리 스크립트의 함수들 import
from llm_preprocess_inclusion_exclusion import (
    get_db_connection,
    preprocess_batch_eligibility,
    insert_llm_results,
    create_table_if_not_exists,
    call_gemini_api
)
from llm_prompts import get_inclusion_exclusion_preprocess_prompt, INCLUSION_EXCLUSION_PREPROCESS_RULES
from llm_config import (
    get_api_keys, GEMINI_MODEL,
    MAX_REQUESTS_PER_MINUTE, BATCH_SIZE
)

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_reprocess_items(conn, limit: Optional[int] = None, check_validation_notes: bool = True) -> List[Dict]:
    """
    재전처리가 필요한 항목들을 조회
    - 실패한 항목들 (INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED) - 모든 실패 항목
    - 수동 검토가 필요한 모든 항목들 (needs_manual_review = TRUE, VERIFIED, UNCERTAIN 등 모든 상태 포함)
    
    Args:
        conn: 데이터베이스 연결
        limit: 처리할 항목 수 제한 (None이면 전체)
        check_validation_notes: validation_history에 validation_notes가 있는 것만 필터링할지 여부
    
    Returns:
        eligibility 리스트
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if check_validation_notes:
            # validation_history에 validation_notes가 있는 항목만
            query = """
                SELECT DISTINCT
                    ier.nct_id,
                    ier.eligibility_criteria_raw,
                    ier.phase,
                    iep.llm_status as current_status,
                    iep.llm_validation_status,
                    iep.needs_manual_review,
                    STRING_AGG(DISTINCT h.validation_notes, ' | ' ORDER BY h.validation_notes) as validation_notes_summary
                FROM inclusion_exclusion_llm_preprocessed iep
                INNER JOIN inclusion_exclusion_raw ier
                    ON iep.nct_id = ier.nct_id
                INNER JOIN inclusion_exclusion_llm_validation_history h
                    ON iep.nct_id = h.nct_id
                WHERE (
                    -- 실패한 항목들 (모든 실패 항목)
                    iep.llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')
                    OR
                    -- 수동 검토가 필요한 모든 항목들 (VERIFIED, UNCERTAIN 등 모든 상태 포함)
                    iep.needs_manual_review = TRUE
                )
                  AND h.validation_notes IS NOT NULL
                  AND h.validation_notes != ''
                GROUP BY ier.nct_id, ier.eligibility_criteria_raw, ier.phase, iep.llm_status, iep.llm_validation_status, iep.needs_manual_review
                ORDER BY ier.nct_id
            """
        else:
            # 재전처리 필요한 모든 항목 (validation_notes도 함께 조회)
            query = """
                SELECT DISTINCT
                    ier.nct_id,
                    ier.eligibility_criteria_raw,
                    ier.phase,
                    iep.llm_status as current_status,
                    iep.llm_validation_status,
                    iep.needs_manual_review,
                    STRING_AGG(DISTINCT h.validation_notes, ' | ' ORDER BY h.validation_notes) FILTER (WHERE h.validation_notes IS NOT NULL AND h.validation_notes != '') as validation_notes_summary
                FROM inclusion_exclusion_llm_preprocessed iep
                INNER JOIN inclusion_exclusion_raw ier
                    ON iep.nct_id = ier.nct_id
                LEFT JOIN inclusion_exclusion_llm_validation_history h
                    ON iep.nct_id = h.nct_id
                WHERE (
                    -- 실패한 항목들 (모든 실패 항목)
                    iep.llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')
                    OR
                    -- 수동 검토가 필요한 모든 항목들 (VERIFIED, UNCERTAIN 등 모든 상태 포함)
                    iep.needs_manual_review = TRUE
                )
                GROUP BY ier.nct_id, ier.eligibility_criteria_raw, ier.phase, iep.llm_status, iep.llm_validation_status, iep.needs_manual_review
                ORDER BY ier.nct_id
            """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        eligibility_list = cur.fetchall()
        
        # validation_notes_summary 포함하여 반환
        result = []
        for row in eligibility_list:
            validation_notes = row.get('validation_notes_summary')
            # check_validation_notes가 True면 validation_notes가 있는 것만, False면 모두 포함
            if check_validation_notes and not validation_notes:
                continue  # validation_notes가 없으면 스킵
            
            result.append({
                'nct_id': row['nct_id'],
                'eligibility_criteria_raw': row['eligibility_criteria_raw'],
                'phase': row['phase'],
                'validation_notes': validation_notes  # validation_history에서 조회한 notes
            })
        
        return result


def get_failed_preprocess_items(conn, limit: Optional[int] = None) -> List[Dict]:
    """
    전처리 실패한 항목들(llm_status != 'SUCCESS')을 조회
    
    Args:
        conn: 데이터베이스 연결
        limit: 처리할 항목 수 제한 (None이면 전체)
    
    Returns:
        eligibility 리스트
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = """
            SELECT DISTINCT
                ier.nct_id,
                ier.eligibility_criteria_raw,
                ier.phase,
                iep.llm_status as current_status,
                iep.failure_reason
            FROM inclusion_exclusion_llm_preprocessed iep
            INNER JOIN inclusion_exclusion_raw ier
                ON iep.nct_id = ier.nct_id
            WHERE iep.llm_status != 'SUCCESS'
            ORDER BY ier.nct_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        # 결과 포맷팅
        result = []
        for row in rows:
            result.append({
                'nct_id': row['nct_id'],
                'eligibility_criteria_raw': row['eligibility_criteria_raw'],
                'phase': row['phase']
            })
        
        return result


def preprocess_batch_eligibility_with_notes(eligibility_list: List[Dict]) -> List[Dict]:
    """
    배치 단위로 eligibilityCriteria를 LLM으로 재전처리 (validation_notes 포함)
    validation_notes를 프롬프트에 포함하여 이전 검증 결과를 참고하도록 함
    """
    if not eligibility_list:
        return []
    
    # nct_id 목록 생성 (복구 시 사용)
    nct_id_list = [e.get('nct_id') for e in eligibility_list if e.get('nct_id')]
    
    # 배치 프롬프트 생성 (validation_notes 포함)
    # validation_history에서 조회한 validation_notes를 각 nct_id별로 포함
    items = []
    for eligibility in eligibility_list:
        nct_id = eligibility.get('nct_id')
        criteria_raw = eligibility.get('eligibility_criteria_raw', '') or ''
        validation_notes = eligibility.get('validation_notes', '')  # validation_history에서 조회한 notes
        
        # validation_notes가 있으면 포함 (해당 nct_id의 validation_history에서 조회한 것)
        parts = [f"{nct_id}"]
        if criteria_raw:
            parts.append(f"{criteria_raw}")
        if validation_notes:
            # validation_history에서 조회한 validation_notes를 프롬프트에 포함
            parts.append(f"[VALIDATION_NOTES:{validation_notes}]")
        
        item_str = "|".join(parts)
        items.append(item_str)
    
    # 재전처리용 프롬프트 생성
    items_text = '\n'.join(items)
    
    # validation_notes를 참고하라는 지시 추가
    # validation_history에서 조회한 validation_notes를 참고하여 재전처리
    prompt = f"""다음 Inclusion/Exclusion Criteria를 재전처리하세요.

**재전처리 지시사항:**
- 이전 검증 결과([VALIDATION_NOTES:...])를 반드시 참고하여 개선된 결과를 생성하세요.
- [VALIDATION_NOTES:...]는 해당 nct_id의 validation_history에서 조회한 검증 노트입니다.
- 검증 노트에 언급된 문제점, 오류, 개선 사항을 반드시 해결하거나 개선하세요.
- 검증 노트가 없는 경우에도 더 정확하게 구조화하세요.

데이터 형식: [nct_id]|[eligibility_criteria_raw]|[VALIDATION_NOTES:validation_notes]
(validation_notes가 있는 경우에만 [VALIDATION_NOTES:...] 포함)

{items_text}

{INCLUSION_EXCLUSION_PREPROCESS_RULES}

**중요: 반드시 JSON 배열만 반환하세요. 코드나 설명 없이 순수 JSON만 반환합니다.**

응답 형식 (JSON 배열):
[
  {{
    "nct_id": "NCT12345678",
    "inclusion_criteria": [...],
    "exclusion_criteria": [...]
  }}
]

**반드시 위 형식의 JSON 배열만 반환하세요. 코드나 설명 텍스트는 포함하지 마세요.**
**⚠️ 필수: 각 JSON 객체의 최상위 레벨에 반드시 "nct_id" 필드를 포함하세요.**
"""
    
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
    
    # 결과 파싱 (기존 preprocess_batch_eligibility와 동일한 로직)
    from llm_preprocess_inclusion_exclusion import determine_llm_status
    import json
    
    results = []
    if isinstance(result, list):
        # nct_id로 매핑
        result_map = {}
        for r in result:
            nct_id = r.get('nct_id')
            if nct_id and isinstance(nct_id, str):
                if nct_id not in result_map:
                    result_map[nct_id] = r
        
        for eligibility in eligibility_list:
            nct_id = eligibility.get('nct_id')
            if nct_id in result_map:
                r = result_map[nct_id]
                inclusion_criteria = r.get('inclusion_criteria')
                exclusion_criteria = r.get('exclusion_criteria')
                
                inclusion_json = json.dumps(inclusion_criteria) if inclusion_criteria is not None else None
                exclusion_json = json.dumps(exclusion_criteria) if exclusion_criteria is not None else None
                
                notes = r.get('notes', '')
                if notes:
                    notes = f'[REPROCESS] {notes}'
                else:
                    notes = '[REPROCESS] validation_notes를 참고하여 재전처리 완료.'
                
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
                # 응답에 nct_id가 없는 경우
                status, failure_reason, formatted_notes = determine_llm_status(
                    None, None, '[PARSE_ERROR] LLM 응답에 nct_id가 없음.'
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
            
            inclusion_json = json.dumps(inclusion_criteria) if inclusion_criteria is not None else None
            exclusion_json = json.dumps(exclusion_criteria) if exclusion_criteria is not None else None
            
            notes = result.get('notes', '')
            if notes:
                notes = f'[REPROCESS] {notes}'
            else:
                notes = '[REPROCESS] validation_notes를 참고하여 재전처리 완료.'
            
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


def insert_llm_results_reprocess(conn, eligibility_list: List[Dict], results: List[Dict]):
    """
    재전처리 결과를 inclusion_exclusion_llm_preprocessed 테이블에 저장
    재전처리이므로 기존 데이터를 무조건 덮어쓰기 (SUCCESS 여부와 관계없이)
    """
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
    
    # 재전처리용 INSERT (항상 덮어쓰기)
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
            inclusion_criteria = EXCLUDED.inclusion_criteria,
            exclusion_criteria = EXCLUDED.exclusion_criteria,
            llm_confidence = EXCLUDED.llm_confidence,
            llm_notes = EXCLUDED.llm_notes,
            llm_status = EXCLUDED.llm_status,
            failure_reason = EXCLUDED.failure_reason,
            -- 재전처리 시 검증 관련 필드 초기화 (전처리 결과가 바뀌었으므로 검증도 다시 해야 함)
            llm_validation_status = NULL,
            llm_validation_confidence = NULL,
            llm_validation_notes = NULL,
            validation_consistency_score = NULL,
            validation_count = NULL,
            needs_manual_review = NULL,
            avg_validation_confidence = NULL,
            updated_at = CURRENT_TIMESTAMP
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, insert_data, page_size=100)
        conn.commit()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] 재전처리 필요한 항목 재전처리 시작 (Inclusion/Exclusion)")
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
    parser = argparse.ArgumentParser(
        description='수동 검토 필요 항목 재전처리 스크립트 (Inclusion/Exclusion)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python llm_reprocess_manual_review.py
  python llm_reprocess_manual_review.py --limit 100
  python llm_reprocess_manual_review.py --batch-size 20
  python llm_reprocess_manual_review.py --limit 100 --batch-size 20 --start-batch 3
  python llm_reprocess_manual_review.py --no-notes-check
        """
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='처리할 항목 수 제한 (기본값: 전체)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=None,
        metavar='SIZE',
        help=f'배치 크기 조정 (기본값: {BATCH_SIZE})'
    )
    parser.add_argument(
        '--start-batch',
        type=int,
        default=1,
        metavar='NUM',
        help='시작할 배치 번호 (기본값: 1)'
    )
    parser.add_argument(
        '--no-notes-check',
        action='store_true',
        help='validation_notes 체크 없이 모든 재전처리 대상 항목 처리'
    )
    parser.add_argument(
        '--failed-only',
        action='store_true',
        help='전처리 실패한 항목만 재전처리 (llm_status != SUCCESS)'
    )
    
    args = parser.parse_args()
    
    limit = args.limit
    custom_batch_size = args.batch_size
    start_batch = args.start_batch if args.start_batch >= 1 else 1
    check_validation_notes = not args.no_notes_check
    
    if args.failed_only:
        print(f"[INFO] 처리 모드: 전처리 실패한 항목 재전처리")
        print(f"  - llm_status != 'SUCCESS'인 항목들")
    else:
        print(f"[INFO] 처리 모드: 재전처리 필요한 항목 재전처리")
        print(f"  - 실패한 항목들 (INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED)")
        print(f"  - 수동 검토가 필요한 모든 항목들 (needs_manual_review = TRUE, 모든 상태 포함)")
        if check_validation_notes:
            print(f"[INFO] 필터: validation_history에 validation_notes가 있는 항목만")
        else:
            print(f"[INFO] 필터: validation_notes 체크 없음 (모든 재전처리 대상 항목)")
    
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
        
        # 재전처리 필요한 항목 조회
        print("\n[STEP 0] 재전처리 필요한 항목 조회 중...")
        if args.failed_only:
            print("  - 전처리 실패한 항목들 (llm_status != 'SUCCESS')")
            eligibility_list = get_failed_preprocess_items(conn, limit)
        else:
            print("  - 실패한 항목들 (INCLUSION_FAILED, EXCLUSION_FAILED, BOTH_FAILED)")
            print("  - VERIFIED 중에서도 수동 검토가 필요한 항목들")
            eligibility_list = get_reprocess_items(conn, limit, check_validation_notes)
        
        total_count = len(eligibility_list)
        print(f"[INFO] 처리할 항목: {total_count:,}개")
        
        if total_count == 0:
            print("[INFO] 처리할 항목이 없습니다.")
            conn.close()
            return
        
        # 통계 출력
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if args.failed_only:
                cur.execute("""
                    SELECT 
                        llm_status,
                        COUNT(*) as count
                    FROM inclusion_exclusion_llm_preprocessed
                    WHERE llm_status != 'SUCCESS'
                    GROUP BY llm_status
                    ORDER BY count DESC
                """)
                stats_rows = cur.fetchall()
                print(f"\n[통계]")
                print(f"  전체 전처리 실패 항목: {sum(row['count'] for row in stats_rows):,}개")
                for row in stats_rows:
                    print(f"  - {row['llm_status']}: {row['count']:,}개")
            else:
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')) as failed_count,
                        COUNT(*) FILTER (WHERE needs_manual_review = TRUE) as needs_manual_review_count,
                        COUNT(*) as total_reprocess
                    FROM inclusion_exclusion_llm_preprocessed iep
                    WHERE (
                        llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')
                        OR needs_manual_review = TRUE
                    )
                """)
                stats = cur.fetchone()
                print(f"\n[통계]")
                print(f"  전체 재전처리 대상: {stats['total_reprocess']:,}개")
                print(f"  - 실패한 항목: {stats['failed_count']:,}개")
                print(f"  - 수동 검토 필요 (needs_manual_review = TRUE): {stats['needs_manual_review_count']:,}개")
                
                if check_validation_notes:
                    cur.execute("""
                        SELECT COUNT(DISTINCT iep.nct_id) as with_notes
                        FROM inclusion_exclusion_llm_preprocessed iep
                        INNER JOIN inclusion_exclusion_llm_validation_history h
                            ON iep.nct_id = h.nct_id
                            AND h.validation_notes IS NOT NULL
                            AND h.validation_notes != ''
                        WHERE (
                            iep.llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')
                            OR iep.needs_manual_review = TRUE
                        )
                    """)
                    notes_stats = cur.fetchone()
                    print(f"  - validation_notes 있는 항목: {notes_stats['with_notes']:,}개")
        
        # LLM 전처리 (배치 처리)
        import llm_config
        actual_batch_size = llm_config.BATCH_SIZE
        print(f"\n[STEP 1] LLM 재전처리 시작 (배치 크기: {actual_batch_size})...")
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
            if args.failed_only:
                # 전처리 실패 항목은 validation_notes 없이 재전처리
                from llm_preprocess_inclusion_exclusion import preprocess_batch_eligibility
                batch_results = preprocess_batch_eligibility(batch_eligibility)
            else:
                # validation_notes 포함하여 재전처리
                batch_results = preprocess_batch_eligibility_with_notes(batch_eligibility)
            
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
            
            # 배치마다 DB 저장 (재전처리이므로 항상 덮어쓰기)
            if batch_results:
                print(f"  배치 {batch_num} 결과 저장 중... ({len(batch_results)}개)")
                insert_llm_results_reprocess(conn, batch_eligibility, batch_results)
            
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
        
        # 재전처리 후 needs_manual_review 상태 확인
        print("\n[STEP 2] 재전처리 후 상태 확인...")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_processed,
                    COUNT(CASE WHEN llm_status = 'SUCCESS' THEN 1 END) as success_after,
                    COUNT(CASE WHEN needs_manual_review = TRUE THEN 1 END) as still_manual_review
                FROM inclusion_exclusion_llm_preprocessed
                WHERE nct_id = ANY(%s)
            """, ([e['nct_id'] for e in eligibility_list],))
            after_stats = cur.fetchone()
            print(f"  재전처리된 항목: {after_stats['total_processed']:,}개")
            print(f"  재전처리 후 SUCCESS: {after_stats['success_after']:,}개")
            print(f"  여전히 needs_manual_review = TRUE: {after_stats['still_manual_review']:,}개")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

