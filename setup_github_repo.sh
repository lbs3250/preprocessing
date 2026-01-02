#!/bin/bash
# GitHub 저장소 설정 스크립트

echo "=========================================="
echo "GitHub 저장소 설정"
echo "=========================================="
echo ""

# 1. 저장소 확인
echo "1. 저장소 확인 중..."
echo "   https://github.com/lbs3250/preprocessing-test"
echo ""
echo "   브라우저에서 위 URL로 접속하여 저장소가 있는지 확인하세요."
echo ""

# 2. Git 설정 확인
echo "2. 현재 Git 설정:"
git config user.name
git config user.email
echo ""

# 3. 원격 저장소 확인
echo "3. 원격 저장소:"
git remote -v
echo ""

# 4. 커밋 상태 확인
echo "4. 커밋 상태:"
git log --oneline -5
echo ""

echo "=========================================="
echo "다음 단계"
echo "=========================================="
echo ""
echo "저장소가 없다면:"
echo "  1. https://github.com/new 접속"
echo "  2. Repository name: preprocessing-test"
echo "  3. Public 또는 Private 선택"
echo "  4. 'Initialize this repository with a README' 체크 해제"
echo "  5. Create repository 클릭"
echo ""
echo "저장소가 있다면:"
echo "  Personal Access Token 생성 후:"
echo "  git push -u origin main"
echo ""

