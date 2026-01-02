"""
ADAS-Cog 관련 약어를 사전에 추가하는 스크립트
"""
import psycopg2
from dotenv import load_dotenv
import os

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

def add_adas_abbreviations():
    """ADAS-Cog 관련 약어를 사전에 추가"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 현재 keywords 확인
        cur.execute("SELECT measure_code, keywords FROM outcome_measure_dict WHERE measure_code = 'ADAS_COG'")
        row = cur.fetchone()
        
        if not row:
            print("ERROR: ADAS_COG 항목을 찾을 수 없습니다.")
            return
        
        current_keywords = row[1] or ''
        print(f"현재 keywords: {current_keywords}")
        
        # 추가할 약어들
        new_keywords = [
            'adas-cog11',
            'adas-cog-11', 
            'adas-cog11',
            'adas-cog14',
            'adas-cog-14',
            'adas-cog14',
            'adas-cog-13',
            'adas-cog13',
            'adas',
            'adas-cog'
        ]
        
        # 기존 keywords에 없는 것만 추가
        existing_keywords = set(current_keywords.lower().split(';'))
        keywords_to_add = [kw for kw in new_keywords if kw.lower() not in existing_keywords]
        
        if keywords_to_add:
            keywords_to_add_str = ';' + ';'.join(keywords_to_add)
            updated_keywords = current_keywords + keywords_to_add_str
            
            # 업데이트
            cur.execute("""
                UPDATE outcome_measure_dict 
                SET keywords = %s
                WHERE measure_code = 'ADAS_COG'
            """, (updated_keywords,))
            
            conn.commit()
            print(f"추가된 keywords: {keywords_to_add_str}")
            print(f"업데이트된 keywords: {updated_keywords}")
        else:
            print("추가할 keywords가 없습니다 (이미 모두 포함되어 있음).")
        
        # 확인
        cur.execute("SELECT measure_code, canonical_name, abbreviation, keywords FROM outcome_measure_dict WHERE measure_code = 'ADAS_COG'")
        row = cur.fetchone()
        print(f"\n최종 확인:")
        print(f"measure_code: {row[0]}")
        print(f"canonical_name: {row[1]}")
        print(f"abbreviation: {row[2]}")
        print(f"keywords: {row[3]}")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    add_adas_abbreviations()

