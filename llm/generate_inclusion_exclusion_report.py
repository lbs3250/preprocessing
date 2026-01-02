"""
Inclusion/Exclusion 전처리 및 Validation 종합 보고서 생성 스크립트

전처리 결과와 validation 결과를 포함한 종합 통계 보고서를 생성합니다.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
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

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def get_preprocessing_stats(conn) -> Dict:
    """전처리 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN llm_status = 'SUCCESS' THEN 1 END) as success,
                COUNT(CASE WHEN llm_status = 'INCLUSION_FAILED' THEN 1 END) as inclusion_failed,
                COUNT(CASE WHEN llm_status = 'EXCLUSION_FAILED' THEN 1 END) as exclusion_failed,
                COUNT(CASE WHEN llm_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                COUNT(CASE WHEN llm_status = 'API_FAILED' THEN 1 END) as api_failed,
                COUNT(inclusion_criteria) as with_inclusion,
                COUNT(exclusion_criteria) as with_exclusion,
                COUNT(CASE WHEN inclusion_criteria IS NOT NULL AND exclusion_criteria IS NOT NULL THEN 1 END) as complete
            FROM inclusion_exclusion_llm_preprocessed
        """)
        stats = cur.fetchone()
        
        # Criteria 개수 통계 (Python에서 계산)
        cur.execute("""
            SELECT 
                inclusion_criteria,
                exclusion_criteria
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
        """)
        all_criteria = cur.fetchall()
        
        inclusion_counts = []
        exclusion_counts = []
        
        for row in all_criteria:
            if row['inclusion_criteria']:
                try:
                    inc = json.loads(row['inclusion_criteria']) if isinstance(row['inclusion_criteria'], str) else row['inclusion_criteria']
                    if isinstance(inc, list):
                        inclusion_counts.append(len(inc))
                except:
                    pass
            
            if row['exclusion_criteria']:
                try:
                    exc = json.loads(row['exclusion_criteria']) if isinstance(row['exclusion_criteria'], str) else row['exclusion_criteria']
                    if isinstance(exc, list):
                        exclusion_counts.append(len(exc))
                except:
                    pass
        
        criteria_stats = {
            'avg_inclusion_count': sum(inclusion_counts) / len(inclusion_counts) if inclusion_counts else None,
            'avg_exclusion_count': sum(exclusion_counts) / len(exclusion_counts) if exclusion_counts else None,
            'max_inclusion_count': max(inclusion_counts) if inclusion_counts else None,
            'max_exclusion_count': max(exclusion_counts) if exclusion_counts else None,
            'min_inclusion_count': min(inclusion_counts) if inclusion_counts else None,
            'min_exclusion_count': min(exclusion_counts) if exclusion_counts else None
        }
        
        # Confidence 통계
        cur.execute("""
            SELECT 
                AVG(llm_confidence) as avg_confidence,
                MIN(llm_confidence) as min_confidence,
                MAX(llm_confidence) as max_confidence,
                COUNT(CASE WHEN llm_confidence >= 0.9 THEN 1 END) as high_confidence,
                COUNT(CASE WHEN llm_confidence >= 0.7 AND llm_confidence < 0.9 THEN 1 END) as medium_confidence,
                COUNT(CASE WHEN llm_confidence < 0.7 THEN 1 END) as low_confidence
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS' AND llm_confidence IS NOT NULL
        """)
        confidence_stats = cur.fetchone()
        
        return {
            'stats': stats,
            'criteria_stats': criteria_stats,
            'confidence_stats': confidence_stats
        }


def get_validation_stats(conn) -> Dict:
    """Validation 통계 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 전체 검증 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total_validated,
                COUNT(CASE WHEN llm_validation_status = 'VERIFIED' THEN 1 END) as verified,
                COUNT(CASE WHEN llm_validation_status = 'UNCERTAIN' THEN 1 END) as uncertain,
                COUNT(CASE WHEN llm_validation_status = 'INCLUSION_FAILED' THEN 1 END) as inclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'EXCLUSION_FAILED' THEN 1 END) as exclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                COUNT(CASE WHEN needs_manual_review = TRUE THEN 1 END) as needs_manual_review,
                COUNT(CASE WHEN needs_manual_review = FALSE THEN 1 END) as no_manual_review,
                AVG(llm_validation_confidence) FILTER (WHERE llm_validation_status = 'VERIFIED') as avg_verified_confidence,
                AVG(llm_validation_confidence) as avg_confidence,
                AVG(validation_consistency_score) as avg_consistency,
                MIN(validation_consistency_score) as min_consistency,
                MAX(validation_consistency_score) as max_consistency
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
        """)
        validation_stats = cur.fetchone()
        
        # 수동 검토 불필요 항목 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN llm_validation_status = 'VERIFIED' THEN 1 END) as verified,
                COUNT(CASE WHEN llm_validation_status = 'UNCERTAIN' THEN 1 END) as uncertain,
                COUNT(CASE WHEN llm_validation_status = 'INCLUSION_FAILED' THEN 1 END) as inclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'EXCLUSION_FAILED' THEN 1 END) as exclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                AVG(llm_validation_confidence) as avg_confidence,
                AVG(validation_consistency_score) as avg_consistency,
                MIN(validation_consistency_score) as min_consistency,
                MAX(validation_consistency_score) as max_consistency
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
              AND needs_manual_review = FALSE
        """)
        no_review_stats = cur.fetchone()
        
        # 수동 검토 필요 항목 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN llm_validation_status = 'VERIFIED' THEN 1 END) as verified,
                COUNT(CASE WHEN llm_validation_status = 'UNCERTAIN' THEN 1 END) as uncertain,
                COUNT(CASE WHEN llm_validation_status = 'INCLUSION_FAILED' THEN 1 END) as inclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'EXCLUSION_FAILED' THEN 1 END) as exclusion_failed,
                COUNT(CASE WHEN llm_validation_status = 'BOTH_FAILED' THEN 1 END) as both_failed,
                AVG(llm_validation_confidence) as avg_confidence,
                AVG(validation_consistency_score) as avg_consistency,
                MIN(validation_consistency_score) as min_consistency,
                MAX(validation_consistency_score) as max_consistency
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND llm_validation_status IS NOT NULL
              AND needs_manual_review = TRUE
        """)
        manual_review_stats = cur.fetchone()
        
        # 일관성 점수 분포
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE validation_consistency_score >= 0.67) as high_consistency,
                COUNT(*) FILTER (WHERE validation_consistency_score >= 0.33 AND validation_consistency_score < 0.67) as medium_consistency,
                COUNT(*) FILTER (WHERE validation_consistency_score < 0.33) as low_consistency
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
              AND validation_consistency_score IS NOT NULL
        """)
        consistency_dist = cur.fetchone()
        
        # 검증 이력 통계
        cur.execute("""
            SELECT 
                COUNT(DISTINCT nct_id) as total_studies_validated,
                COUNT(*) as total_validation_runs,
                AVG(validation_confidence) as avg_validation_confidence,
                COUNT(CASE WHEN validation_notes IS NOT NULL AND validation_notes != '' THEN 1 END) as with_notes
            FROM inclusion_exclusion_llm_validation_history
        """)
        history_stats = cur.fetchone()
        
        return {
            'validation_stats': validation_stats,
            'consistency_dist': consistency_dist,
            'history_stats': history_stats,
            'no_review_stats': no_review_stats,
            'manual_review_stats': manual_review_stats
        }


