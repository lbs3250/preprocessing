"""
프롬프트와 LLM 응답 예시 저장 스크립트

실제 LLM 전처리 과정에서 사용되는 프롬프트와 응답을 1건만 캡처하여 MD 파일로 저장합니다.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from llm_config import get_api_keys, GEMINI_MODEL
from llm_prompts import get_preprocess_initial_prompt
from google import genai

load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_example_outcome():
    """예시 outcome 데이터 생성"""
    return {
        'id': 1,
        'measure_raw': 'Alzheimer\'s Disease Assessment Scale-Cognitive Subscale (ADAS-Cog)',
        'description_raw': 'Change from baseline in ADAS-Cog score',
        'time_frame_raw': 'Baseline, Week 12, Week 24, Week 36'
    }


def save_prompt_response_example():
    """프롬프트와 응답 예시를 MD 파일로 저장"""
    # 예시 데이터 준비
    outcome = get_example_outcome()
    
    # 프롬프트 생성
    items = []
    oid = outcome.get('id')
    mr = outcome.get('measure_raw', '') or ''
    dr = outcome.get('description_raw', '') or ''
    tr = outcome.get('time_frame_raw', '') or ''
    parts = [f"{oid}"]
    if mr: parts.append(f"M:{mr}")
    if dr: parts.append(f"D:{dr}")
    if tr: parts.append(f"T:{tr}")
    item_str = "|".join(parts)
    
    items_text = item_str
    prompt = get_preprocess_initial_prompt(items_text)
    
    # API 호출
    api_keys = get_api_keys()
    if not api_keys:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다!")
        return
    
    print("[INFO] LLM API 호출 중...")
    client = genai.Client(api_key=api_keys[0])
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    
    response_text = response.text.strip()
    
    # MD 파일로 저장
    output_dir = os.path.join(ROOT_DIR, 'docs')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f'llm_prompt_response_example_{timestamp}.md')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# LLM 전처리 프롬프트 및 응답 예시\n\n')
        f.write(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        
        f.write('## 1. 입력 데이터\n\n')
        f.write('```json\n')
        f.write(json.dumps(outcome, indent=2, ensure_ascii=False))
        f.write('\n```\n\n')
        
        f.write('## 2. 프롬프트\n\n')
        f.write('```\n')
        f.write(prompt)
        f.write('\n```\n\n')
        
        f.write('## 3. LLM 응답\n\n')
        f.write('```json\n')
        f.write(response_text)
        f.write('\n```\n\n')
        
        # JSON 파싱 시도
        try:
            # 코드 블록 제거
            cleaned_response = response_text
            if '```' in cleaned_response:
                import re
                code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
                match = re.search(code_block_pattern, cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            
            # JSON 배열 시작 부분 찾기
            json_start = cleaned_response.find('[')
            if json_start >= 0:
                cleaned_response = cleaned_response[json_start:]
            
            parsed_response = json.loads(cleaned_response)
            
            f.write('## 4. 파싱된 응답\n\n')
            f.write('```json\n')
            f.write(json.dumps(parsed_response, indent=2, ensure_ascii=False))
            f.write('\n```\n\n')
            
            # 결과 분석
            if isinstance(parsed_response, list) and len(parsed_response) > 0:
                result = parsed_response[0]
                f.write('## 5. 추출된 정보\n\n')
                f.write('| 항목 | 값 |\n')
                f.write('|------|-----|\n')
                f.write(f"| outcome_id | {result.get('outcome_id', 'N/A')} |\n")
                f.write(f"| measure_code | {result.get('measure_code', 'N/A')} |\n")
                f.write(f"| time_value | {result.get('time_value', 'N/A')} |\n")
                f.write(f"| time_unit | {result.get('time_unit', 'N/A')} |\n")
                f.write(f"| time_points | {json.dumps(result.get('time_points', []), ensure_ascii=False)} |\n")
                f.write(f"| confidence | {result.get('confidence', 'N/A')} |\n")
                f.write(f"| notes | {result.get('notes', 'N/A')} |\n")
        except json.JSONDecodeError as e:
            f.write('## 4. 파싱 오류\n\n')
            f.write(f'JSON 파싱 실패: {str(e)}\n\n')
            f.write('원본 응답을 확인해주세요.\n')
    
    print(f"[OK] 예시 파일 저장: {output_path}")
    return output_path


def main():
    """메인 함수"""
    print("=" * 80)
    print("[START] 프롬프트 및 응답 예시 저장")
    print("=" * 80)
    
    try:
        output_path = save_prompt_response_example()
        
        print("\n" + "=" * 80)
        print("[OK] 완료!")
        print("=" * 80)
        print(f"\n생성된 파일: {output_path}")
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()



