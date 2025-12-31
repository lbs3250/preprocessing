"""
Gemini API 클라이언트
"""
import os
from dotenv import load_dotenv
from google import genai

# 환경 변수 로드
load_dotenv()

# 여러 API 키 관리
_api_keys = None
_current_key_index = 0
_previous_key_index = -1  # 이전 키 인덱스 추적 (규칙 캐싱용)
_client = None
_all_keys_exhausted = False  # 모든 키가 소진되었는지 플래그


def get_api_keys():
    """
    .env 파일에서 모든 API 키를 로드합니다.
    GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 등 모두 로드합니다.
    
    Returns:
        API 키 리스트
    """
    global _api_keys
    
    if _api_keys is not None:
        return _api_keys
    
    api_keys = []
    
    # 첫 번째 키 (GEMINI_API_KEY)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        api_keys.append(api_key)
    
    # 추가 키들 (GEMINI_API_KEY_2, GEMINI_API_KEY_3, ...)
    index = 2
    while True:
        key = os.getenv(f"GEMINI_API_KEY_{index}")
        if key:
            api_keys.append(key)
            index += 1
        else:
            break
    
    _api_keys = api_keys
    return api_keys


def get_client(api_key: str = None):
    """
    Gemini API 클라이언트를 가져옵니다. 필요할 때 초기화됩니다.
    
    Args:
        api_key: 사용할 API 키 (None이면 현재 인덱스의 키 사용)
    
    Returns:
        genai.Client 인스턴스
    """
    global _client, _current_key_index
    
    if api_key is None:
        api_keys = get_api_keys()
        if not api_keys:
            raise ValueError("API 키가 설정되지 않았습니다. GEMINI_API_KEY 환경변수를 설정하세요.")
        api_key = api_keys[_current_key_index]
    
    # 새로운 API 키로 클라이언트 생성 또는 재생성
    _client = genai.Client(api_key=api_key)
    return _client


def switch_to_next_api_key():
    """
    다음 API 키로 전환합니다.
    
    Returns:
        전환 성공 여부 (True: 성공, False: 더 이상 키가 없음)
    """
    global _current_key_index, _client
    
    api_keys = get_api_keys()
    _current_key_index += 1
    
    if _current_key_index >= len(api_keys):
        _current_key_index = len(api_keys) - 1  # 마지막 키 유지
        return False
    
    # 새로운 키로 클라이언트 재생성
    _client = genai.Client(api_key=api_keys[_current_key_index])
    return True


# 모델 설정
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

# API 호출 제한 설정
MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '15'))
# 배치 크기: RPD 제한(20회/일)을 고려하되 응답 길이 제한도 고려 (환경변수로 오버라이드 가능)
# 토큰 제한 내에서 적절히 설정: 데이터 100개 ≈ 1,500토큰
# 배치가 너무 크면 JSON 응답이 너무 길어 파싱 오류 발생 가능
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = float(os.getenv('RETRY_DELAY', '2.0'))

# 프롬프트는 llm_prompts.py에서 import
from llm_prompts import (
    PREPROCESS_FAILED_RULES,
    PREPROCESS_FAILED_PROMPT_TEMPLATE,
    get_preprocess_failed_prompt,
    PREPROCESS_INITIAL_RULES,
    PREPROCESS_INITIAL_PROMPT_TEMPLATE,
    get_preprocess_initial_prompt,
    VALIDATION_RULES,
    VALIDATION_PROMPT_TEMPLATE,
    get_validation_prompt
)

# 하위 호환성을 위한 별칭
PREPROCESS_RULES = PREPROCESS_FAILED_RULES
PREPROCESS_PROMPT_TEMPLATE = PREPROCESS_FAILED_PROMPT_TEMPLATE

