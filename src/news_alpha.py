import os
import re
import argparse
from datetime import datetime
import feedparser
import pandas as pd

TICKER_MAP = {
    'AAPL': ['apple', 'iphone'],
    'MSFT': ['microsoft', 'azure'],
    'NVDA': ['nvidia', 'ai chip'],
    'TSLA': ['tesla', 'ev'],
    '005930.KS': ['samsung', 'galaxy', 'memory chip'],
}

RSS_FEEDS = [
    'https://feeds.reuters.com/reuters/businessNews',
    'https://feeds.reuters.com/news/wealth'
]


def fetch_news(limit_per_feed=30):
    rows = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries[:limit_per_feed]:
            rows.append({
                'title': e.get('title', ''),
                'summary': re.sub('<[^<]+?>', '', e.get('summary', '')),
                'link': e.get('link', ''),
                'published': e.get('published', ''),
            })
    return pd.DataFrame(rows)


def map_tickers(text):
    text_l = text.lower()
    hits = []
    for t, kws in TICKER_MAP.items():
        if any(k in text_l for k in kws):
            hits.append(t)
    return hits


def score_rule_based(text):
    pos = ['beat', 'surge', 'growth', 'record', 'upgrade', 'strong']
    neg = ['miss', 'drop', 'lawsuit', 'probe', 'downgrade', 'weak']
    tl = text.lower()
    s = sum(1 for w in pos if w in tl) - sum(1 for w in neg if w in tl)
    return max(-3, min(3, s))


def score_with_llm(text, client, model):
    prompt = (
        'You are a finance signal classifier. Return only one integer from -3 to 3 '\
        'for short-term stock impact sentiment for this news:\n' + text[:1500]
    )
    r = client.responses.create(model=model, input=prompt)
    out = r.output_text.strip()
    try:
        return int(re.findall(r'-?\d+', out)[0])
    except Exception:
        return score_rule_based(text)


def main(use_llm=False):
    df = fetch_news()
    if df.empty:
        print('No news fetched')
        return

    rows = []
    client = None
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    if use_llm:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL') or None)

    for _, r in df.iterrows():
        text = f"{r['title']}\n{r['summary']}"
        tickers = map_tickers(text)
        if not tickers:
            continue
        sc = score_with_llm(text, client, model) if use_llm and client else score_rule_based(text)
        for t in tickers:
            rows.append({
                'ticker': t,
                'title': r['title'],
                'score': sc,
                'link': r['link'],
                'published': r['published'],
            })

    out = pd.DataFrame(rows)
    if out.empty:
        print('No mapped ticker news')
        return

    agg = out.groupby('ticker', as_index=False)['score'].sum().sort_values('score', ascending=False)
    agg['signal'] = agg['score'].apply(lambda x: 'LONG' if x >= 2 else ('SHORT' if x <= -2 else 'NEUTRAL'))

    os.makedirs('outputs', exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = f'outputs/alpha_candidates_{ts}.csv'
    agg.to_csv(out_file, index=False)

    print('Top candidates:')
    print(agg.head(10).to_string(index=False))
    print(f'\nSaved: {out_file}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--use-llm', type=str, default='false')
    args = ap.parse_args()
    main(use_llm=args.use_llm.lower() == 'true')
