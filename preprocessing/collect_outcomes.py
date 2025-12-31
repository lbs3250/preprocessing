"""
ClinicalTrials.gov API를 통한 Outcomes 데이터 수집 스크립트

사용법:
    python collect_outcomes.py

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
    # 또는 가장 높은 phase만 사용할 수도 있음
    # 여기서는 모든 phase를 쉼표로 구분하여 저장
    phase_str = ','.join(phases)
    return phase_str if phase_str else 'NA'


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


def extract_outcomes(study: Dict) -> List[Dict]:
    """
    Study JSON에서 outcomes 추출
    
    Returns:
        outcomes 리스트 (각 outcome은 딕셔너리)
    """
    outcomes = []
    nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
    
    if not nct_id:
        return outcomes
    
    # source_version 추출 (derivedSection.miscInfoModule.versionHolder)
    source_version = study.get('derivedSection', {}).get('miscInfoModule', {}).get('versionHolder')
    
    # phase 정보 추출 (study 레벨이므로 모든 outcome에 동일하게 적용)
    phase = extract_phase(study)
    
    # intervention 정보 추출 (study 레벨이므로 모든 outcome에 동일하게 적용)
    arms_interventions_module = study.get('protocolSection', {}).get('armsInterventionsModule', {})
    interventions_list = arms_interventions_module.get('interventions', [])
    intervention_json = json.dumps(interventions_list) if interventions_list else None
    
    outcomes_module = study.get('protocolSection', {}).get('outcomesModule', {})
    
    # Primary Outcomes 추출
    primary_outcomes = outcomes_module.get('primaryOutcomes', [])
    for idx, outcome in enumerate(primary_outcomes):
        outcomes.append({
            'nct_id': nct_id,
            'outcome_type': 'PRIMARY',
            'outcome_order': idx,
            'measure_raw': outcome.get('measure'),
            'description_raw': outcome.get('description'),
            'time_frame_raw': outcome.get('timeFrame'),
            'phase': phase,
            'source_version': source_version,
            'raw_json': json.dumps(outcome),  # 원본 outcome JSON 보존
            'intervention_json': intervention_json  # 해당 study의 intervention 정보 (원본 JSON 배열)
        })
    
    # Secondary Outcomes 추출
    secondary_outcomes = outcomes_module.get('secondaryOutcomes', [])
    for idx, outcome in enumerate(secondary_outcomes):
        outcomes.append({
            'nct_id': nct_id,
            'outcome_type': 'SECONDARY',
            'outcome_order': idx,
            'measure_raw': outcome.get('measure'),
            'description_raw': outcome.get('description'),
            'time_frame_raw': outcome.get('timeFrame'),
            'phase': phase,
            'source_version': source_version,
            'raw_json': json.dumps(outcome),
            'intervention_json': intervention_json  # 해당 study의 intervention 정보 (원본 JSON 배열)
        })
    
    return outcomes


def extract_party_info(study: Dict) -> List[Dict]:
    """
    Study JSON에서 기관/담당자/시설 정보 추출
    
    Returns:
        party 정보 리스트
    """
    parties = []
    nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
    
    if not nct_id:
        return parties
    
    protocol_section = study.get('protocolSection', {})
    
    # 1. Lead Sponsor
    sponsor_module = protocol_section.get('sponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('leadSponsor')
    if lead_sponsor:
        parties.append({
            'nct_id': nct_id,
            'party_type': 'LEAD_SPONSOR',
            'name_raw': lead_sponsor.get('name'),
            'affiliation_raw': None,
            'role_raw': None,
            'class_raw': lead_sponsor.get('class'),
            'location_raw': None,
            'source_path': 'protocolSection.sponsorCollaboratorsModule.leadSponsor'
        })
    
    # 2. Organization
    identification_module = protocol_section.get('identificationModule', {})
    organization = identification_module.get('organization')
    if organization:
        parties.append({
            'nct_id': nct_id,
            'party_type': 'ORGANIZATION',
            'name_raw': organization.get('fullName'),
            'affiliation_raw': None,
            'role_raw': None,
            'class_raw': organization.get('class'),
            'location_raw': None,
            'source_path': 'protocolSection.identificationModule.organization'
        })
    
    # 3. Overall Officials (Collaborators는 제외)
    contacts_module = protocol_section.get('contactsLocationsModule', {})
    officials = contacts_module.get('overallOfficials', [])
    for official in officials:
        parties.append({
            'nct_id': nct_id,
            'party_type': 'OFFICIAL',
            'name_raw': official.get('name'),
            'affiliation_raw': official.get('affiliation'),
            'role_raw': official.get('role'),
            'class_raw': None,
            'location_raw': None,
            'source_path': 'protocolSection.contactsLocationsModule.overallOfficials'
        })
    
    # 4. Facilities/Locations는 제외 (사용하지 않음)
    
    return parties


def insert_outcomes(conn, outcomes: List[Dict]):
    """outcome_raw 테이블에 outcomes 삽입"""
    if not outcomes:
        return
    
    insert_sql = """
        INSERT INTO outcome_raw 
        (nct_id, outcome_type, outcome_order, measure_raw, description_raw, 
         time_frame_raw, phase, raw_json, source_version, intervention_json)
        VALUES (%(nct_id)s, %(outcome_type)s, %(outcome_order)s, %(measure_raw)s, 
                %(description_raw)s, %(time_frame_raw)s, %(phase)s, %(raw_json)s::jsonb, 
                %(source_version)s,
                CASE WHEN %(intervention_json)s IS NOT NULL THEN %(intervention_json)s::jsonb ELSE NULL END)
        ON CONFLICT (nct_id, outcome_type, outcome_order) 
        DO UPDATE SET
            measure_raw = EXCLUDED.measure_raw,
            description_raw = EXCLUDED.description_raw,
            time_frame_raw = EXCLUDED.time_frame_raw,
            phase = EXCLUDED.phase,
            raw_json = EXCLUDED.raw_json,
            source_version = EXCLUDED.source_version,
            intervention_json = EXCLUDED.intervention_json,
            ingested_at = CURRENT_TIMESTAMP
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, outcomes)
    conn.commit()


