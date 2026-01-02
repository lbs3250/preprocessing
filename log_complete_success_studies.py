"""
완전히 성공한 Study 개수 로깅 스크립트

성공 테이블에 있는 nct_id 중에서
실패 테이블에 없는 nct_id의 개수를 출력
(즉, 모든 outcome이 성공한 study)
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


def log_complete_success_studies():
    """완전히 성공한 Study 개수 로깅"""
    print("=" * 80)
    print("완전히 성공한 Study 개수 조회")
    print("=" * 80)
    print(f"조회 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 기본 통계
            print("[기본 통계]")
            print("-" * 80)
            
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT success_nct.nct_id) as complete_success_study_count,
                    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized_success) as total_success_studies,
                    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized_failed) as total_failed_studies,
                    (SELECT COUNT(DISTINCT nct_id) FROM outcome_normalized) as total_all_studies
                FROM (
                    SELECT DISTINCT nct_id 
                    FROM outcome_normalized_success
                ) success_nct
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM outcome_normalized_failed failed
                    WHERE failed.nct_id = success_nct.nct_id
                )
            """)
            
            stats = cur.fetchone()
            
            print(f"완전히 성공한 Study 개수: {stats['complete_success_study_count']:,}건")
            print(f"성공 테이블의 전체 Study 개수: {stats['total_success_studies']:,}건")
            print(f"실패 테이블의 전체 Study 개수: {stats['total_failed_studies']:,}건")
            print(f"전체 Study 개수: {stats['total_all_studies']:,}건")
            
            if stats['total_success_studies'] > 0:
                success_rate = stats['complete_success_study_count'] / stats['total_success_studies'] * 100
                print(f"\n성공 테이블 내 완전 성공 비율: {success_rate:.2f}%")
            
            if stats['total_all_studies'] > 0:
                overall_rate = stats['complete_success_study_count'] / stats['total_all_studies'] * 100
                print(f"전체 Study 대비 완전 성공 비율: {overall_rate:.2f}%")
            
            # 상세 카테고리별 통계
            print("\n[카테고리별 통계]")
            print("-" * 80)
            
            cur.execute("""
                SELECT 
                    '완전히 성공한 Study' as category,
                    COUNT(DISTINCT success_nct.nct_id) as count
                FROM (
                    SELECT DISTINCT nct_id 
                    FROM outcome_normalized_success
                ) success_nct
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM outcome_normalized_failed failed
                    WHERE failed.nct_id = success_nct.nct_id
                )

                UNION ALL

                SELECT 
                    '일부 성공한 Study (일부 실패 포함)' as category,
                    COUNT(DISTINCT mixed.nct_id) as count
                FROM (
                    SELECT DISTINCT nct_id 
                    FROM outcome_normalized_success
                    INTERSECT
                    SELECT DISTINCT nct_id 
                    FROM outcome_normalized_failed
                ) mixed

                UNION ALL

                SELECT 
                    '완전히 실패한 Study' as category,
                    COUNT(DISTINCT failed_nct.nct_id) as count
                FROM (
                    SELECT DISTINCT nct_id 
                    FROM outcome_normalized_failed
                ) failed_nct
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM outcome_normalized_success success
                    WHERE success.nct_id = failed_nct.nct_id
                )
            """)
            
            categories = cur.fetchall()
            
            total_categorized = sum(row['count'] for row in categories)
            
            for row in categories:
                count = row['count']
                percentage = (count / total_categorized * 100) if total_categorized > 0 else 0
                print(f"{row['category']}: {count:,}건 ({percentage:.2f}%)")
            
            print(f"\n합계: {total_categorized:,}건")
            
            # 검증
            if total_categorized != stats['total_all_studies']:
                print(f"\n[경고] 카테고리 합계({total_categorized:,})와 전체 Study 개수({stats['total_all_studies']:,})가 일치하지 않습니다.")
            else:
                print(f"\n[OK] 검증 완료: 카테고리 합계와 전체 Study 개수가 일치합니다.")
            
            # 로그 파일 저장
            log_file = f"log_complete_success_studies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("완전히 성공한 Study 개수 조회\n")
                f.write("=" * 80 + "\n")
                f.write(f"조회 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("[기본 통계]\n")
                f.write("-" * 80 + "\n")
                f.write(f"완전히 성공한 Study 개수: {stats['complete_success_study_count']:,}건\n")
                f.write(f"성공 테이블의 전체 Study 개수: {stats['total_success_studies']:,}건\n")
                f.write(f"실패 테이블의 전체 Study 개수: {stats['total_failed_studies']:,}건\n")
                f.write(f"전체 Study 개수: {stats['total_all_studies']:,}건\n")
                
                if stats['total_success_studies'] > 0:
                    success_rate = stats['complete_success_study_count'] / stats['total_success_studies'] * 100
                    f.write(f"\n성공 테이블 내 완전 성공 비율: {success_rate:.2f}%\n")
                
                if stats['total_all_studies'] > 0:
                    overall_rate = stats['complete_success_study_count'] / stats['total_all_studies'] * 100
                    f.write(f"전체 Study 대비 완전 성공 비율: {overall_rate:.2f}%\n")
                
                f.write("\n[카테고리별 통계]\n")
                f.write("-" * 80 + "\n")
                
                for row in categories:
                    count = row['count']
                    percentage = (count / total_categorized * 100) if total_categorized > 0 else 0
                    f.write(f"{row['category']}: {count:,}건 ({percentage:.2f}%)\n")
                
                f.write(f"\n합계: {total_categorized:,}건\n")
            
            print(f"\n[OK] 로그 파일 저장 완료: {log_file}")
            
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    log_complete_success_studies()

