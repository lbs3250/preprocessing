"""
Phase NA인 항목들의 OverallStatus 분포 조회
"""

import os
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


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def main():
    """메인 함수"""
    print("=" * 80)
    print("Phase NA인 항목들의 OverallStatus 분포")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Phase NA인 항목들의 OverallStatus 분포
            cur.execute("""
                SELECT 
                    COALESCE(s.overall_status, 'UNKNOWN') as overall_status,
                    COUNT(DISTINCT o.nct_id) as study_count,
                    COUNT(*) as outcome_count,
                    COUNT(*) FILTER (WHERE o.measure_code IS NOT NULL AND o.failure_reason IS NULL) as success_count,
                    COUNT(*) FILTER (WHERE o.measure_code IS NULL OR o.failure_reason IS NOT NULL) as failed_count,
                    ROUND(
                        COUNT(*) FILTER (WHERE o.measure_code IS NOT NULL AND o.failure_reason IS NULL)::NUMERIC / 
                        COUNT(*)::NUMERIC * 100, 
                        2
                    ) as success_rate
                FROM outcome_normalized o
                LEFT JOIN study_status_raw s ON o.nct_id = s.nct_id
                WHERE o.phase = 'NA' OR o.phase IS NULL
                GROUP BY s.overall_status
                ORDER BY outcome_count DESC
            """)
            
            results = cur.fetchall()
            
            print("\nPhase NA인 항목들의 OverallStatus 분포:\n")
            print(f"{'Overall Status':<30} {'Study 수':<15} {'Outcome 수':<15} {'성공':<15} {'실패':<15} {'성공률':<10}")
            print("-" * 100)
            
            total_studies = 0
            total_outcomes = 0
            total_success = 0
            total_failed = 0
            
            for row in results:
                print(f"{row['overall_status']:<30} {row['study_count']:<15,} {row['outcome_count']:<15,} "
                      f"{row['success_count']:<15,} {row['failed_count']:<15,} {row['success_rate']:<10.2f}%")
                total_studies += row['study_count']
                total_outcomes += row['outcome_count']
                total_success += row['success_count']
                total_failed += row['failed_count']
            
            print("-" * 100)
            total_rate = (total_success / total_outcomes * 100) if total_outcomes > 0 else 0
            print(f"{'합계':<30} {total_studies:<15,} {total_outcomes:<15,} "
                  f"{total_success:<15,} {total_failed:<15,} {total_rate:<10.2f}%")
            
            # Phase NA인 항목 중 OverallStatus가 없는 경우 상세 조회
            print("\n\nPhase NA이면서 OverallStatus가 없는 항목 (UNKNOWN):")
            cur.execute("""
                SELECT 
                    o.nct_id,
                    COUNT(*) as outcome_count,
                    COUNT(*) FILTER (WHERE o.measure_code IS NOT NULL AND o.failure_reason IS NULL) as success_count,
                    COUNT(*) FILTER (WHERE o.measure_code IS NULL OR o.failure_reason IS NOT NULL) as failed_count
                FROM outcome_normalized o
                LEFT JOIN study_status_raw s ON o.nct_id = s.nct_id
                WHERE (o.phase = 'NA' OR o.phase IS NULL)
                  AND (s.overall_status IS NULL OR s.overall_status = 'UNKNOWN')
                GROUP BY o.nct_id
                ORDER BY outcome_count DESC
                LIMIT 20
            """)
            
            unknown_results = cur.fetchall()
            if unknown_results:
                print(f"\n{'NCT ID':<20} {'Outcome 수':<15} {'성공':<15} {'실패':<15}")
                print("-" * 65)
                for row in unknown_results:
                    print(f"{row['nct_id']:<20} {row['outcome_count']:<15,} {row['success_count']:<15,} {row['failed_count']:<15,}")
            else:
                print("  없음")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