def insert_party_info(conn, parties: List[Dict]):
    """study_party_raw 테이블에 party 정보 삽입"""
    if not parties:
        return
    
    # 중복 방지: 같은 nct_id + party_type + name_raw 조합은 업데이트
    insert_sql = """
        INSERT INTO study_party_raw 
        (nct_id, party_type, name_raw, affiliation_raw, role_raw, 
         class_raw, location_raw, source_path)
        VALUES (%(nct_id)s, %(party_type)s, %(name_raw)s, %(affiliation_raw)s, 
                %(role_raw)s, %(class_raw)s, 
                CASE WHEN %(location_raw)s IS NOT NULL AND %(location_raw)s != '' 
                     THEN %(location_raw)s::jsonb 
                     ELSE NULL END,
                %(source_path)s)
        ON CONFLICT (nct_id, party_type, name_raw) 
        DO UPDATE SET
            affiliation_raw = EXCLUDED.affiliation_raw,
            role_raw = EXCLUDED.role_raw,
            class_raw = EXCLUDED.class_raw,
            location_raw = EXCLUDED.location_raw,
            source_path = EXCLUDED.source_path,
            ingested_at = CURRENT_TIMESTAMP
    """
    
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, parties)
    conn.commit()


def save_studies_to_json(studies: List[Dict], output_file: str = "raw.json", append: bool = True):
    """
    Study 전체 원본 JSON을 하나의 파일로 저장
    
    Args:
        studies: Study 딕셔너리 리스트
        output_file: 저장할 파일명 (기본값: "raw.json")
        append: 기존 파일에 추가할지 여부 (True면 배열에 추가, False면 새로 생성)
    
    Returns:
        저장된 study 개수
    """
    if not studies:
        return 0
    
    output_path = Path(output_file)
    
    # 기존 데이터 로드 (append 모드인 경우)
    existing_studies = []
    if append and output_path.exists():
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    existing_studies = existing_data
                elif isinstance(existing_data, dict) and 'studies' in existing_data:
                    existing_studies = existing_data['studies']
        except (json.JSONDecodeError, FileNotFoundError):
            existing_studies = []
    
    # 기존 study의 nct_id 집합 (중복 체크용)
    existing_nct_ids = set()
    for study in existing_studies:
        nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
        if nct_id:
            existing_nct_ids.add(nct_id)
    
    # 새 study 추가 (중복 제외)
    new_studies = []
    for study in studies:
        nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
        if not nct_id:
            continue
        if nct_id not in existing_nct_ids:
            new_studies.append(study)
            existing_nct_ids.add(nct_id)
    
    # 기존 + 새로운 study 합치기
    all_studies = existing_studies + new_studies
    
    # 하나의 JSON 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_studies, f, indent=2, ensure_ascii=False)
    
    return len(new_studies)


