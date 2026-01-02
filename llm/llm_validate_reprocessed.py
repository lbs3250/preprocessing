"""
재전처리 완료 항목 LLM 검증 스크립트 (Inclusion/Exclusion)

재전처리 완료된 항목(llm_status = 'SUCCESS'이고 llm_notes에 '[REPROCESS]' 포함)에 대해
LLM 검증을 다시 수행합니다.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv

# 기존 검증 스크립트의 함수들 import
from llm_validate_inclusion_exclusion import (
    get_db_connection,
    validate_batch_single_run,
    validate_with_multi_run_for_eligibility,
    update_validation_results,
    apply_confidence_consistency_filtering,
    majority_voting,
    calculate_consistency_score
)
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


def get_reprocessed_items(conn, limit: Optional[int] = None) -> List[Dict]:
    """
    전처리 완료되었지만 검증 상태가 없는 항목들을 조회
    
    Args:
        conn: 데이터베이스 연결
        limit: 조회할 항목 수 제한 (None이면 전체)
    
    Returns:
        전처리 완료되었지만 검증되지 않은 eligibility 리스트
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = """
            SELECT 
                ier.nct_id,
                ier.eligibility_criteria_raw,
                ier.phase,
                iep.inclusion_criteria,
                iep.exclusion_criteria,
                iep.llm_status,
                iep.llm_validation_status
            FROM inclusion_exclusion_raw ier
            INNER JOIN inclusion_exclusion_llm_preprocessed iep
                ON ier.nct_id = iep.nct_id
            WHERE iep.llm_status = 'SUCCESS'
              AND iep.llm_validation_status IS NULL
            ORDER BY ier.nct_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        return cur.fetchall()


def main():
    """메인 함수"""
    # API 키 확인
    api_keys = get_api_keys()
    if not api_keys:
        print("환경변수에 GEMINI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        sys.exit(1)
    
    print(f"\n[INFO] 사용 가능한 API 키: {len(api_keys)}개")
    print(f"[INFO] 사용 모델: {GEMINI_MODEL}")
    print(f"[INFO] 배치 크기: {BATCH_SIZE}개")
    
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description='재전처리 완료 항목 LLM 검증 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python llm_validate_reprocessed.py
  python llm_validate_reprocessed.py --limit 100
  python llm_validate_reprocessed.py --batch-size 20
  python llm_validate_reprocessed.py --runs 3
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
        '--runs',
        type=int,
        default=3,
        metavar='NUM',
        help='검증 실행 횟수 (기본값: 3)'
    )
    
    args = parser.parse_args()
    
    limit = args.limit
    custom_batch_size = args.batch_size
    num_runs = args.runs if args.runs >= 1 else 3
    
    print(f"[INFO] 처리 모드: 전처리 완료 항목 검증")
    print(f"  - 전처리 완료되었지만 검증되지 않은 항목")
    print(f"    (llm_status = 'SUCCESS' AND llm_validation_status IS NULL)")
    print(f"  - 검증 실행 횟수: {num_runs}회")
    
    # 배치 크기 조정
    if custom_batch_size and custom_batch_size > 0:
        import llm_config
        llm_config.BATCH_SIZE = custom_batch_size
        print(f"[INFO] 배치 크기를 {custom_batch_size}개로 조정했습니다.")
    
    try:
        conn = get_db_connection()
        
        # 재전처리 완료된 항목 조회
        print("\n[STEP 0] 재전처리 완료된 항목 조회 중...")
        eligibility_list = get_reprocessed_items(conn, limit)
        
        total_count = len(eligibility_list)
        print(f"[INFO] 처리할 항목: {total_count:,}개")
        
        if total_count == 0:
            print("[INFO] 처리할 항목이 없습니다.")
            conn.close()
            return
        
        # 통계 출력
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as total_success,
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NOT NULL) as already_validated,
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NULL) as needs_validation
                FROM inclusion_exclusion_llm_preprocessed
            """)
            stats = cur.fetchone()
            print(f"\n[통계]")
            print(f"  전체 전처리 완료 항목 (SUCCESS): {stats['total_success']:,}개")
            print(f"  - 이미 검증된 항목: {stats['already_validated']:,}개")
            print(f"  - 검증 필요 항목 (llm_validation_status IS NULL): {stats['needs_validation']:,}개")
        
        # LLM 검증 (다중 실행)
        import llm_config
        actual_batch_size = llm_config.BATCH_SIZE
        print(f"\n[STEP 1] LLM 검증 시작 (배치 크기: {actual_batch_size}, 실행 횟수: {num_runs}회)...")
        
        all_results = []
        validation_results_by_run = {}
        
        # 다중 실행
        for run_num in range(1, num_runs + 1):
            print(f"\n[RUN {run_num}/{num_runs}] 검증 실행 중...")
            
            # 배치 단위로 처리
            for batch_start in range(0, total_count, actual_batch_size):
                batch_end = min(batch_start + actual_batch_size, total_count)
                batch_num = (batch_start // actual_batch_size) + 1
                total_batches = (total_count + actual_batch_size - 1) // actual_batch_size
                
                print(f"  배치 {batch_num}/{total_batches} 처리 중: {batch_start + 1:,}~{batch_end:,}번째 항목")
                
                batch_eligibility = eligibility_list[batch_start:batch_end]
                
                # 배치 단위로 한번에 API 호출
                batch_results = validate_batch_single_run(batch_eligibility)
                
                if not batch_results:
                    print(f"  [WARNING] 배치 {batch_num} 검증 실패")
                    continue
                
                # run별 결과 저장
                if run_num not in validation_results_by_run:
                    validation_results_by_run[run_num] = {}
                validation_results_by_run[run_num].update(batch_results)
                
                # API 호출 제한 대기
                time.sleep(60.0 / MAX_REQUESTS_PER_MINUTE)
        
        # 다중 검증 결과 통합 처리
        print(f"\n[STEP 2] 다중 검증 결과 통합 처리 중...")
        final_results = []
        
        for eligibility in eligibility_list:
            nct_id = eligibility.get('nct_id')
            if not nct_id:
                continue
            
            # 기존 검증 이력 조회
            existing_results = []
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
                for row in cur.fetchall():
                    existing_results.append({
                        'status': row['status'],
                        'confidence': row['confidence'],
                        'notes': row['notes'] or ''
                    })
            
            # 다중 검증 결과 통합
            result = validate_with_multi_run_for_eligibility(
                eligibility,
                validation_results_by_run,
                existing_results
            )
            final_results.append(result)
        
        # 결과 저장
        print(f"\n[STEP 3] 검증 결과 저장 중...")
        update_validation_results(conn, final_results, validation_results_by_run)
        
        # 최종 통계
        print(f"\n[STEP 4] 최종 통계 확인...")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') as verified,
                    COUNT(*) FILTER (WHERE llm_validation_status = 'UNCERTAIN') as uncertain,
                    COUNT(*) FILTER (WHERE llm_validation_status IN ('INCLUSION_FAILED', 'EXCLUSION_FAILED', 'BOTH_FAILED')) as failed,
                    COUNT(*) FILTER (WHERE needs_manual_review = TRUE) as needs_manual_review,
                    COUNT(*) FILTER (WHERE llm_validation_status IS NULL) as still_null
                FROM inclusion_exclusion_llm_preprocessed
                WHERE llm_status = 'SUCCESS'
            """)
            final_stats = cur.fetchone()
            
            total_validated = sum([
                final_stats['verified'] or 0,
                final_stats['uncertain'] or 0,
                final_stats['failed'] or 0
            ])
            
            print(f"\n[최종 통계]")
            if total_validated > 0:
                print(f"  검증 완료: {total_validated:,}개")
                print(f"  - VERIFIED: {final_stats['verified']:,}개 ({final_stats['verified']/total_validated*100:.1f}%)")
                print(f"  - UNCERTAIN: {final_stats['uncertain']:,}개 ({final_stats['uncertain']/total_validated*100:.1f}%)")
                print(f"  - FAILED: {final_stats['failed']:,}개 ({final_stats['failed']/total_validated*100:.1f}%)")
            print(f"  - 수동 검토 필요: {final_stats['needs_manual_review']:,}개")
            if final_stats['still_null'] and final_stats['still_null'] > 0:
                print(f"  - 아직 검증되지 않은 항목: {final_stats['still_null']:,}개")
        
        print(f"\n[완료] 재전처리 완료 항목 검증이 완료되었습니다.")
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    main()

