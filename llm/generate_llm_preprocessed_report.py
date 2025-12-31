"""
LLM 전처리 성공 항목 검증 결과 문서화 스크립트

outcome_llm_preprocessed 테이블에서 llm_status = 'SUCCESS'인 항목들의
검증 결과를 분석하여 MD 파일로 문서화합니다.
"""

import os
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def get_validation_stats(conn):
    """검증 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_success,
                COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') as verified,
                COUNT(*) FILTER (WHERE llm_validation_status = 'UNCERTAIN') as uncertain,
                COUNT(*) FILTER (WHERE llm_validation_status = 'MEASURE_FAILED') as measure_failed,
                COUNT(*) FILTER (WHERE llm_validation_status = 'TIMEFRAME_FAILED') as timeframe_failed,
                COUNT(*) FILTER (WHERE llm_validation_status = 'BOTH_FAILED') as both_failed,
                COUNT(*) FILTER (WHERE llm_validation_status IS NULL) as not_validated,
                AVG(llm_validation_confidence) FILTER (WHERE llm_validation_status = 'VERIFIED') as avg_verified_confidence,
                AVG(llm_validation_confidence) as avg_confidence,
                MIN(llm_validation_confidence) FILTER (WHERE llm_validation_status = 'VERIFIED') as min_verified_confidence,
                MAX(llm_validation_confidence) FILTER (WHERE llm_validation_status = 'VERIFIED') as max_verified_confidence
            FROM outcome_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
        """)
        return cur.fetchone()


def get_status_detail_stats(conn):
    """상태별 상세 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_validation_status,
                COUNT(*) as count,
                AVG(llm_validation_confidence) as avg_confidence,
                MIN(llm_validation_confidence) as min_confidence,
                MAX(llm_validation_confidence) as max_confidence
            FROM outcome_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
            GROUP BY llm_validation_status
            ORDER BY count DESC
        """)
        return cur.fetchall()


def get_study_validation_stats(conn):
    """Study별 검증 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            WITH StudyValidationStatus AS (
                SELECT
                    nct_id,
                    COUNT(*) AS total_outcomes,
                    COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') AS verified_outcomes,
                    COUNT(*) FILTER (WHERE llm_validation_status = 'UNCERTAIN') AS uncertain_outcomes,
                    COUNT(*) FILTER (WHERE llm_validation_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED')) AS failed_outcomes
                FROM outcome_llm_preprocessed
                WHERE llm_status = 'SUCCESS'
                GROUP BY nct_id
            )
            SELECT
                COUNT(DISTINCT nct_id) AS total_studies,
                COUNT(DISTINCT nct_id) FILTER (WHERE total_outcomes = verified_outcomes) AS complete_verified_studies,
                COUNT(DISTINCT nct_id) FILTER (WHERE verified_outcomes > 0 AND failed_outcomes = 0) AS partial_verified_studies,
                COUNT(DISTINCT nct_id) FILTER (WHERE failed_outcomes > 0) AS has_failed_studies
            FROM StudyValidationStatus
        """)
        return cur.fetchone()


def get_measure_code_stats(conn):
    """Measure Code별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_measure_code,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') as verified_count,
                ROUND(
                    COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED')::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as verified_rate
            FROM outcome_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_measure_code IS NOT NULL
            GROUP BY llm_measure_code
            HAVING COUNT(*) >= 5
            ORDER BY total_count DESC
            LIMIT 20
        """)
        return cur.fetchall()


def get_time_unit_stats(conn):
    """Time Unit별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_time_unit,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED') as verified_count,
                ROUND(
                    COUNT(*) FILTER (WHERE llm_validation_status = 'VERIFIED')::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as verified_rate,
                AVG(llm_time_value) FILTER (WHERE llm_validation_status = 'VERIFIED') as avg_time_value
            FROM outcome_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_time_unit IS NOT NULL
            GROUP BY llm_time_unit
            ORDER BY total_count DESC
        """)
        return cur.fetchall()


