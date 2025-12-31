"""
정규화된 데이터를 2개 테이블로 분리하는 스크립트

1. outcome_normalized_success: 완벽 정규화된 데이터
   - measure_code IS NOT NULL AND failure_reason IS NULL
   - 개별 outcome 단위로 성공/실패 판단
   
2. outcome_normalized_failed: 정규화 실패 데이터
   - measure_code IS NULL OR failure_reason IS NOT NULL
   - failure_reason 필드로 구분: 'MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED'
"""

import os
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import psycopg2

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




def create_separation_tables(conn):
    """분리 테이블 생성"""
    print("\n[STEP 1] 분리 테이블 생성 중...")
    
    with conn.cursor() as cur:
        # 1. 완벽 정규화된 테이블
        cur.execute("""
            DROP TABLE IF EXISTS outcome_normalized_success CASCADE;
            
            CREATE TABLE outcome_normalized_success (
                LIKE outcome_normalized INCLUDING ALL
            );
            
            CREATE INDEX idx_outcome_normalized_success_nct_id 
                ON outcome_normalized_success(nct_id);
            CREATE INDEX idx_outcome_normalized_success_type 
                ON outcome_normalized_success(outcome_type);
            CREATE INDEX idx_outcome_normalized_success_phase 
                ON outcome_normalized_success(phase);
        """)
        
        # 2. 정규화 실패 테이블
        cur.execute("""
            DROP TABLE IF EXISTS outcome_normalized_failed CASCADE;
            
            CREATE TABLE outcome_normalized_failed (
                LIKE outcome_normalized INCLUDING ALL
            );
            
            CREATE INDEX idx_outcome_normalized_failed_nct_id 
                ON outcome_normalized_failed(nct_id);
            CREATE INDEX idx_outcome_normalized_failed_type 
                ON outcome_normalized_failed(outcome_type);
            CREATE INDEX idx_outcome_normalized_failed_reason 
                ON outcome_normalized_failed(failure_reason);
            CREATE INDEX idx_outcome_normalized_failed_phase 
                ON outcome_normalized_failed(phase);
        """)
        
        conn.commit()
        print("[OK] 분리 테이블 생성 완료")


def separate_data(conn):
    """데이터 분리 (개별 Outcome 단위 성공 기준)"""
    print("\n[STEP 2] 데이터 분리 중...")
    print("  성공 기준:")
    print("    - measure_code IS NOT NULL AND failure_reason IS NULL")
    print("    - 개별 outcome 단위로 성공/실패 판단")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 데이터 확인
        cur.execute("SELECT COUNT(*) FROM outcome_normalized")
        total_count = cur.fetchone()['count']
        print(f"\n  전체 데이터: {total_count:,}건")
        
        # 개별 outcome 단위로 성공 여부 판단
        # 성공 기준: measure_code IS NOT NULL AND failure_reason IS NULL
        print("\n  [1] 개별 outcome 단위 성공 여부 판단 중...")
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE measure_code IS NOT NULL AND failure_reason IS NULL) as success_count,
                COUNT(*) FILTER (WHERE measure_code IS NULL OR failure_reason IS NOT NULL) as failed_count
            FROM outcome_normalized
        """)
        stats = cur.fetchone()
        print(f"    성공한 outcome: {stats['success_count']:,}건")
        print(f"    실패한 outcome: {stats['failed_count']:,}건")
        
        # 성공한 outcome만 success 테이블에 삽입
        print("\n  [2] 성공한 outcome 분리 중...")
        cur.execute("""
            INSERT INTO outcome_normalized_success
            SELECT *
            FROM outcome_normalized
            WHERE measure_code IS NOT NULL 
              AND failure_reason IS NULL
        """)
        success_count = cur.rowcount
        conn.commit()
        print(f"    완벽 정규화된 데이터: {success_count:,}건")
        
        # 실패한 outcome을 failed 테이블에 삽입
        print("\n  [3] 실패한 outcome 분리 중...")
        cur.execute("""
            INSERT INTO outcome_normalized_failed
            SELECT *
            FROM outcome_normalized
            WHERE measure_code IS NULL 
               OR failure_reason IS NOT NULL
        """)
        failed_count = cur.rowcount
        conn.commit()
        print(f"    정규화 실패 데이터: {failed_count:,}건")
        
        # 실패 원인별 통계
        print("\n  [3] 실패 원인별 통계:")
        cur.execute("""
            SELECT 
                failure_reason,
                COUNT(*) as count
            FROM outcome_normalized_failed
            GROUP BY failure_reason
            ORDER BY count DESC
        """)
        failure_stats = cur.fetchall()
        for row in failure_stats:
            print(f"    {row['failure_reason']}: {row['count']:,}건")
        
        # 검증
        print("\n  [VERIFY] 데이터 검증 중...")
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM outcome_normalized_success) as success,
                (SELECT COUNT(*) FROM outcome_normalized_failed) as failed,
                (SELECT COUNT(*) FROM outcome_normalized) as total
        """)
        verify = cur.fetchone()
        
        print(f"\n    검증 결과:")
        print(f"      완벽 정규화: {verify['success']:,}건")
        print(f"      정규화 실패: {verify['failed']:,}건")
        print(f"      합계: {verify['success'] + verify['failed']:,}건")
        print(f"      원본 총계: {verify['total']:,}건")
        
        if verify['success'] + verify['failed'] == verify['total']:
            print(f"    [OK] 데이터 분리 검증 성공!")
        else:
            print(f"    [WARN] 데이터 분리 검증 실패! 합계가 일치하지 않습니다.")