def collect_all_studies(query_params: Dict):
    """
    모든 studies를 수집하여 DB에 저장
    
    Args:
        query_params: API 쿼리 파라미터 (예: {'query.cond': "Alzheimer's Disease"})
    """
    conn = get_db_connection()
    
    total_collected = 0
    total_filtered = 0  # drug가 아닌 intervention을 가진 study 개수
    total_outcomes = 0
    total_parties = 0
    page_token = None
    page_num = 0
    
    try:
        print("=" * 60)
        print("ClinicalTrials.gov Data Collection Started")
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
            
            # 각 study 처리
            # API 필터는 drug가 포함된 study를 가져오지만, drug만 단독으로 있는 것만 수집
            all_outcomes = []
            all_parties = []
            all_studies = []  # 전체 study JSON 저장용
            filtered_count = 0
            
            for study in studies:
                # Drug만 단독으로 있는 study만 수집
                # interventionType에 drug 외 다른 것이 있으면 수집하지 않음
                if not is_drug_only_study(study):
                    filtered_count += 1
                    # 디버깅: 필터링된 study의 intervention 정보 출력 (선택적)
                    # nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
                    # interventions = study.get('protocolSection', {}).get('armsInterventionsModule', {}).get('interventions', [])
                    # if interventions:
                    #     intervention_types = [i.get('type', '') for i in interventions]
                    #     print(f"    [FILTERED] {nct_id}: {intervention_types}")
                    continue
                
                # Study 전체 원본 JSON 저장
                all_studies.append(study)
                
                # Outcomes 추출 (intervention 정보 포함)
                outcomes = extract_outcomes(study)
                all_outcomes.extend(outcomes)
                
                # Party 정보 추출
                parties = extract_party_info(study)
                all_parties.extend(parties)
            
            # DB에 삽입
            if all_outcomes:
                insert_outcomes(conn, all_outcomes)
                total_outcomes += len(all_outcomes)
                print(f"  [OK] Inserted {len(all_outcomes)} outcomes")
            
            if all_parties:
                insert_party_info(conn, all_parties)
                total_parties += len(all_parties)
                print(f"  [OK] Inserted {len(all_parties)} party records")
            
            if all_studies:
                saved_count = save_studies_to_json(all_studies)
                print(f"  [OK] Saved {saved_count} study JSON files")
            
            if filtered_count > 0:
                print(f"  [FILTERED] Skipped {filtered_count} studies (has non-drug interventions like biomarker)")
            
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
        print(f"Total Outcomes: {total_outcomes:,}")
        print(f"Total Party Records: {total_parties:,}")
        print(f"Total Study JSON Files Saved: {total_collected:,}")
        if total_count:
            print(f"Expected (from API): {total_count:,} studies")
            if total_collected + total_filtered > 0:
                print(f"Filter Rate: {total_filtered/(total_collected + total_filtered)*100:.1f}%")
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
    
    collect_all_studies(query_params)


if __name__ == "__main__":
    main()