def generate_report(conn, output_dir=None):
    """검증 결과 리포트 생성"""
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/llm_preprocessed_validation_report_{timestamp}.md'
    
    # 통계 조회
    validation_stats = get_validation_stats(conn)
    status_detail_stats = get_status_detail_stats(conn)
    study_stats = get_study_validation_stats(conn)
    measure_code_stats = get_measure_code_stats(conn)
    time_unit_stats = get_time_unit_stats(conn)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# LLM 전처리 성공 항목 검증 리포트\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        # 1. 전체 통계
        f.write('## 1. 전체 통계\n\n')
        if validation_stats and validation_stats['total_success'] > 0:
            total = validation_stats['total_success']
            f.write(f'- **전체 SUCCESS 항목**: {total:,}개\n')
            
            if validation_stats['not_validated'] > 0:
                f.write(f'- **미검증**: {validation_stats["not_validated"]:,}개 ({validation_stats["not_validated"]/total*100:.2f}%)\n')
            
            validated_total = total - (validation_stats['not_validated'] or 0)
            if validated_total > 0:
                f.write(f'- **검증 완료**: {validated_total:,}개\n\n')
                
                f.write('### 검증 결과 분포\n\n')
                f.write('| 검증 상태 | 개수 | 비율 |\n')
                f.write('|----------|------|------|\n')
                
                if validation_stats['verified']:
                    f.write(f"| VERIFIED | {validation_stats['verified']:,} | {validation_stats['verified']/validated_total*100:.2f}% |\n")
                if validation_stats['uncertain']:
                    f.write(f"| UNCERTAIN | {validation_stats['uncertain']:,} | {validation_stats['uncertain']/validated_total*100:.2f}% |\n")
                if validation_stats['measure_failed']:
                    f.write(f"| MEASURE_FAILED | {validation_stats['measure_failed']:,} | {validation_stats['measure_failed']/validated_total*100:.2f}% |\n")
                if validation_stats['timeframe_failed']:
                    f.write(f"| TIMEFRAME_FAILED | {validation_stats['timeframe_failed']:,} | {validation_stats['timeframe_failed']/validated_total*100:.2f}% |\n")
                if validation_stats['both_failed']:
                    f.write(f"| BOTH_FAILED | {validation_stats['both_failed']:,} | {validation_stats['both_failed']/validated_total*100:.2f}% |\n")
                
                f.write('\n')
                
                if validation_stats['avg_verified_confidence']:
                    f.write(f'- **VERIFIED 평균 신뢰도**: {float(validation_stats["avg_verified_confidence"]):.2f}\n')
                    if validation_stats['min_verified_confidence']:
                        f.write(f'- **VERIFIED 최소 신뢰도**: {float(validation_stats["min_verified_confidence"]):.2f}\n')
                    if validation_stats['max_verified_confidence']:
                        f.write(f'- **VERIFIED 최대 신뢰도**: {float(validation_stats["max_verified_confidence"]):.2f}\n')
                if validation_stats['avg_confidence']:
                    f.write(f'- **전체 평균 신뢰도**: {float(validation_stats["avg_confidence"]):.2f}\n')
        f.write('\n')
        
        # 2. 상태별 상세 통계
        f.write('## 2. 상태별 상세 통계\n\n')
        if status_detail_stats:
            f.write('| 검증 상태 | 개수 | 비율 | 평균 신뢰도 | 최소 신뢰도 | 최대 신뢰도 |\n')
            f.write('|----------|------|------|------------|------------|------------|\n')
            validated_total = sum(s['count'] for s in status_detail_stats)
            for stat in status_detail_stats:
                percentage = stat['count'] / validated_total * 100 if validated_total > 0 else 0
                avg_conf = float(stat['avg_confidence']) if stat['avg_confidence'] else 0
                min_conf = float(stat['min_confidence']) if stat['min_confidence'] else 0
                max_conf = float(stat['max_confidence']) if stat['max_confidence'] else 0
                f.write(f"| {stat['llm_validation_status']} | {stat['count']:,} | {percentage:.2f}% | {avg_conf:.2f} | {min_conf:.2f} | {max_conf:.2f} |\n")
        f.write('\n')
        
        # 3. Study별 통계
        f.write('## 3. Study별 통계\n\n')
        if study_stats:
            total_studies = study_stats['total_studies'] or 0
            if total_studies > 0:
                f.write(f'- **전체 Study**: {total_studies:,}개\n')
                
                if study_stats['complete_verified_studies']:
                    complete = study_stats['complete_verified_studies']
                    f.write(f'- **모든 outcome이 VERIFIED인 Study**: {complete:,}개 ({complete/total_studies*100:.2f}%)\n')
                
                if study_stats['partial_verified_studies']:
                    partial = study_stats['partial_verified_studies']
                    f.write(f'- **일부 VERIFIED인 Study (실패 없음)**: {partial:,}개 ({partial/total_studies*100:.2f}%)\n')
                
                if study_stats['has_failed_studies']:
                    failed = study_stats['has_failed_studies']
                    f.write(f'- **실패 항목이 있는 Study**: {failed:,}개 ({failed/total_studies*100:.2f}%)\n')
        f.write('\n')
        
        # 4. Measure Code별 통계
        f.write('## 4. Measure Code별 통계 (상위 20개)\n\n')
        if measure_code_stats:
            f.write('| Measure Code | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 |\n')
            f.write('|-------------|----------|--------------|-------------|\n')
            for stat in measure_code_stats:
                f.write(f"| {stat['llm_measure_code']} | {stat['total_count']:,} | {stat['verified_count']:,} | {stat['verified_rate']:.2f}% |\n")
        f.write('\n')
        
        # 5. Time Unit별 통계
        f.write('## 5. Time Unit별 통계\n\n')
        if time_unit_stats:
            f.write('| Time Unit | 전체 개수 | VERIFIED 개수 | VERIFIED 비율 | 평균 Time Value |\n')
            f.write('|----------|----------|--------------|-------------|----------------|\n')
            for stat in time_unit_stats:
                avg_value = float(stat['avg_time_value']) if stat['avg_time_value'] else 0
                f.write(f"| {stat['llm_time_unit']} | {stat['total_count']:,} | {stat['verified_count']:,} | {stat['verified_rate']:.2f}% | {avg_value:.1f} |\n")
        f.write('\n')
        
        # 6. 검증 방법 설명
        f.write('## 6. 검증 방법\n\n')
        f.write('1. **대상**: `outcome_llm_preprocessed` 테이블에서 `llm_status = \'SUCCESS\'`인 항목\n')
        f.write('2. **검증 내용**:\n')
        f.write('   - 원본 데이터(`measure_raw`, `time_frame_raw`)와 LLM 추출 결과(`llm_measure_code`, `llm_time_value`, `llm_time_unit`) 비교\n')
        f.write('   - Measure Code 일치 여부 확인\n')
        f.write('   - Time 정보 일치 여부 확인 (단일 시점, 범위 시점, 복수 시점 모두 고려)\n')
        f.write('3. **검증 상태**:\n')
        f.write('   - `VERIFIED`: 원본과 추출 결과가 완벽하게 일치\n')
        f.write('   - `UNCERTAIN`: 애매한 경우 또는 불확실한 매칭\n')
        f.write('   - `MEASURE_FAILED`: Measure Code 불일치\n')
        f.write('   - `TIMEFRAME_FAILED`: Time 정보 불일치\n')
        f.write('   - `BOTH_FAILED`: Measure Code와 Time 정보 모두 불일치\n')
        f.write('4. **검증 결과 저장**: `llm_validation_status`, `llm_validation_confidence`, `llm_validation_notes` 컬럼에 저장\n')
        f.write('\n')
        
        # 7. 요약
        f.write('## 7. 요약\n\n')
        if validation_stats and validation_stats['total_success'] > 0:
            total = validation_stats['total_success']
            validated_total = total - (validation_stats['not_validated'] or 0)
            
            if validated_total > 0:
                verified_count = validation_stats['verified'] or 0
                verified_rate = verified_count / validated_total * 100
                
                f.write(f'- LLM 전처리 성공 항목 중 **{verified_rate:.2f}%**가 VERIFIED로 검증됨\n')
                
                if study_stats and study_stats['total_studies']:
                    complete_studies = study_stats['complete_verified_studies'] or 0
                    total_studies = study_stats['total_studies']
                    if total_studies > 0:
                        f.write(f'- 전체 Study 중 **{complete_studies/total_studies*100:.2f}%**가 모든 outcome이 VERIFIED\n')
    
    print(f"[OK] 리포트 저장: {report_path}")
    return report_path


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] LLM 전처리 성공 항목 검증 결과 문서화")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        print("\n[STEP 1] 검증 통계 조회 중...")
        validation_stats = get_validation_stats(conn)
        
        if validation_stats and validation_stats['total_success'] > 0:
            total = validation_stats['total_success']
            print(f"\n[INFO] 전체 SUCCESS 항목: {total:,}개")
            
            validated_total = total - (validation_stats['not_validated'] or 0)
            if validated_total > 0:
                print(f"[INFO] 검증 완료: {validated_total:,}개")
                if validation_stats['verified']:
                    print(f"[INFO] VERIFIED: {validation_stats['verified']:,}개 ({validation_stats['verified']/validated_total*100:.2f}%)")
        else:
            print("[WARN] 검증 데이터가 없습니다.")
        
        print("\n[STEP 2] 리포트 생성 중...")
        report_path = generate_report(conn)
        
        print("\n" + "=" * 80)
        print("[OK] 문서화 완료!")
        print("=" * 80)
        print(f"\n생성된 리포트: {report_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

