# GitHub 푸시 가이드

## 현재 상태

✅ **커밋 완료**: 5개 커밋
✅ **Git 사용자**: lbs3250 <lbs3250@gmail.com>
✅ **원격 저장소**: https://github.com/lbs3250/preprocessing-test.git
✅ **브랜치**: main

## 저장소 확인

먼저 저장소가 정말 만들어져 있는지 확인하세요:

**브라우저에서 접속:**
```
https://github.com/lbs3250/preprocessing-test
```

### 저장소가 없는 경우

1. https://github.com/new 접속
2. Repository name: `preprocessing-test`
3. Description: "LLM-based preprocessing and validation system for clinical trials data"
4. Public 또는 Private 선택
5. **"Initialize this repository with a README" 체크 해제** (이미 로컬에 파일이 있으므로)
6. "Create repository" 클릭

### 저장소가 있는 경우

Personal Access Token이 필요합니다.

## Personal Access Token 생성

1. https://github.com/settings/tokens 접속
2. "Generate new token (classic)" 클릭
3. Note: `preprocessing-test`
4. Expiration: 원하는 기간 선택
5. 권한: **`repo`** 체크 (전체 권한)
6. "Generate token" 클릭
7. **토큰 복사** (한 번만 표시됨!)

## 푸시 실행

토큰을 생성한 후:

```bash
git push -u origin main
```

인증 프롬프트가 나오면:
- **Username**: `lbs3250`
- **Password**: 생성한 Personal Access Token 붙여넣기

## 대안: SSH 사용

SSH 키가 있다면:

```bash
git remote set-url origin git@github.com:lbs3250/preprocessing-test.git
git push -u origin main
```

## 커밋된 내용

- ✅ LLM 전처리 및 검증 스크립트
- ✅ Inclusion/Exclusion 처리 스크립트
- ✅ 데이터베이스 스키마
- ✅ 문서 및 사용 가이드
- ✅ README.md

## 문제 해결

### "Repository not found" 에러

1. 저장소가 정말 만들어져 있는지 확인
2. 저장소 이름이 정확한지 확인 (대소문자 구분)
3. Personal Access Token 생성 및 사용

### 인증 실패

1. Personal Access Token이 `repo` 권한을 가지고 있는지 확인
2. 토큰이 만료되지 않았는지 확인
3. Username과 Password(Token)를 정확히 입력했는지 확인