def get_feature_distribution(conn, limit: int = 20) -> List[Dict]:
    """Feature 분포 조회 (상위 N개)"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                inclusion_criteria,
                exclusion_criteria
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = 'SUCCESS'
        """)
        all_data = cur.fetchall()
        
        # Python에서 feature 추출
        feature_counts = {}
        for row in all_data:
            # Inclusion features
            if row['inclusion_criteria']:
                try:
                    inc = json.loads(row['inclusion_criteria']) if isinstance(row['inclusion_criteria'], str) else row['inclusion_criteria']
                    if isinstance(inc, list):
                        for item in inc:
                            if isinstance(item, dict):
                                feature = item.get('feature')
                                if feature and feature.strip():
                                    feature_counts[feature] = feature_counts.get(feature, 0) + 1
                except:
                    pass
            
            # Exclusion features
            if row['exclusion_criteria']:
                try:
                    exc = json.loads(row['exclusion_criteria']) if isinstance(row['exclusion_criteria'], str) else row['exclusion_criteria']
                    if isinstance(exc, list):
                        for item in exc:
                            if isinstance(item, dict):
                                feature = item.get('feature')
                                if feature and feature.strip():
                                    feature_counts[feature] = feature_counts.get(feature, 0) + 1
                except:
                    pass
        
        # 상위 N개 반환
        sorted_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'feature': f, 'usage_count': c} for f, c in sorted_features]


