"""
룰베이스 vs LLM 전처리 성공률 비교 시각화 스크립트

normalization_history 테이블의 룰베이스 전처리 결과와
outcome_llm_preprocessed 테이블의 LLM 전처리 결과를 비교합니다.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

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
            print(f"[INFO] 한글 폰트 설정: {selected_font} (경로: {font_path})")
        elif selected_font:
            plt.rcParams['font.family'] = 'sans-serif'
            current_sans = plt.rcParams['font.sans-serif']
            new_sans = [selected_font] + [f for f in current_sans if f != selected_font]
            plt.rcParams['font.sans-serif'] = new_sans
            print(f"[INFO] 한글 폰트 설정: {selected_font}")
        else:
            plt.rcParams['font.family'] = 'DejaVu Sans'
            print("[WARN] 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
    elif platform.system() == 'Darwin':
        plt.rcParams['font.family'] = 'AppleGothic'
        print("[INFO] 한글 폰트 설정: AppleGothic")
    else:
        plt.rcParams['font.family'] = 'NanumGothic'
        print("[INFO] 한글 폰트 설정: NanumGothic")
    
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


def get_rule_based_statistics(conn):
    """룰베이스 전처리 통계 조회 (normalization_history)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                processing_round,
                execution_date,
                total_outcomes,
                success_count,
                failed_count,
                success_rate,
                notes
            FROM normalization_history
            ORDER BY execution_date ASC
        """)
        return cur.fetchall()


def get_llm_statistics(conn):
    """LLM 전처리 통계 조회 (outcome_llm_preprocessed)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_outcomes,
                COUNT(*) FILTER (WHERE llm_status = 'SUCCESS') as success_count,
                COUNT(*) FILTER (WHERE llm_status != 'SUCCESS') as failed_count,
                ROUND(
                    COUNT(*) FILTER (WHERE llm_status = 'SUCCESS')::NUMERIC / 
                    COUNT(*)::NUMERIC * 100, 
                    2
                ) as success_rate
            FROM outcome_llm_preprocessed
        """)
        return cur.fetchone()


def plot_rule_vs_llm_success_rate(rule_stats, llm_stats, output_dir='visualization'):
    """룰베이스 vs LLM 전처리 성공률 비교 Bar Chart"""
    if not rule_stats:
        print("[WARN] 룰베이스 전처리 통계가 없습니다.")
        return
    
    if not llm_stats:
        print("[WARN] LLM 전처리 통계가 없습니다.")
        return
    
    # 룰베이스 전처리 라운드별 데이터 준비
    rounds = []
    rule_success_rates = []
    rule_labels = []
    
    for stat in rule_stats:
        round_name = stat['processing_round']
        success_rate = float(stat['success_rate'])
        rounds.append(round_name)
        rule_success_rates.append(success_rate)
        rule_labels.append(f"{success_rate:.2f}%\n({stat['success_count']:,}/{stat['total_outcomes']:,})")
    
    # LLM 전처리 데이터 추가
    llm_success_rate = float(llm_stats['success_rate'])
    rounds.append('LLM')
    rule_success_rates.append(llm_success_rate)
    rule_labels.append(f"{llm_success_rate:.2f}%\n({llm_stats['success_count']:,}/{llm_stats['total_outcomes']:,})")
    
    # 색상 설정: 룰베이스는 파란색 계열, LLM은 초록색
    colors = []
    for i, round_name in enumerate(rounds):
        if round_name == 'LLM':
            colors.append('#2ecc71')  # 초록색
        else:
            # 룰베이스는 파란색 계열 (라운드별로 다른 색조)
            if i == 0:
                colors.append('#3498db')  # 밝은 파란색
            elif i == 1:
                colors.append('#2980b9')  # 중간 파란색
            elif i == 2:
                colors.append('#1f618d')  # 진한 파란색
            else:
                colors.append('#5dade2')  # 연한 파란색
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    bars = ax.bar(rounds, rule_success_rates, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 값 표시 (막대 위 중앙)
    for bar, label in zip(bars, rule_labels):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               label,
               ha='center', va='bottom', fontsize=10, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    
    ax.set_xlabel('전처리 방법', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('성공률 (%)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('룰베이스 vs LLM 전처리 성공률 비교', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    
    # 범례 추가
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', alpha=0.8, label='룰베이스 전처리'),
        Patch(facecolor='#2ecc71', alpha=0.8, label='LLM 전처리')
    ]
    ax.legend(handles=legend_elements, prop=KOREAN_FONT_PROP, loc='upper right')
    
    # 통계 정보 표시
    max_rule_rate = max(rule_success_rates[:-1]) if len(rule_success_rates) > 1 else rule_success_rates[0]
    diff = llm_success_rate - max_rule_rate
    
    stats_text = f'최고 룰베이스 성공률: {max_rule_rate:.2f}%\n'
    stats_text += f'LLM 성공률: {llm_success_rate:.2f}%\n'
    stats_text += f'차이: {diff:+.2f}%'
    
    ax.text(0.02, 0.98, stats_text,
           transform=ax.transAxes, ha='left', va='top',
           fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
           fontproperties=KOREAN_FONT_PROP)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/rule_vs_llm_success_rate_comparison.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/rule_vs_llm_success_rate_comparison.png")
    plt.close()


def plot_normalization_round_success_rate_with_llm(rule_stats, llm_stats, output_dir='visualization'):
    """정규화 단계별 성공률 (LLM 포함)"""
    if not rule_stats:
        print("[WARN] 룰베이스 전처리 통계가 없습니다.")
        return
    
    if not llm_stats:
        print("[WARN] LLM 전처리 통계가 없습니다.")
        return
    
    # 룰베이스 전처리 라운드별 데이터 준비
    rounds = []
    success_rates = []
    labels = []
    
    for stat in rule_stats:
        round_name = stat['processing_round']
        success_rate = float(stat['success_rate'])
        rounds.append(round_name)
        success_rates.append(success_rate)
        labels.append(f"{success_rate:.2f}%\n({stat['success_count']:,}/{stat['total_outcomes']:,})")
    
    # LLM 전처리 데이터 추가
    llm_success_rate = float(llm_stats['success_rate'])
    rounds.append('LLM')
    success_rates.append(llm_success_rate)
    labels.append(f"{llm_success_rate:.2f}%\n({llm_stats['success_count']:,}/{llm_stats['total_outcomes']:,})")
    
    # 색상 설정: 룰베이스는 파란색 계열, LLM은 초록색
    colors = []
    for i, round_name in enumerate(rounds):
        if round_name == 'LLM':
            colors.append('#2ecc71')  # 초록색
        else:
            colors.append('#3498db')  # 파란색
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    bars = ax.bar(rounds, success_rates, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 값 표시 (막대 위 중앙)
    for bar, label in zip(bars, labels):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               label,
               ha='center', va='bottom', fontsize=10, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    
    ax.set_xlabel('정규화 단계', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_ylabel('성공률 (%)', fontsize=12, fontweight='bold', fontproperties=KOREAN_FONT_PROP)
    ax.set_title('정규화 단계별 성공률 (룰베이스 + LLM)', fontsize=14, fontweight='bold', pad=20, fontproperties=KOREAN_FONT_PROP)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    
    # 범례 추가
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', alpha=0.8, label='룰베이스 전처리'),
        Patch(facecolor='#2ecc71', alpha=0.8, label='LLM 전처리')
    ]
    ax.legend(handles=legend_elements, prop=KOREAN_FONT_PROP, loc='upper right')
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/normalization_round_success_rate_with_llm.png', dpi=300, bbox_inches='tight')
    print(f"[OK] 그래프 저장: {output_dir}/normalization_round_success_rate_with_llm.png")
    plt.close()


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] 룰베이스 vs LLM 전처리 성공률 비교 시각화 시작")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        
        # 룰베이스 전처리 통계 조회
        print("\n[STEP 1] 룰베이스 전처리 통계 조회 중...")
        rule_stats = get_rule_based_statistics(conn)
        
        if not rule_stats:
            print("[WARN] 룰베이스 전처리 통계가 없습니다.")
        else:
            print(f"[INFO] 조회된 룰베이스 라운드: {len(rule_stats)}개")
            for stat in rule_stats:
                print(f"  - {stat['processing_round']}: {float(stat['success_rate']):.2f}% ({stat['success_count']:,}/{stat['total_outcomes']:,})")
        
        # LLM 전처리 통계 조회
        print("\n[STEP 2] LLM 전처리 통계 조회 중...")
        llm_stats = get_llm_statistics(conn)
        
        if not llm_stats:
            print("[WARN] LLM 전처리 통계가 없습니다.")
        else:
            print(f"[INFO] LLM 전처리 성공률: {float(llm_stats['success_rate']):.2f}% ({llm_stats['success_count']:,}/{llm_stats['total_outcomes']:,})")
        
        if not rule_stats or not llm_stats:
            print("[ERROR] 비교할 데이터가 부족합니다!")
            conn.close()
            return
        
        # 시각화
        print("\n[STEP 3] 룰베이스 vs LLM 성공률 비교 그래프 생성 중...")
        plot_rule_vs_llm_success_rate(rule_stats, llm_stats)
        
        print("\n[STEP 4] 정규화 단계별 성공률 그래프 생성 중 (LLM 포함)...")
        plot_normalization_round_success_rate_with_llm(rule_stats, llm_stats)
        
        print("\n" + "=" * 80)
        print("[OK] 시각화 완료!")
        print("=" * 80)
        print("\n생성된 파일:")
        print("  - visualization/rule_vs_llm_success_rate_comparison.png")
        print("  - visualization/normalization_round_success_rate_with_llm.png")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()

