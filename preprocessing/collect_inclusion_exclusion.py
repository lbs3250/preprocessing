"""
ClinicalTrials.gov API를 통한 Inclusion/Exclusion Criteria 데이터 수집 스크립트

사용법:
    python collect_inclusion_exclusion.py

환경변수 (.env 파일):
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=clinicaltrials
    DB_USER=postgres
    DB_PASSWORD=your_password
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_batch


# API 설정
API_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 500  # API 최대값 (1000까지 가능하지만 안정성을 위해 500)
REQUEST_DELAY = 0.5  # API 호출 간 딜레이 (초) - Rate limiting 방지

# DB 연결 설정
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'clinicaltrials'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'tests1234')
}


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def fetch_studies_page(query_params: Dict, page_token: Optional[str] = None) -> Dict:
    """
    ClinicalTrials.gov API에서 studies 페이지 가져오기
    
    Args:
        query_params: API 쿼리 파라미터 딕셔너리
        page_token: 다음 페이지 토큰 (None이면 첫 페이지)
    
    Returns:
        API 응답 JSON 딕셔너리
    """
    params = query_params.copy()
    params['format'] = 'json'
    params['pageSize'] = PAGE_SIZE
    
    if page_token:
        params['pageToken'] = page_token
    
    try:
        response = requests.get(API_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 실패: {e}")
        raise


def extract_phase(study: Dict) -> str:
    """
    Study JSON에서 phase 정보 추출
    
    Returns:
        phase 문자열 (예: "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA" 등)
        phase 정보가 없으면 'NA' 반환
    """
    design_module = study.get('protocolSection', {}).get('designModule', {})
    phases = design_module.get('phases', [])
    
    if not phases:
        return 'NA'
    
    # phases는 배열이므로 여러 phase가 있을 수 있음
    # 예: ["PHASE1", "PHASE2"] -> "PHASE1,PHASE2"로 결합
    phase_str = ','.join(phases)
    return phase_str if phase_str else 'NA'


def extract_eligibility_criteria(study: Dict) -> Optional[str]:
    """
    Study JSON에서 eligibilityCriteria 추출
    
    Returns:
        eligibilityCriteria 텍스트 (없으면 None)
    """
    eligibility_module = study.get('protocolSection', {}).get('eligibilityModule', {})
    return eligibility_module.get('eligibilityCriteria')


def is_drug_only_study(study: Dict) -> bool:
    """
    Study의 intervention이 drug만 있는지 확인
    (drug 외 다른 interventionType이 있으면 False)
    
    Returns:
        intervention이 모두 drug이거나 없는 경우 True
        drug 외 다른 interventionType이 있으면 False
    """
    arms_interventions_module = study.get('protocolSection', {}).get('armsInterventionsModule', {})
    interventions = arms_interventions_module.get('interventions', [])
    
    # intervention이 없으면 True (수집 가능)
    if not interventions:
        return True
    
    # 모든 intervention의 type이 "DRUG"인지 확인
    # 하나라도 drug가 아니면 False
    for intervention in interventions:
        intervention_type = intervention.get('type', '').upper()
        if intervention_type and intervention_type != 'DRUG':
            # drug가 아닌 interventionType이 있으면 수집하지 않음
            return False
    
    # 모든 intervention이 drug이거나 없는 경우만 True
    return True


def extract_eligibility_data(study: Dict) -> Optional[Dict]:
    """
    Study JSON에서 eligibilityCriteria 데이터 추출
    
    Returns:
        eligibility 데이터 딕셔너리 (eligibilityCriteria가 없어도 null로 수집)
    """
    nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
    
    if not nct_id:
        return None
    
    eligibility_criteria = extract_eligibility_criteria(study)
    
    # eligibilityCriteria가 없어도 수집 (null 처리)
    # eligibilityCriteria가 None이거나 빈 문자열이면 None으로 저장
    if eligibility_criteria and eligibility_criteria.strip():
        criteria_text = eligibility_criteria
    else:
        criteria_text = None
    
    # source_version 추출 (derivedSection.miscInfoModule.versionHolder)
    source_version = study.get('derivedSection', {}).get('miscInfoModule', {}).get('versionHolder')
    
    # phase 정보 추출
    phase = extract_phase(study)
    
    return {
        'nct_id': nct_id,
        'eligibility_criteria_raw': criteria_text,  # None일 수 있음
        'phase': phase,
        'source_version': source_version,
        'raw_json': json.dumps(study)  # 원본 study JSON 보존
    }


def insert_eligibility_criteria(conn, eligibility_list: List[Dict]):
    """inclusion_exclusion_raw 테이블에 eligibilityCriteria 삽입"""
    if not eligibility_list:
        return
    
    insert_sql = """
        INSERT INTO inclusion_exclusion_raw 
        (nct_id, eligibility_criteria_raw, phase, source_version, raw_json)
        VALUES (%(nct_id)s, %(eligibility_criteria_raw)s, %(phase)s, 
                %(source_version)s, %(raw_json)s::jsonb)
        ON CONFLICT (nct_id) 
        DO UPDATE SET
            eligibility_criteria_raw = EXCLUDED.eligibility_criteria_raw,
            phase = EXCLUDED.phase,
            source_version = EXCLUDED.source_version,
            raw_json = EXCLUDED.raw_json,
            ingested_at = CURRENT_TIMESTAMP
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, eligibility_list, page_size=100)
    conn.commit()