def print_statistics(conn):
    """분리 결과 통계 출력"""
    print("\n" + "=" * 80)
    print("[STATISTICS] 분리 결과 통계")
    print("=" * 80)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Study 단위 통계 (제거: 한 Study는 일부 outcome 성공/실패가 섞일 수 있어 의미 없음)
        
        # Outcome 단위 통계
        print("\n[OUTCOME] Outcome 단위 통계:")
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                (SELECT COUNT(*) FROM outcome_normalized_success) as success_outcomes,
                (SELECT COUNT(*) FROM outcome_normalized_failed) as failed_outcomes
            FROM outcome_normalized
        """)
        outcome_stats = cur.fetchone()
        
        print(f"  전체 Outcomes: {outcome_stats['total_outcomes']:,}건")
        print(f"  완벽 정규화 Outcomes: {outcome_stats['success_outcomes']:,}건 ({outcome_stats['success_outcomes']/outcome_stats['total_outcomes']*100:.1f}%)")
        print(f"  정규화 실패 Outcomes: {outcome_stats['failed_outcomes']:,}건 ({outcome_stats['failed_outcomes']/outcome_stats['total_outcomes']*100:.1f}%)")
        
        # PRIMARY/SECONDARY 분류
        print("\n[PRIMARY/SECONDARY] 타입별 통계:")
        cur.execute("""
            SELECT 
                outcome_type,
                COUNT(*) as count
            FROM outcome_normalized_success
            GROUP BY outcome_type
            ORDER BY outcome_type
        """)
        success_by_type = cur.fetchall()
        
        print("  완벽 정규화:")
        for row in success_by_type:
            print(f"    {row['outcome_type']}: {row['count']:,}건")
        
        cur.execute("""
            SELECT 
                outcome_type,
                COUNT(*) as count
            FROM outcome_normalized_failed
            GROUP BY outcome_type
            ORDER BY outcome_type
        """)
        failed_by_type = cur.fetchall()
        
        print("  정규화 실패:")
        for row in failed_by_type:
            print(f"    {row['outcome_type']}: {row['count']:,}건")


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] 정규화 데이터 분리 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # 데이터 존재 여부 확인
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM outcome_normalized")
            normalized_count = cur.fetchone()[0]
            
            if normalized_count == 0:
                print("\n[ERROR] outcome_normalized 테이블에 데이터가 없습니다!")
                print("먼저 normalize_phase1.py를 실행하여 정규화를 수행하세요.")
                return
        
        # 테이블 생성
        create_separation_tables(conn)
        
        # 데이터 분리
        separate_data(conn)
        
        # 통계 출력
        print_statistics(conn)
        
        print("\n" + "=" * 80)
        print("[OK] 데이터 분리 완료!")
        print("=" * 80)
        print("\n생성된 테이블:")
        print("  1. outcome_normalized_success: 완벽 정규화된 데이터")
        print("     - measure_code IS NOT NULL AND failure_reason IS NULL")
        print("     - 개별 outcome 단위로 성공/실패 판단")
        print("  2. outcome_normalized_failed: 정규화 실패 데이터")
        print("     - measure_code IS NULL OR failure_reason IS NOT NULL")
        print("     - failure_reason 필드로 구분: 'MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED'")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

