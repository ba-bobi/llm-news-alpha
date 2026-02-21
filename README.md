# LLM News Alpha (Prototype)

주요 금융 뉴스를 수집하고(Reuters RSS), LLM으로 종목별 모멘텀 점수를 추정해
단기 아이디어(롱/숏 후보)를 생성하는 실험 프로젝트입니다.

## Features
- Reuters Business/Markets RSS 수집
- 티커 키워드 매핑 기반 기사-종목 연결
- LLM(선택)으로 기사별 감성/임팩트 점수화
- 종목별 알파 점수 집계 및 랭킹 출력

## Quickstart
```bash
pip install -r requirements.txt
python src/news_alpha.py --use-llm false
```

LLM 사용 시 환경변수 설정:
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (선택)
- `OPENAI_MODEL` (기본: gpt-4o-mini)

## Output
`outputs/alpha_candidates_YYYYMMDD_HHMMSS.csv`
