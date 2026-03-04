#!/bin/bash
# coin-agent 초기 세팅 스크립트
# 사용법: bash setup.sh

set -e  # 에러 발생 시 즉시 중단

echo "=== [1/3] 가상환경 생성 ==="
python3.11 -m venv venv
echo "✅ venv 생성 완료"

echo ""
echo "=== [2/3] 가상환경 활성화 및 패키지 설치 ==="
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ 패키지 설치 완료"

echo ""
echo "=== [3/3] 환경변수 파일 생성 ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ .env 파일 생성됨 → 실제 API 키를 .env에 입력하세요"
else
    echo "ℹ️  .env 파일이 이미 존재합니다. 건너뜀"
fi

echo ""
echo "==================================="
echo "🚀 세팅 완료!"
echo ""
echo "다음 단계:"
echo "  1. .env 파일에 업비트 API 키 입력"
echo "  2. source venv/bin/activate  (매 세션마다 필요)"
echo "  3. python main.py  (Step 12 완료 후 실행 가능)"
echo "==================================="