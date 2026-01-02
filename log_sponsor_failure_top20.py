"""
기관별 Outcome 실패율 및 실패 카운트 Top 20 로깅 스크립트

1. 실패율 높은순 Top 20
2. 실패 카운트 높은순 Top 20
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

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


def log_sponsor_failure_top20():
    """기관별 실패율 및 실패 카운트 Top 20 로깅"""
    print("=" * 100)
    print("기관별 Outcome 실패율 및 실패 카운트 Top 20")
    print("=" * 100)
    print(f"조회 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. 실패율 높은순 Top 20
            print("[1] 실패율 높은순 Top 20")
            print("-" * 100)
            print(f"{'순위':<6} {'기관명':<50} {'실패 건수':<12} {'전체 건수':<12} {'실패율 (%)':<12}")
            print("-" * 100)
            
            cur.execute("""
                WITH sponsor_outcomes AS (
                    SELECT 
                        sp.name_raw as sponsor_name,
                        COUNT(*) FILTER (WHERE on_failed.outcome_id IS NOT NULL) as failed_count,
                        COUNT(*) as total_count
                    FROM outcome_normalized on_all
                    LEFT JOIN outcome_normalized_failed on_failed 
                        ON on_all.outcome_id = on_failed.outcome_id
                    LEFT JOIN study_party_raw sp 
                        ON on_all.nct_id = sp.nct_id 
                        AND sp.party_type = 'LEAD_SPONSOR'
                    WHERE sp.name_raw IS NOT NULL
                    GROUP BY sp.name_raw
                    HAVING COUNT(*) >= 5
                )
                SELECT 
                    sponsor_name,
                    failed_count,
                    total_count,
                    ROUND(failed_count::numeric / NULLIF(total_count, 0) * 100, 2) as failure_rate_percent
                FROM sponsor_outcomes
                ORDER BY failure_rate_percent DESC, failed_count DESC
                LIMIT 20
            """)
            
            failure_rate_results = cur.fetchall()
            
            for idx, row in enumerate(failure_rate_results, 1):
                sponsor_name = row['sponsor_name'][:48] if len(row['sponsor_name']) > 48 else row['sponsor_name']
                print(f"{idx:<6} {sponsor_name:<50} {row['failed_count']:<12,} {row['total_count']:<12,} {row['failure_rate_percent']:<12.2f}")
            
            # 2. 실패 카운트 높은순 Top 20
            print("\n[2] 실패 카운트 높은순 Top 20")
            print("-" * 100)
            print(f"{'순위':<6} {'기관명':<50} {'실패 건수':<12} {'전체 건수':<12} {'실패율 (%)':<12}")
            print("-" * 100)
            
            cur.execute("""
                WITH sponsor_outcomes AS (
                    SELECT 
                        sp.name_raw as sponsor_name,
                        COUNT(*) FILTER (WHERE on_failed.outcome_id IS NOT NULL) as failed_count,
                        COUNT(*) as total_count
                    FROM outcome_normalized on_all
                    LEFT JOIN outcome_normalized_failed on_failed 
                        ON on_all.outcome_id = on_failed.outcome_id
                    LEFT JOIN study_party_raw sp 
                        ON on_all.nct_id = sp.nct_id 
                        AND sp.party_type = 'LEAD_SPONSOR'
                    WHERE sp.name_raw IS NOT NULL
                    GROUP BY sp.name_raw
                    HAVING COUNT(*) >= 5
                )
                SELECT 
                    sponsor_name,
                    failed_count,
                    total_count,
                    ROUND(failed_count::numeric / NULLIF(total_count, 0) * 100, 2) as failure_rate_percent
                FROM sponsor_outcomes
                ORDER BY failed_count DESC, failure_rate_percent DESC
                LIMIT 20
            """)
            
            failure_count_results = cur.fetchall()
            
            for idx, row in enumerate(failure_count_results, 1):
                sponsor_name = row['sponsor_name'][:48] if len(row['sponsor_name']) > 48 else row['sponsor_name']
                print(f"{idx:<6} {sponsor_name:<50} {row['failed_count']:<12,} {row['total_count']:<12,} {row['failure_rate_percent']:<12.2f}")
            
            # 통계 요약
            print("\n[통계 요약]")
            print("-" * 100)
            
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT sp.name_raw) as total_sponsors,
                    COUNT(*) FILTER (WHERE on_failed.outcome_id IS NOT NULL) as total_failed_outcomes,
                    COUNT(*) as total_outcomes
                FROM outcome_normalized on_all
                LEFT JOIN outcome_normalized_failed on_failed 
                    ON on_all.outcome_id = on_failed.outcome_id
                LEFT JOIN study_party_raw sp 
                    ON on_all.nct_id = sp.nct_id 
                    AND sp.party_type = 'LEAD_SPONSOR'
                WHERE sp.name_raw IS NOT NULL
            """)
            
            summary = cur.fetchone()
            
            print(f"전체 기관 수: {summary['total_sponsors']:,}개")
            print(f"전체 Outcome 수: {summary['total_outcomes']:,}건")
            print(f"실패한 Outcome 수: {summary['total_failed_outcomes']:,}건")
            
            if summary['total_outcomes'] > 0:
                overall_failure_rate = summary['total_failed_outcomes'] / summary['total_outcomes'] * 100
                print(f"전체 실패율: {overall_failure_rate:.2f}%")
            
            # 로그 파일 저장
            log_file = f"log_sponsor_failure_top20_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("기관별 Outcome 실패율 및 실패 카운트 Top 20\n")
                f.write("=" * 100 + "\n")
                f.write(f"조회 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("[1] 실패율 높은순 Top 20\n")
                f.write("-" * 100 + "\n")
                f.write(f"{'순위':<6} {'기관명':<50} {'실패 건수':<12} {'전체 건수':<12} {'실패율 (%)':<12}\n")
                f.write("-" * 100 + "\n")
                
                for idx, row in enumerate(failure_rate_results, 1):
                    sponsor_name = row['sponsor_name'][:48] if len(row['sponsor_name']) > 48 else row['sponsor_name']
                    f.write(f"{idx:<6} {sponsor_name:<50} {row['failed_count']:<12,} {row['total_count']:<12,} {row['failure_rate_percent']:<12.2f}\n")
                
                f.write("\n[2] 실패 카운트 높은순 Top 20\n")
                f.write("-" * 100 + "\n")
                f.write(f"{'순위':<6} {'기관명':<50} {'실패 건수':<12} {'전체 건수':<12} {'실패율 (%)':<12}\n")
                f.write("-" * 100 + "\n")
                
                for idx, row in enumerate(failure_count_results, 1):
                    sponsor_name = row['sponsor_name'][:48] if len(row['sponsor_name']) > 48 else row['sponsor_name']
                    f.write(f"{idx:<6} {sponsor_name:<50} {row['failed_count']:<12,} {row['total_count']:<12,} {row['failure_rate_percent']:<12.2f}\n")
                
                f.write("\n[통계 요약]\n")
                f.write("-" * 100 + "\n")
                f.write(f"전체 기관 수: {summary['total_sponsors']:,}개\n")
                f.write(f"전체 Outcome 수: {summary['total_outcomes']:,}건\n")
                f.write(f"실패한 Outcome 수: {summary['total_failed_outcomes']:,}건\n")
                
                if summary['total_outcomes'] > 0:
                    overall_failure_rate = summary['total_failed_outcomes'] / summary['total_outcomes'] * 100
                    f.write(f"전체 실패율: {overall_failure_rate:.2f}%\n")
            
            print(f"\n[OK] 로그 파일 저장 완료: {log_file}")
            
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    log_sponsor_failure_top20()








