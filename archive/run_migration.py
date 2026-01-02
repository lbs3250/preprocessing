"""
스키마 마이그레이션 실행 스크립트
update_schema.sql 파일을 실행합니다.
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


def execute_sql_file(conn, file_path):
    """SQL 파일을 읽어서 실행"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # SQL 문을 세미콜론으로 분리 (DO 블록은 별도 처리 필요)
    # 단순 분리로는 안되므로 전체를 한번에 실행
    with conn.cursor() as cur:
        try:
            # SQL 파일 전체 실행
            cur.execute(sql_content)
            
            # SELECT 결과가 있으면 출력
            if cur.description:
                results = cur.fetchall()
                print("\n[통계 결과]")
                print("-" * 60)
                for row in results:
                    print(f"{row[0]}: {row[1]:,}건")
                print("-" * 60)
            
            conn.commit()
            print("\n[OK] 마이그레이션 실행 완료!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] 마이그레이션 실행 중 오류 발생:")
            print(f"  {str(e)}")
            raise


def main():
    """메인 함수"""
    print("=" * 60)
    print("스키마 마이그레이션 실행")
    print("=" * 60)
    print("\n실행할 파일: update_schema.sql")
    print("\n변경 사항:")
    print("  - parsing_method 컬럼 추가 (RULE_BASED / LLM 구분)")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        print("\n[OK] 데이터베이스 연결 성공")
        
        # 테이블 존재 확인
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'outcome_normalized'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                print("\n[WARN] outcome_normalized 테이블이 존재하지 않습니다.")
                print("       schema.sql을 먼저 실행해주세요.")
                return
        
        # 마이그레이션 실행
        print("\n[진행] 마이그레이션 실행 중...")
        execute_sql_file(conn, 'update_schema.sql')
        
        # 최종 확인
        print("\n[확인] parsing_method 컬럼 확인 중...")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    column_name,
                    data_type,
                    column_default,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'outcome_normalized'
                  AND column_name = 'parsing_method'
            """)
            result = cur.fetchone()
            
            if result:
                print(f"\n[OK] parsing_method 컬럼 확인:")
                print(f"  컬럼명: {result['column_name']}")
                print(f"  데이터 타입: {result['data_type']}")
                print(f"  기본값: {result['column_default']}")
                print(f"  NULL 허용: {result['is_nullable']}")
            else:
                print("\n[WARN] parsing_method 컬럼을 찾을 수 없습니다.")
        
        conn.close()
        print("\n[OK] 모든 작업 완료!")
        
    except psycopg2.Error as e:
        print(f"\n[ERROR] 데이터베이스 오류:")
        print(f"  {str(e)}")
    except FileNotFoundError:
        print("\n[ERROR] update_schema.sql 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류:")
        print(f"  {str(e)}")


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


if __name__ == '__main__':
    main()

