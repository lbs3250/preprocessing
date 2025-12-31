"""
LLM 전처리 결과 요약 통계 생성 스크립트

outcome_llm_preprocessed 테이블의 통계를 조회하여 MD 파일로 저장합니다.
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


def get_total_stats(conn):
    """전체 Outcome 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED', 'API_FAILED')) as failed_count,
                ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
                ROUND(COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED', 'API_FAILED'))::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as failed_rate
            FROM outcome_llm_preprocessed
        """)
        return cur.fetchone()


def get_status_detail(conn):
    """상태별 상세 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_status,
                COUNT(*) as count,
                ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed) * 100, 2) as percentage
            FROM outcome_llm_preprocessed
            GROUP BY llm_status
            ORDER BY count DESC
        """)
        return cur.fetchall()


def get_study_stats(conn):
    """Study 기준 성공 현황"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            WITH StudyStats AS (
                SELECT 
                    nct_id,
                    COUNT(*) as total_outcomes,
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_outcomes,
                    COUNT(*) FILTER (WHERE llm_status IN ('MEASURE_FAILED', 'TIMEFRAME_FAILED', 'BOTH_FAILED')) as failed_outcomes
                FROM outcome_llm_preprocessed
                GROUP BY nct_id
            )
            SELECT 
                COUNT(*) as total_studies,
                COUNT(*) FILTER (WHERE success_outcomes = total_outcomes) as complete_success_studies,
                COUNT(*) FILTER (WHERE success_outcomes > 0 AND failed_outcomes > 0) as partial_success_studies,
                COUNT(*) FILTER (WHERE success_outcomes = 0) as complete_failed_studies,
                ROUND(COUNT(*) FILTER (WHERE success_outcomes = total_outcomes)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as complete_success_rate,
                ROUND(COUNT(*) FILTER (WHERE success_outcomes > 0 AND failed_outcomes > 0)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as partial_success_rate,
                ROUND(COUNT(*) FILTER (WHERE success_outcomes = 0)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as complete_failed_rate
            FROM StudyStats
        """)
        return cur.fetchone()


def get_measure_code_stats(conn):
    """Measure Code별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_measure_code,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate
            FROM outcome_llm_preprocessed
            WHERE llm_measure_code IS NOT NULL
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
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate,
                AVG(llm_time_value) FILTER (WHERE llm_status = 'SUCCESS') as avg_time_value
            FROM outcome_llm_preprocessed
            WHERE llm_time_unit IS NOT NULL
            GROUP BY llm_time_unit
            ORDER BY total_count DESC
        """)
        return cur.fetchall()


def get_validation_stats(conn):
    """검증 상태별 통계 (SUCCESS 항목 기준)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                llm_validation_status,
                COUNT(*) as count,
                ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE llm_status = 'SUCCESS' AND llm_validation_status IS NOT NULL) * 100, 2) as percentage,
                AVG(llm_validation_confidence) as avg_confidence
            FROM outcome_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
            GROUP BY llm_validation_status
            ORDER BY count DESC
        """)
        return cur.fetchall()


def get_failure_reason_stats(conn):
    """실패 이유별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                failure_reason,
                COUNT(*) as count,
                ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM outcome_llm_preprocessed WHERE failure_reason IS NOT NULL) * 100, 2) as percentage
            FROM outcome_llm_preprocessed
            WHERE failure_reason IS NOT NULL
            GROUP BY failure_reason
            ORDER BY count DESC
        """)
        return cur.fetchall()


def get_phase_stats(conn):
    """Phase별 통계"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                phase,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                ROUND(COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as success_rate
            FROM outcome_llm_preprocessed
            WHERE phase IS NOT NULL
            GROUP BY phase
            ORDER BY total_count DESC
        """)
        return cur.fetchall()


def generate_summary_report(conn, output_dir=None):
    """요약 통계 리포트 생성"""
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/llm_preprocessed_summary_{timestamp}.md'
    
    # 통계 조회
    total_stats = get_total_stats(conn)
    status_detail = get_status_detail(conn)
    study_stats = get_study_stats(conn)
    measure_code_stats = get_measure_code_stats(conn)
    time_unit_stats = get_time_unit_stats(conn)
    validation_stats = get_validation_stats(conn)
    failure_reason_stats = get_failure_reason_stats(conn)
    phase_stats = get_phase_stats(conn)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# LLM 전처리 결과 요약 통계\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        # 1. 전체 Outcome 통계
        f.write('## 1. 전체 Outcome 통계\n\n')
        if total_stats and total_stats['total_outcomes'] > 0:
            total = total_stats['total_outcomes']
            success = total_stats['success_count'] or 0
            failed = total_stats['failed_count'] or 0
            success_rate = float(total_stats['success_rate']) if total_stats['success_rate'] else 0
            failed_rate = float(total_stats['failed_rate']) if total_stats['failed_rate'] else 0
            
            f.write(f'총 Outcome **{total:,}건** 기준\n\n')
            f.write('| 구분 | 건수 | 비율 (%) |\n')
            f.write('|------|------|----------|\n')
            f.write(f'| 성공 | {success:,} | {success_rate:.1f} |\n')
            f.write(f'| 실패 | {failed:,} | {failed_rate:.1f} |\n')
            f.write('\n')
            
            # 상태별 상세
            if status_detail:
                f.write('### 상태별 상세 통계\n\n')
                f.write('| 상태 | 건수 | 비율 (%) |\n')
                f.write('|------|------|----------|\n')
                for stat in status_detail:
                    f.write(f"| {stat['llm_status']} | {stat['count']:,} | {float(stat['percentage']):.2f} |\n")
                f.write('\n')
        
        # 2. Study 기준 성공 현황
        f.write('## 2. Study 기준 성공 현황 (NCT ID 기준)\n\n')
        if study_stats and study_stats['total_studies']:
            total_studies = study_stats['total_studies']
            complete_success = study_stats['complete_success_studies'] or 0
            partial_success = study_stats['partial_success_studies'] or 0
            complete_failed = study_stats['complete_failed_studies'] or 0
            
            f.write(f'총 Study **{total_studies:,}건** 기준\n\n')
            f.write('| 카테고리 | Study 수 | 비율 (%) |\n')
            f.write('|----------|----------|----------|\n')
            f.write(f'| 완전히 성공 | {complete_success:,} | {float(study_stats["complete_success_rate"]):.2f} |\n')
            f.write(f'| 일부 성공 (일부 outcome 실패 포함) | {partial_success:,} | {float(study_stats["partial_success_rate"]):.2f} |\n')
            f.write(f'| 완전히 실패 | {complete_failed:,} | {float(study_stats["complete_failed_rate"]):.2f} |\n')
            f.write(f'| 합계 | {total_studies:,} | 100.00 |\n')
            f.write('\n')
        
        # 3. Measure Code별 통계
        f.write('## 3. Measure Code별 통계 (상위 20개)\n\n')
        if measure_code_stats:
            f.write('| Measure Code | 전체 개수 | 성공 개수 | 성공률 (%) |\n')
            f.write('|-------------|----------|----------|-----------|\n')
            for stat in measure_code_stats:
                f.write(f"| {stat['llm_measure_code']} | {stat['total_count']:,} | {stat['success_count']:,} | {float(stat['success_rate']):.2f} |\n")
            f.write('\n')
        
        # 4. Time Unit별 통계
        f.write('## 4. Time Unit별 통계\n\n')
        if time_unit_stats:
            f.write('| Time Unit | 전체 개수 | 성공 개수 | 성공률 (%) | 평균 Time Value |\n')
            f.write('|----------|----------|----------|-----------|----------------|\n')
            for stat in time_unit_stats:
                avg_value = float(stat['avg_time_value']) if stat['avg_time_value'] else 0
                f.write(f"| {stat['llm_time_unit']} | {stat['total_count']:,} | {stat['success_count']:,} | {float(stat['success_rate']):.2f} | {avg_value:.1f} |\n")
            f.write('\n')
        
        # 5. 검증 상태별 통계 (SUCCESS 항목 기준)
        f.write('## 5. 검증 상태별 통계 (SUCCESS 항목 기준)\n\n')
        if validation_stats:
            validated_total = sum(s['count'] for s in validation_stats)
            f.write(f'검증 완료 항목: **{validated_total:,}건**\n\n')
            f.write('| 검증 상태 | 건수 | 비율 (%) | 평균 신뢰도 |\n')
            f.write('|----------|------|----------|------------|\n')
            for stat in validation_stats:
                avg_conf = float(stat['avg_confidence']) if stat['avg_confidence'] else 0
                f.write(f"| {stat['llm_validation_status']} | {stat['count']:,} | {float(stat['percentage']):.2f} | {avg_conf:.2f} |\n")
            f.write('\n')
        
        # 6. 실패 이유별 통계
        f.write('## 6. 실패 이유별 통계\n\n')
        if failure_reason_stats:
            f.write('| 실패 이유 | 건수 | 비율 (%) |\n')
            f.write('|----------|------|----------|\n')
            for stat in failure_reason_stats:
                f.write(f"| {stat['failure_reason']} | {stat['count']:,} | {float(stat['percentage']):.2f} |\n")
            f.write('\n')
        
        # 7. Phase별 통계
        f.write('## 7. Phase별 통계\n\n')
        if phase_stats:
            f.write('| Phase | 전체 개수 | 성공 개수 | 성공률 (%) |\n')
            f.write('|-------|----------|----------|-----------|\n')
            for stat in phase_stats:
                f.write(f"| {stat['phase']} | {stat['total_count']:,} | {stat['success_count']:,} | {float(stat['success_rate']):.2f} |\n")
            f.write('\n')
        
        # 8. 요약
        f.write('## 8. 요약\n\n')
        if total_stats and study_stats:
            total = total_stats['total_outcomes']
            success = total_stats['success_count'] or 0
            total_studies = study_stats['total_studies'] or 0
            complete_success_studies = study_stats['complete_success_studies'] or 0
            
            f.write(f'- **전체 Outcome**: {total:,}건\n')
            f.write(f'- **성공 Outcome**: {success:,}건 ({float(total_stats["success_rate"]):.1f}%)\n')
            f.write(f'- **전체 Study**: {total_studies:,}건\n')
            f.write(f'- **완전히 성공한 Study**: {complete_success_studies:,}건 ({float(study_stats["complete_success_rate"]):.2f}%)\n')
    
    print(f"[OK] 리포트 저장: {report_path}")
    return report_path


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] LLM 전처리 결과 요약 통계 생성")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        print("\n[STEP 1] 통계 조회 중...")
        total_stats = get_total_stats(conn)
        
        if total_stats and total_stats['total_outcomes'] > 0:
            print(f"\n[INFO] 전체 Outcome: {total_stats['total_outcomes']:,}건")
            print(f"[INFO] 성공: {total_stats['success_count']:,}건 ({float(total_stats['success_rate']):.1f}%)")
            print(f"[INFO] 실패: {total_stats['failed_count']:,}건 ({float(total_stats['failed_rate']):.1f}%)")
        else:
            print("[WARN] 데이터가 없습니다.")
        
        print("\n[STEP 2] 리포트 생성 중...")
        report_path = generate_summary_report(conn)
        
        print("\n" + "=" * 80)
        print("[OK] 리포트 생성 완료!")
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