def get_sample_results(conn, status: str = 'SUCCESS', limit: int = 3) -> List[Dict]:
    """샘플 결과 조회"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                nct_id,
                eligibility_criteria_raw,
                inclusion_criteria,
                exclusion_criteria,
                llm_confidence,
                llm_notes,
                llm_validation_status,
                llm_validation_confidence,
                llm_validation_notes,
                validation_consistency_score,
                needs_manual_review
            FROM inclusion_exclusion_llm_preprocessed
            WHERE llm_status = %s
            ORDER BY nct_id
            LIMIT %s
        """, (status, limit))
        return cur.fetchone() if limit == 1 else cur.fetchall()


def format_criteria_list(criteria_json: str, max_items: int = 5) -> str:
    """Criteria 리스트 포맷팅"""
    if not criteria_json:
        return "N/A"
    
    try:
        criteria = json.loads(criteria_json) if isinstance(criteria_json, str) else criteria_json
        if not isinstance(criteria, list):
            return "N/A"
        
        items = []
        for idx, item in enumerate(criteria[:max_items]):
            if isinstance(item, dict):
                feature = item.get('feature', 'N/A')
                operator = item.get('operator', 'N/A')
                value = item.get('value', 'N/A')
                unit = item.get('unit')
                confidence = item.get('confidence')
                
                item_str = f"**{idx + 1}.** Feature: `{feature}`, Operator: `{operator}`, Value: `{value}`"
                if unit:
                    item_str += f", Unit: `{unit}`"
                if confidence:
                    item_str += f", Confidence: `{confidence}`"
                items.append(item_str)
            else:
                items.append(f"**{idx + 1}.** {str(item)}")
        
        if len(criteria) > max_items:
            items.append(f"\n*... 외 {len(criteria) - max_items}개 항목*")
        
        return '\n\n'.join(items)
    except:
        return "파싱 실패"