def collect_all_eligibility_criteria(query_params: Dict):
    """
    모든 studies의 eligibilityCriteria를 수집하여 DB에 저장
    
    Args:
        query_params: API 쿼리 파라미터 (예: {'query.cond': "Alzheimer's Disease"})
    """
    conn = get_db_connection()
    
    # 기존 데이터 삭제 (재수집)
    print("=" * 60)
    print("Clearing existing data...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM inclusion_exclusion_raw")
        deleted_count = cur.rowcount
        conn.commit()
    print(f"[OK] Deleted {deleted_count:,} existing records")
    print("=" * 60)
    
    total_collected = 0
    total_filtered = 0  # drug가 아닌 intervention을 가진 study 개수
    total_eligibility = 0
    page_token = None
    page_num = 0
    
    try:
        print("\n" + "=" * 60)
        print("ClinicalTrials.gov Inclusion/Exclusion Criteria Collection Started")
        print("=" * 60)
        
        total_count = None  # 첫 페이지에서 가져올 때까지 None
        
        while True:
            page_num += 1
            print(f"\n[Page {page_num}] Requesting...")
            
            # API 호출
            response_data = fetch_studies_page(query_params, page_token)
            
            studies = response_data.get('studies', [])
            api_total_count = response_data.get('totalCount', 0)
            next_page_token = response_data.get('nextPageToken')
            
            # 첫 페이지에서만 totalCount 저장
            if page_num == 1:
                if api_total_count > 0:
                    total_count = api_total_count
                    print(f"Total expected: {total_count:,} studies")
                else:
                    print("Total count not available from API")
            
            if not studies:
                print("No more data available.")
                break
            
            # 각 study에서 eligibilityCriteria 추출
            # API 필터는 drug가 포함된 study를 가져오지만, drug만 단독으로 있는 것만 수집
            all_eligibility = []
            filtered_count = 0
            
            for study in studies:
                # Drug만 단독으로 있는 study만 수집
                # interventionType에 drug 외 다른 것이 있으면 수집하지 않음
                if not is_drug_only_study(study):
                    filtered_count += 1
                    continue
                
                eligibility_data = extract_eligibility_data(study)
                if eligibility_data:
                    all_eligibility.append(eligibility_data)
            
            if filtered_count > 0:
                print(f"  [FILTERED] Skipped {filtered_count} studies (has non-drug interventions like biomarker)")
            
            # DB에 삽입 (배치 처리)
            if all_eligibility:
                insert_eligibility_criteria(conn, all_eligibility)
                total_eligibility += len(all_eligibility)
                print(f"  [OK] Inserted {len(all_eligibility)} eligibility criteria records")
            
            total_collected += len(studies) - filtered_count
            total_filtered += filtered_count
            
            # 진행률 표시
            if total_count:
                print(f"  Progress: {total_collected:,} / {total_count:,} studies ({total_collected/total_count*100:.1f}%)")
            else:
                print(f"  Progress: {total_collected:,} studies collected")
            
            # 다음 페이지가 없으면 종료
            if not next_page_token:
                print("\n모든 페이지 수집 완료!")
                break
            
            page_token = next_page_token
            
            # Rate limiting 방지
            time.sleep(REQUEST_DELAY)
        
        print("\n" + "=" * 60)
        print("Collection Summary")
        print("=" * 60)
        print(f"Total Studies Collected (drug only): {total_collected:,}")
        print(f"Total Studies Filtered (has non-drug): {total_filtered:,}")
        print(f"Total Eligibility Records Collected: {total_eligibility:,}")
        if total_count:
            print(f"Expected (from API): {total_count:,} studies")
            if total_collected + total_filtered > 0:
                print(f"Filter Rate: {total_filtered/(total_collected + total_filtered)*100:.1f}%")
            if total_collected > 0:
                print(f"Collection Rate: {total_eligibility/total_collected*100:.1f}%")
        
        # eligibilityCriteria가 있는 항목과 없는 항목 통계
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(eligibility_criteria_raw) as with_criteria,
                    COUNT(*) FILTER (WHERE eligibility_criteria_raw IS NULL) as without_criteria
                FROM inclusion_exclusion_raw
            """)
            stats = cur.fetchone()
            if stats and stats['total'] > 0:
                print(f"\n[Eligibility Criteria 통계]")
                print(f"  전체: {stats['total']:,}개")
                print(f"  Criteria 있음: {stats['with_criteria']:,}개 ({stats['with_criteria']/stats['total']*100:.1f}%)")
                print(f"  Criteria 없음 (NULL): {stats['without_criteria']:,}개 ({stats['without_criteria']/stats['total']*100:.1f}%)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """메인 함수"""
    # 쿼리 파라미터 설정
    # 예시: Alzheimer's Disease 관련 trials
    # Intervention 필터: drug만 있는 study만 수집 (API 레벨 필터)
    query_params = {
        'query.cond': "Alzheimer's Disease",
        'filter.advanced': 'AREA[InterventionType]Drug'
    }
    
    # 다른 조건으로 변경 가능:
    # query_params = {
    #     'query.cond': 'Dementia',
    #     'filter.advanced': 'AREA[InterventionType]Drug'
    # }
    # query_params = {'filter.advanced': 'AREA[InterventionType]Drug'}  # 전체 데이터 중 drug만
    
    print("Query parameters:", query_params)
    print("Filter: Only studies with DRUG-only interventions will be collected")
    print("  - API filter: AREA[InterventionType]Drug (drug 포함된 study)")
    print("  - Additional filter: drug만 단독으로 있는 study만 수집 (biomarker 등 제외)")
    print("\nStarting collection...")
    
    collect_all_eligibility_criteria(query_params)


if __name__ == "__main__":
    main()

