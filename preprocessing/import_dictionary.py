"""
CSV 파일에서 outcome_measure_dict 테이블로 데이터 삽입
"""

import os
import csv
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def import_dictionary(csv_file: str = 'dic.csv'):
    """
    CSV 파일을 읽어서 outcome_measure_dict 테이블에 삽입
    """
    print("=" * 80)
    print("Dictionary CSV Import")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # CSV 파일 읽기
        print(f"\n[1] CSV 파일 읽기: {csv_file}")
        dict_data = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 빈 행 스킵
                if not row.get('measure_code') or not row.get('canonical_name'):
                    continue
                
                dict_data.append({
                    'measure_code': row['measure_code'].strip(),
                    'canonical_name': row['canonical_name'].strip(),
                    'abbreviation': row.get('abbreviation', '').strip() or None,
                    'keywords': row.get('keywords', '').strip() or None,
                    'domain': row.get('domain', '').strip() or None,
                    'typical_role': row.get('typical_role', '').strip() or None,
                    'unit_type': None,  # dic.csv에 없음
                    'score_direction': None  # dic.csv에 없음
                })
        
        print(f"  총 {len(dict_data):,}개 항목 읽기 완료")
        
        # 기존 데이터 삭제 (선택사항)
        print("\n[2] 기존 Dictionary 데이터 삭제 중...")
        with conn.cursor() as cur:
            # 외래키 제약 때문에 DELETE 사용
            cur.execute("DELETE FROM outcome_measure_dict")
        conn.commit()
        print("  [OK] 기존 데이터 삭제 완료")
        
        # DB에 삽입
        print("\n[3] Dictionary 데이터 삽입 중...")
        insert_sql = """
            INSERT INTO outcome_measure_dict 
            (measure_code, canonical_name, abbreviation, keywords, domain, typical_role, unit_type, score_direction)
            VALUES (%(measure_code)s, %(canonical_name)s, %(abbreviation)s, %(keywords)s, 
                    %(domain)s, %(typical_role)s, %(unit_type)s, %(score_direction)s)
            ON CONFLICT (measure_code) 
            DO UPDATE SET
                canonical_name = EXCLUDED.canonical_name,
                abbreviation = EXCLUDED.abbreviation,
                keywords = EXCLUDED.keywords,
                domain = EXCLUDED.domain,
                typical_role = EXCLUDED.typical_role,
                unit_type = EXCLUDED.unit_type,
                score_direction = EXCLUDED.score_direction,
                updated_at = CURRENT_TIMESTAMP
        """
        
        with conn.cursor() as cur:
            execute_batch(cur, insert_sql, dict_data)
        conn.commit()
        
        print(f"  [OK] {len(dict_data):,}개 항목 삽입 완료")
        
        # 통계 출력
        print("\n[4] Dictionary 통계")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM outcome_measure_dict")
            total = cur.fetchone()[0]
            print(f"  총 Dictionary 항목 수: {total:,}개")
            
            cur.execute("""
                SELECT domain, COUNT(*) as count
                FROM outcome_measure_dict
                GROUP BY domain
                ORDER BY count DESC
            """)
            print("\n  Domain별 분포:")
            for row in cur.fetchall():
                print(f"    {row[0] or '(NULL)'}: {row[1]:,}개")
            
            cur.execute("""
                SELECT typical_role, COUNT(*) as count
                FROM outcome_measure_dict
                GROUP BY typical_role
                ORDER BY count DESC
            """)
            print("\n  Typical Role별 분포:")
            for row in cur.fetchall():
                print(f"    {row[0] or '(NULL)'}: {row[1]:,}개")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("[OK] Dictionary import 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()


if __name__ == "__main__":
    import_dictionary()