def generate_report(output_dir: Optional[str] = None) -> str:
    """종합 보고서 생성"""
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(output_dir, f'inclusion_exclusion_comprehensive_report_{timestamp}.md')
    
    conn = get_db_connection()
    
    try:
        # 통계 수집
        print("[INFO] 전처리 통계 수집 중...")
        prep_stats = get_preprocessing_stats(conn)
        
        print("[INFO] Validation 통계 수집 중...")
        val_stats = get_validation_stats(conn)
        
        print("[INFO] Feature 분포 수집 중...")
        features = get_feature_distribution(conn, 20)
        
        print("[INFO] 샘플 결과 수집 중...")
        success_samples = get_sample_results(conn, 'SUCCESS', 3)
        
        # 보고서 작성
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('# Inclusion/Exclusion LLM 전처리 및 Validation 종합 보고서\n\n')
            f.write(f'생성일: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            f.write('---\n\n')
            
            # 1. 전체 요약
            f.write('## 1. 전체 요약\n\n')
            stats = prep_stats['stats']
            val_stat = val_stats['validation_stats']
            
            f.write('### 1.1 전처리 요약\n\n')
            f.write(f'- **전체 레코드**: {stats["total"]:,}개\n')
            if stats['total'] > 0:
                f.write(f'- **성공 (SUCCESS)**: {stats["success"]:,}개 ({stats["success"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **Inclusion 실패**: {stats["inclusion_failed"]:,}개 ({stats["inclusion_failed"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **Exclusion 실패**: {stats["exclusion_failed"]:,}개 ({stats["exclusion_failed"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **둘 다 실패**: {stats["both_failed"]:,}개 ({stats["both_failed"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **API 실패**: {stats["api_failed"]:,}개 ({stats["api_failed"]/stats["total"]*100:.2f}%)\n')
            f.write('\n')
            
            f.write('### 1.2 Validation 요약\n\n')
            if val_stat and val_stat['total_validated']:
                total_val = val_stat['total_validated']
                f.write(f'- **검증 완료 항목**: {total_val:,}개\n')
                f.write(f'- **VERIFIED**: {val_stat["verified"]:,}개 ({val_stat["verified"]/total_val*100:.2f}%)\n')
                f.write(f'- **UNCERTAIN**: {val_stat["uncertain"]:,}개 ({val_stat["uncertain"]/total_val*100:.2f}%)\n')
                f.write(f'- **INCLUSION_FAILED**: {val_stat["inclusion_failed"]:,}개 ({val_stat["inclusion_failed"]/total_val*100:.2f}%)\n')
                f.write(f'- **EXCLUSION_FAILED**: {val_stat["exclusion_failed"]:,}개 ({val_stat["exclusion_failed"]/total_val*100:.2f}%)\n')
                f.write(f'- **BOTH_FAILED**: {val_stat["both_failed"]:,}개 ({val_stat["both_failed"]/total_val*100:.2f}%)\n')
                f.write(f'\n')
                f.write(f'- **수동 검토 필요**: {val_stat["needs_manual_review"]:,}개 ({val_stat["needs_manual_review"]/total_val*100:.2f}%)\n')
                if val_stat['avg_consistency']:
                    f.write(f'- **평균 일관성 점수**: {float(val_stat["avg_consistency"]):.2f}\n')
            else:
                f.write('- **검증 완료 항목**: 0개 (아직 검증이 수행되지 않았습니다)\n')
            f.write('\n')
            
            # 2. 전처리 상세 통계
            f.write('## 2. 전처리 상세 통계\n\n')
            
            f.write('### 2.1 추출 통계\n\n')
            if stats['total'] > 0:
                f.write(f'- **Inclusion Criteria 추출**: {stats["with_inclusion"]:,}개 ({stats["with_inclusion"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **Exclusion Criteria 추출**: {stats["with_exclusion"]:,}개 ({stats["with_exclusion"]/stats["total"]*100:.2f}%)\n')
                f.write(f'- **완전 파싱 (둘 다)**: {stats["complete"]:,}개 ({stats["complete"]/stats["total"]*100:.2f}%)\n')
            f.write('\n')
            
            f.write('### 2.2 Criteria 개수 통계\n\n')
            criteria_stats = prep_stats['criteria_stats']
            if criteria_stats and criteria_stats['avg_inclusion_count']:
                f.write(f'- **평균 Inclusion Criteria 개수**: {float(criteria_stats["avg_inclusion_count"]):.1f}개\n')
                f.write(f'- **평균 Exclusion Criteria 개수**: {float(criteria_stats["avg_exclusion_count"]):.1f}개\n')
                f.write(f'- **최대 Inclusion Criteria 개수**: {criteria_stats["max_inclusion_count"]}개\n')
                f.write(f'- **최대 Exclusion Criteria 개수**: {criteria_stats["max_exclusion_count"]}개\n')
                f.write(f'- **최소 Inclusion Criteria 개수**: {criteria_stats["min_inclusion_count"]}개\n')
                f.write(f'- **최소 Exclusion Criteria 개수**: {criteria_stats["min_exclusion_count"]}개\n')
            f.write('\n')
            
            f.write('### 2.3 Confidence 통계\n\n')
            conf_stats = prep_stats['confidence_stats']
            if conf_stats and conf_stats['avg_confidence']:
                f.write(f'- **평균 Confidence**: {float(conf_stats["avg_confidence"]):.2f}\n')
                f.write(f'- **최소 Confidence**: {float(conf_stats["min_confidence"]):.2f}\n')
                f.write(f'- **최대 Confidence**: {float(conf_stats["max_confidence"]):.2f}\n')
                f.write(f'- **높은 Confidence (≥0.9)**: {conf_stats["high_confidence"]:,}개\n')
                f.write(f'- **중간 Confidence (0.7~0.9)**: {conf_stats["medium_confidence"]:,}개\n')
                f.write(f'- **낮은 Confidence (<0.7)**: {conf_stats["low_confidence"]:,}개\n')
            f.write('\n')
            
            # 3. Validation 상세 통계
            f.write('## 3. Validation 상세 통계\n\n')
            
            if val_stat and val_stat['total_validated']:
                f.write('### 3.1 검증 상태 분포\n\n')
                total_val = val_stat['total_validated']
                f.write(f'- **VERIFIED**: {val_stat["verified"]:,}개 ({val_stat["verified"]/total_val*100:.2f}%)\n')
                f.write(f'- **UNCERTAIN**: {val_stat["uncertain"]:,}개 ({val_stat["uncertain"]/total_val*100:.2f}%)\n')
                f.write(f'- **INCLUSION_FAILED**: {val_stat["inclusion_failed"]:,}개 ({val_stat["inclusion_failed"]/total_val*100:.2f}%)\n')
                f.write(f'- **EXCLUSION_FAILED**: {val_stat["exclusion_failed"]:,}개 ({val_stat["exclusion_failed"]/total_val*100:.2f}%)\n')
                f.write(f'- **BOTH_FAILED**: {val_stat["both_failed"]:,}개 ({val_stat["both_failed"]/total_val*100:.2f}%)\n')
                f.write('\n')
                
                f.write('### 3.2 검증 신뢰도 통계\n\n')
                if val_stat['avg_verified_confidence']:
                    f.write(f'- **VERIFIED 평균 신뢰도**: {float(val_stat["avg_verified_confidence"]):.2f}\n')
                if val_stat['avg_confidence']:
                    f.write(f'- **전체 평균 신뢰도**: {float(val_stat["avg_confidence"]):.2f}\n')
                f.write('\n')
                
                f.write('### 3.3 일관성 점수 통계\n\n')
                if val_stat['avg_consistency']:
                    f.write(f'- **평균 일관성 점수**: {float(val_stat["avg_consistency"]):.2f}\n')
                    f.write(f'- **최소 일관성 점수**: {float(val_stat["min_consistency"]):.2f}\n')
                    f.write(f'- **최대 일관성 점수**: {float(val_stat["max_consistency"]):.2f}\n')
                
                consistency_dist = val_stats['consistency_dist']
                if consistency_dist:
                    total_consistency = (
                        (consistency_dist['high_consistency'] or 0) +
                        (consistency_dist['medium_consistency'] or 0) +
                        (consistency_dist['low_consistency'] or 0)
                    )
                    if total_consistency > 0:
                        f.write(f'\n- **높은 일관성 (≥0.67)**: {consistency_dist["high_consistency"]:,}개 ({consistency_dist["high_consistency"]/total_consistency*100:.2f}%)\n')
                        f.write(f'- **중간 일관성 (0.33~0.67)**: {consistency_dist["medium_consistency"]:,}개 ({consistency_dist["medium_consistency"]/total_consistency*100:.2f}%)\n')
                        f.write(f'- **낮은 일관성 (<0.33)**: {consistency_dist["low_consistency"]:,}개 ({consistency_dist["low_consistency"]/total_consistency*100:.2f}%)\n')
                f.write('\n')
                
                f.write('### 3.4 수동 검토 현황\n\n')
                f.write(f'- **수동 검토 필요 항목**: {val_stat["needs_manual_review"]:,}개 ({val_stat["needs_manual_review"]/total_val*100:.2f}%)\n')
                f.write(f'- **수동 검토 불필요 항목**: {val_stat["no_manual_review"]:,}개 ({val_stat["no_manual_review"]/total_val*100:.2f}%)\n')
                f.write('\n')
                
                # 수동 검토 불필요 vs 필요 비교
                f.write('### 3.5 수동 검토 불필요 vs 필요 항목 비교\n\n')
                no_review = val_stats['no_review_stats']
                manual_review = val_stats['manual_review_stats']
                
                if no_review and no_review['total'] and manual_review and manual_review['total']:
                    # 수동 검토 불필요 항목 중 VERIFIED만 "바로 사용 가능"
                    no_review_verified = no_review['verified'] or 0
                    no_review_failed = (no_review['inclusion_failed'] or 0) + (no_review['exclusion_failed'] or 0) + (no_review['both_failed'] or 0)
                    
                    f.write('#### 3.5.1 수동 검토 불필요 항목\n\n')
                    f.write(f'- **전체**: {no_review["total"]:,}개\n')
                    f.write(f'- **바로 사용 가능 (VERIFIED)**: {no_review_verified:,}개 ({no_review_verified/no_review["total"]*100:.2f}%)\n')
                    f.write(f'- **UNCERTAIN**: {no_review["uncertain"]:,}개 ({no_review["uncertain"]/no_review["total"]*100:.2f}%)\n')
                    f.write(f'- **실패 항목 (사용 불가)**: {no_review_failed:,}개 ({no_review_failed/no_review["total"]*100:.2f}%)\n')
                    f.write(f'  - INCLUSION_FAILED: {no_review["inclusion_failed"]:,}개\n')
                    f.write(f'  - EXCLUSION_FAILED: {no_review["exclusion_failed"]:,}개\n')
                    f.write(f'  - BOTH_FAILED: {no_review["both_failed"]:,}개\n')
                    if no_review['avg_confidence']:
                        f.write(f'- **평균 신뢰도**: {float(no_review["avg_confidence"]):.2f}\n')
                    if no_review['avg_consistency']:
                        f.write(f'- **평균 일관성 점수**: {float(no_review["avg_consistency"]):.2f}\n')
                    f.write('\n')
                    
                    f.write('#### 3.5.2 수동 검토 필요 항목\n\n')
                    f.write(f'- **전체**: {manual_review["total"]:,}개\n')
                    f.write(f'- **VERIFIED**: {manual_review["verified"]:,}개 ({manual_review["verified"]/manual_review["total"]*100:.2f}%)\n')
                    f.write(f'- **UNCERTAIN**: {manual_review["uncertain"]:,}개 ({manual_review["uncertain"]/manual_review["total"]*100:.2f}%)\n')
                    f.write(f'- **INCLUSION_FAILED**: {manual_review["inclusion_failed"]:,}개 ({manual_review["inclusion_failed"]/manual_review["total"]*100:.2f}%)\n')
                    f.write(f'- **EXCLUSION_FAILED**: {manual_review["exclusion_failed"]:,}개 ({manual_review["exclusion_failed"]/manual_review["total"]*100:.2f}%)\n')
                    f.write(f'- **BOTH_FAILED**: {manual_review["both_failed"]:,}개 ({manual_review["both_failed"]/manual_review["total"]*100:.2f}%)\n')
                    if manual_review['avg_confidence']:
                        f.write(f'- **평균 신뢰도**: {float(manual_review["avg_confidence"]):.2f}\n')
                    if manual_review['avg_consistency']:
                        f.write(f'- **평균 일관성 점수**: {float(manual_review["avg_consistency"]):.2f}\n')
                    f.write('\n')
                    
                    f.write('#### 3.5.3 비교 요약\n\n')
                    manual_review_failed = (manual_review["inclusion_failed"] or 0) + (manual_review["exclusion_failed"] or 0) + (manual_review["both_failed"] or 0)
                    f.write('| 항목 | 수동 검토 불필요 | 수동 검토 필요 | 차이 |\n')
                    f.write('| ---- | ---------------- | ------------- | ---- |\n')
                    f.write(f'| **전체** | {no_review["total"]:,}개 ({no_review["total"]/total_val*100:.2f}%) | {manual_review["total"]:,}개 ({manual_review["total"]/total_val*100:.2f}%) | - |\n')
                    f.write(f'| **바로 사용 가능 (VERIFIED)** | {no_review["verified"]:,}개 ({no_review["verified"]/no_review["total"]*100:.2f}%) | {manual_review["verified"]:,}개 ({manual_review["verified"]/manual_review["total"]*100:.2f}%) | {no_review["verified"]/no_review["total"]*100 - manual_review["verified"]/manual_review["total"]*100:+.2f}%p |\n')
                    f.write(f'| **실패 항목 (사용 불가)** | {no_review_failed:,}개 ({no_review_failed/no_review["total"]*100:.2f}%) | {manual_review_failed:,}개 ({manual_review_failed/manual_review["total"]*100:.2f}%) | - |\n')
                    if no_review['avg_confidence'] and manual_review['avg_confidence']:
                        f.write(f'| **평균 신뢰도** | {float(no_review["avg_confidence"]):.2f} | {float(manual_review["avg_confidence"]):.2f} | {float(no_review["avg_confidence"]) - float(manual_review["avg_confidence"]):+.2f} |\n')
                    if no_review['avg_consistency'] and manual_review['avg_consistency']:
                        f.write(f'| **평균 일관성** | {float(no_review["avg_consistency"]):.2f} | {float(manual_review["avg_consistency"]):.2f} | {float(no_review["avg_consistency"]) - float(manual_review["avg_consistency"]):+.2f} |\n')
                    f.write('\n')
                f.write('\n')
                
                f.write('### 3.6 검증 이력 통계\n\n')
                history_stats = val_stats['history_stats']
                if history_stats:
                    f.write(f'- **검증된 Study 수**: {history_stats["total_studies_validated"]:,}개\n')
                    f.write(f'- **총 검증 실행 횟수**: {history_stats["total_validation_runs"]:,}회\n')
                    if history_stats['avg_validation_confidence']:
                        f.write(f'- **평균 검증 신뢰도**: {float(history_stats["avg_validation_confidence"]):.2f}\n')
                    f.write(f'- **검증 노트 있는 항목**: {history_stats["with_notes"]:,}개\n')
                f.write('\n')
            else:
                f.write('아직 검증이 수행되지 않았습니다.\n\n')
            
            # 4. Feature 분포
            f.write('## 4. 주요 Feature 분포 (상위 20개)\n\n')
            f.write('| 순위 | Feature | 사용 횟수 |\n')
            f.write('| ---- | ------- | --------- |\n')
            for idx, feature in enumerate(features, 1):
                f.write(f"| {idx} | {feature['feature']} | {feature['usage_count']:,} |\n")
            f.write('\n')
            
            # 5. 샘플 결과
            f.write('## 5. 전처리 결과 예시\n\n')
            for idx, sample in enumerate(success_samples, 1):
                f.write(f'### 5.{idx} 성공 샘플 #{idx}\n\n')
                f.write(f'**NCT ID**: `{sample["nct_id"]}`\n\n')
                
                if sample['eligibility_criteria_raw']:
                    f.write('**원본 Eligibility Criteria** (일부):\n\n')
                    raw_text = sample['eligibility_criteria_raw']
                    if len(raw_text) > 500:
                        raw_text = raw_text[:500] + '...'
                    f.write(f'```\n{raw_text}\n```\n\n')
                
                if sample['inclusion_criteria']:
                    inclusion = json.loads(sample['inclusion_criteria']) if isinstance(sample['inclusion_criteria'], str) else sample['inclusion_criteria']
                    f.write(f'**Inclusion Criteria 개수**: {len(inclusion) if isinstance(inclusion, list) else "N/A"}개\n')
                
                if sample['exclusion_criteria']:
                    exclusion = json.loads(sample['exclusion_criteria']) if isinstance(sample['exclusion_criteria'], str) else sample['exclusion_criteria']
                    f.write(f'**Exclusion Criteria 개수**: {len(exclusion) if isinstance(exclusion, list) else "N/A"}개\n')
                
                if sample['llm_confidence']:
                    f.write(f'**LLM Confidence**: {float(sample["llm_confidence"]):.2f}\n')
                
                if sample['llm_validation_status']:
                    f.write(f'**Validation Status**: {sample["llm_validation_status"]}\n')
                    if sample['llm_validation_confidence']:
                        f.write(f'**Validation Confidence**: {float(sample["llm_validation_confidence"]):.2f}\n')
                    if sample['validation_consistency_score']:
                        f.write(f'**Consistency Score**: {float(sample["validation_consistency_score"]):.2f}\n')
                    if sample['needs_manual_review']:
                        f.write(f'**수동 검토 필요**: 예\n')
                
                f.write('\n')
                
                if sample['inclusion_criteria']:
                    f.write('**Inclusion Criteria 예시** (처음 5개):\n\n')
                    f.write(format_criteria_list(sample['inclusion_criteria'], 5))
                    f.write('\n\n')
                
                f.write('---\n\n')
            
            # 6. 결론
            f.write('## 6. 결론\n\n')
            f.write('### 6.1 전처리 성과\n\n')
            if stats['total'] > 0:
                success_rate = stats['success'] / stats['total'] * 100
                f.write(f'- 전처리 성공률: **{success_rate:.2f}%** ({stats["success"]:,}/{stats["total"]:,})\n')
                f.write(f'- Inclusion/Exclusion 모두 추출 성공률: **{stats["complete"]/stats["total"]*100:.2f}%**\n')
            f.write('\n')
            
            f.write('### 6.2 Validation 성과\n\n')
            if val_stat and val_stat['total_validated']:
                verified_rate = val_stat['verified'] / val_stat['total_validated'] * 100
                f.write(f'- 검증 완료율: **{val_stat["total_validated"]:,}개** 항목 검증 완료\n')
                f.write(f'- VERIFIED 비율: **{verified_rate:.2f}%** ({val_stat["verified"]:,}/{val_stat["total_validated"]:,})\n')
                f.write(f'- 수동 검토 필요 비율: **{val_stat["needs_manual_review"]/val_stat["total_validated"]*100:.2f}%**\n')
            f.write('\n')
            
            f.write('---\n\n')
            f.write(f'*보고서 생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*\n')
        
        print(f"[OK] 보고서 생성 완료: {report_path}")
        return report_path
        
    finally:
        conn.close()


def main():
    """메인 함수"""
    import sys
    
    output_dir = None
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    print("=" * 80)
    print("[START] Inclusion/Exclusion 종합 보고서 생성")
    print("=" * 80)
    
    report_path = generate_report(output_dir)
    
    print(f"\n[OK] 보고서 생성 완료!")
    print(f"경로: {report_path}")


if __name__ == "__main__":
    main()

