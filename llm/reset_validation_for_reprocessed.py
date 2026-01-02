"""
재전처리 완료 항목의 검증 상태 초기화 스크립트

이미 재전처리 완료된 항목들 중 검증 상태가 남아있는 항목의 검증 관련 필드를 초기화합니다.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def reset_validation_for_reprocessed(conn, dry_run: bool = True):
    """
    재전처리 완료된 항목의 검증 상태 초기화
    
    Args:
        conn: 데이터베이스 연결
        dry_run: True면 실제 업데이트하지 않고 통계만 출력
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 재전처리 완료 항목 중 검증 상태가 남아있는 항목 조회
        cur.execute("""
            SELECT 
                COUNT(*) as total_reprocessed,
                COUNT(*) FILTER (WHERE llm_validation_status IS NOT NULL) as with_validation_status,
                COUNT(*) FILTER (WHERE validation_consistency_score IS NOT NULL) as with_consistency_score,
                COUNT(*) FILTER (WHERE needs_manual_review IS NOT NULL) as with_manual_review
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND (llm_notes LIKE '%[REPROCESS]%' OR llm_notes LIKE '%재전처리%')
        """)
        stats = cur.fetchone()
        
        print(f"\n[통계]")
        print(f"  전체 재전처리 완료 항목: {stats['total_reprocessed']:,}개")
        print(f"  - 검증 상태가 남아있는 항목: {stats['with_validation_status']:,}개")
        print(f"  - 일관성 점수가 남아있는 항목: {stats['with_consistency_score']:,}개")
        print(f"  - 수동 검토 플래그가 남아있는 항목: {stats['with_manual_review']:,}개")
        
        if stats['with_validation_status'] == 0:
            print("\n[INFO] 초기화할 항목이 없습니다.")
            return
        
        if dry_run:
            print(f"\n[DRY RUN] 실제 업데이트는 수행하지 않습니다.")
            print(f"  초기화될 항목: {stats['with_validation_status']:,}개")
            print(f"\n실제 업데이트를 수행하려면 --execute 옵션을 사용하세요.")
            return
        
        # 검증 상태 초기화
        print(f"\n[업데이트] 검증 상태 초기화 중...")
        cur.execute("""
            UPDATE inclusion_exclusion_llm_preprocessed
            SET 
                llm_validation_status = NULL,
                llm_validation_confidence = NULL,
                llm_validation_notes = NULL,
                validation_consistency_score = NULL,
                validation_count = NULL,
                needs_manual_review = NULL,
                avg_validation_confidence = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE llm_status = 'SUCCESS'
              AND (llm_notes LIKE '%[REPROCESS]%' OR llm_notes LIKE '%재전처리%')
              AND llm_validation_status IS NOT NULL
        """)
        
        updated_count = cur.rowcount
        conn.commit()
        
        print(f"[완료] {updated_count:,}개 항목의 검증 상태를 초기화했습니다.")
        
        # 검증 이력도 삭제할지 확인
        cur.execute("""
            SELECT COUNT(*) as history_count
            FROM inclusion_exclusion_llm_validation_history h
            INNER JOIN inclusion_exclusion_llm_preprocessed p
                ON h.nct_id = p.nct_id
            WHERE p.llm_status = 'SUCCESS'
              AND (p.llm_notes LIKE '%[REPROCESS]%' OR p.llm_notes LIKE '%재전처리%')
        """)
        history_stats = cur.fetchone()
        
        if history_stats['history_count'] > 0:
            print(f"\n[참고] 검증 이력도 {history_stats['history_count']:,}개 남아있습니다.")
            print(f"  검증 이력도 삭제하려면 --delete-history 옵션을 사용하세요.")


def delete_validation_history_for_reprocessed(conn):
    """재전처리 완료된 항목의 검증 이력 삭제"""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM inclusion_exclusion_llm_validation_history
            WHERE nct_id IN (
                SELECT nct_id
                FROM inclusion_exclusion_llm_preprocessed
                WHERE llm_status = 'SUCCESS'
                  AND (llm_notes LIKE '%[REPROCESS]%' OR llm_notes LIKE '%재전처리%')
            )
        """)
        
        deleted_count = cur.rowcount
        conn.commit()
        
        print(f"[완료] {deleted_count:,}개 검증 이력을 삭제했습니다.")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='재전처리 완료 항목의 검증 상태 초기화',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python llm/reset_validation_for_reprocessed.py                    # 통계만 확인 (dry run)
  python llm/reset_validation_for_reprocessed.py --execute         # 검증 상태 초기화
  python llm/reset_validation_for_reprocessed.py --execute --delete-history  # 검증 상태 + 이력 삭제
        """
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제로 업데이트 수행 (기본값: dry run)'
    )
    parser.add_argument(
        '--delete-history',
        action='store_true',
        help='검증 이력도 삭제'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("[START] 재전처리 완료 항목의 검증 상태 초기화")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        reset_validation_for_reprocessed(conn, dry_run=not args.execute)
        
        if args.execute and args.delete_history:
            print(f"\n[검증 이력 삭제] 재전처리 완료 항목의 검증 이력 삭제 중...")
            delete_validation_history_for_reprocessed(conn)
        
        print(f"\n[완료] 작업이 완료되었습니다.")
        
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

