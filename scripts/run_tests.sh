#!/bin/bash
# 테스트 실행 스크립트
# 작업 프로세스에 따라 모든 테스트와 검사를 수행합니다.

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 키움증권 백테스팅 시스템 - 테스트 실행"
echo "=========================================="

# 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${RED}❌ 오류: 가상환경이 활성화되지 않았습니다!${NC}"
    echo "실행: source venv/bin/activate"
    exit 1
fi

echo -e "${GREEN}✅ 가상환경 활성화 확인${NC}"

# 1. 코드 스타일 검사
echo -e "\n${YELLOW}📝 코드 스타일 검사...${NC}"
echo "------------------------"

echo "Black 검사..."
black --check src/ tests/
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Black 검사 실패! 'black src/ tests/' 실행 필요${NC}"
    exit 1
fi

echo "isort 검사..."
isort --check-only src/ tests/
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ isort 검사 실패! 'isort src/ tests/' 실행 필요${NC}"
    exit 1
fi

echo "flake8 검사..."
flake8 src/ tests/
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ flake8 검사 실패!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 코드 스타일 검사 통과${NC}"

# 2. 타입 체크
echo -e "\n${YELLOW}🔍 타입 체크...${NC}"
echo "---------------"
mypy src/
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 타입 체크 실패!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 타입 체크 통과${NC}"

# 3. 단위 테스트
echo -e "\n${YELLOW}🧪 단위 테스트 실행...${NC}"
echo "---------------------"
pytest tests/unit/ -v --tb=short
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 단위 테스트 실패!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 단위 테스트 통과${NC}"

# 4. 통합 테스트
echo -e "\n${YELLOW}🧪 통합 테스트 실행...${NC}"
echo "---------------------"
if [ -d "tests/integration" ] && [ "$(ls -A tests/integration/*.py 2>/dev/null)" ]; then
    pytest tests/integration/ -v --tb=short
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 통합 테스트 실패!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 통합 테스트 통과${NC}"
else
    echo -e "${YELLOW}⚠️  통합 테스트가 없습니다${NC}"
fi

# 5. 커버리지 리포트
echo -e "\n${YELLOW}📊 커버리지 리포트...${NC}"
echo "--------------------"
pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 커버리지 80% 미달!${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ 모든 테스트 통과!${NC}"
echo "HTML 커버리지 리포트: htmlcov/index.html"

# 6. 문서 체크 (선택사항)
echo -e "\n${YELLOW}📚 문서 확인...${NC}"
echo "---------------"
if [ -f "scripts/check_docs.py" ]; then
    python scripts/check_docs.py
else
    echo -e "${YELLOW}⚠️  문서 체크 스크립트가 없습니다${NC}"
fi

echo -e "\n${GREEN}🎉 작업 완료! 문서 업데이트를 진행하세요.${NC}"