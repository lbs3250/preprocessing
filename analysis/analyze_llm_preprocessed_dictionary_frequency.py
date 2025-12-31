"""
LLM 전처리 결과 Dictionary 빈도수 분석 스크립트

outcome_llm_preprocessed 테이블의 measure_code 검출 빈도수를 분석합니다.
- Outcome 기준 measure_code 검출 빈도수
- Study 기준 measure_code 검출 빈도수
"""

import os
import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import datetime
from typing import Dict, List
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

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 설정"""
    if platform.system() == 'Windows':
        font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕', 'Gulim', '굴림', 'Batang', '바탕', 'MS Gothic']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        selected_font = None
        font_path = None
        
        for font in font_list:
            if font in available_fonts:
                selected_font = font
                for font_file in fm.fontManager.ttflist:
                    if font_file.name == selected_font:
                        font_path = font_file.fname
                        break
                if font_path:
                    break
        
        if selected_font and font_path:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
        elif selected_font:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
    
    plt.rcParams['axes.unicode_minus'] = False

def get_korean_font_prop():
    """한글 폰트 속성 반환"""
    if platform.system() == 'Windows':
        font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕', 'Gulim', '굴림', 'Batang', '바탕', 'MS Gothic']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font in font_list:
            if font in available_fonts:
                for font_file in fm.fontManager.ttflist:
                    if font_file.name == font:
                        return fm.FontProperties(fname=font_file.fname)
        for font in font_list:
            if font in available_fonts:
                return fm.FontProperties(family=font)
    return fm.FontProperties()

# 폰트 설정 실행
setup_korean_font()
KOREAN_FONT_PROP = get_korean_font_prop()
sns.set_style("whitegrid")


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def get_measure_code_frequency_by_outcome(conn):
    """Outcome 기준 measure_code 검출 빈도수 (outcome_llm_preprocessed)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                olp.llm_measure_code as measure_code,
                COUNT(*) as detection_count,
                COUNT(DISTINCT olp.nct_id) as study_count
            FROM outcome_llm_preprocessed olp
            WHERE olp.llm_measure_code IS NOT NULL
              AND olp.llm_status = 'SUCCESS'
            GROUP BY olp.llm_measure_code
            ORDER BY detection_count DESC
        """)
        return cur.fetchall()


def get_measure_code_frequency_by_study(conn):
    """Study 기준 measure_code 검출 빈도수 (outcome_llm_preprocessed)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                olp.llm_measure_code as measure_code,
                COUNT(DISTINCT olp.nct_id) as study_count
            FROM outcome_llm_preprocessed olp
            WHERE olp.llm_measure_code IS NOT NULL
              AND olp.llm_status = 'SUCCESS'
            GROUP BY olp.llm_measure_code
            ORDER BY study_count DESC
        """)
        return cur.fetchall()


def plot_measure_code_frequency_by_outcome(outcome_stats, output_dir='visualization', top_n=50):
    """Outcome 기준 measure_code 빈도수 Bar Chart"""
    if not outcome_stats:
        return
    
    top_measures = outcome_stats[:top_n]
    codes = [m['measure_code'] for m in top_measures]
    counts = [m['detection_count'] for m in top_measures]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    bars = ax.barh(range(len(codes)), counts, color='#3498db', alpha=0.7)
    
    # 값 표시
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,}',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes, fontsize=9)
    ax.set_xlabel('검출 빈도수 (Outcome 기준)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Measure Code', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'LLM 전처리: Top {top_n} Measure Code 검출 빈도수 (Outcome 기준)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_measure_code_frequency_by_outcome_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_measure_code_frequency_by_outcome_top{top_n}.png")
    plt.close()


def plot_measure_code_frequency_by_study(study_stats, output_dir='visualization', top_n=50):
    """Study 기준 measure_code 빈도수 Bar Chart"""
    if not study_stats:
        return
    
    top_measures = study_stats[:top_n]
    codes = [m['measure_code'] for m in top_measures]
    counts = [m['study_count'] for m in top_measures]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    bars = ax.barh(range(len(codes)), counts, color='#2ecc71', alpha=0.7)
    
    # 값 표시
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2.,
               f'{count:,}',
               ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes, fontsize=9)
    ax.set_xlabel('검출 빈도수 (Study 기준)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('Measure Code', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title(f'LLM 전처리: Top {top_n} Measure Code 검출 빈도수 (Study 기준)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/llm_measure_code_frequency_by_study_top{top_n}.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/llm_measure_code_frequency_by_study_top{top_n}.png")
    plt.close()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] LLM 전처리 결과 Dictionary 빈도수 분석 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # Outcome 기준 measure_code 빈도수 조회
        print("\n[STEP 1] Outcome 기준 measure_code 빈도수 조회 중...")
        outcome_stats = get_measure_code_frequency_by_outcome(conn)
        
        if not outcome_stats:
            print("[WARN] Outcome 기준 measure_code 통계가 없습니다.")
        else:
            print(f"[INFO] 조회된 Measure Code: {len(outcome_stats):,}개")
        
        # Study 기준 measure_code 빈도수 조회
        print("\n[STEP 2] Study 기준 measure_code 빈도수 조회 중...")
        study_stats = get_measure_code_frequency_by_study(conn)
        
        if not study_stats:
            print("[WARN] Study 기준 measure_code 통계가 없습니다.")
        else:
            print(f"[INFO] 조회된 Measure Code: {len(study_stats):,}개")
        
        # 시각화
        print("\n[STEP 3] Outcome 기준 measure_code 빈도수 그래프 생성 중...")
        plot_measure_code_frequency_by_outcome(outcome_stats, top_n=50)
        
        print("\n[STEP 4] Study 기준 measure_code 빈도수 그래프 생성 중...")
        plot_measure_code_frequency_by_study(study_stats, top_n=50)
        
        # 통계 요약 출력
        print("\n" + "=" * 80)
        print("[INFO] 통계 요약")
        print("=" * 80)
        if outcome_stats:
            print(f"\nOutcome 기준 Top 5 Measure Code:")
            for i, stat in enumerate(outcome_stats[:5], 1):
                print(f"  {i}. {stat['measure_code']}: {stat['detection_count']:,}회 검출 ({stat['study_count']:,}개 Studies)")
        
        if study_stats:
            print(f"\nStudy 기준 Top 5 Measure Code:")
            for i, stat in enumerate(study_stats[:5], 1):
                print(f"  {i}. {stat['measure_code']}: {stat['study_count']:,}개 Studies")
        
        print("\n" + "=" * 80)
        print("[OK] LLM 전처리 결과 Dictionary 빈도수 분석 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        print("  - visualization/llm_measure_code_frequency_by_outcome_top50.png")
        print("  - visualization/llm_measure_code_frequency_by_study_top50.png")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

