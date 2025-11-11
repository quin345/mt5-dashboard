import requests
import csv

# Replace with your actual API key
api_key = '5LM14J8UVA6DDFYE'
url = (
    'https://www.alphavantage.co/query?function=NEWS_SENTIMENT'
    '&topics=financial_markets'
    '&time_from=20150101T0000'
    '&limit=1000'
    f'&apikey={api_key}'
)

# Fetch data
response = requests.get(url)
data = response.json()

# Extract news items
news_items = data.get("feed", [])

# Define CSV headers
headers = [
    "title", "summary", "source", "url", "time_published",
    "overall_sentiment_score", "overall_sentiment_label",
    "tickers_sentiment", "topics"
]

# Write to CSV
with open("financial_markets_news.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    for item in news_items:
        # Format ticker sentiment
        tickers_sentiment = "; ".join([
            f"{ts.get('ticker', '')} (score: {ts.get('ticker_sentiment_score', 'N/A')}, label: {ts.get('ticker_sentiment_label', 'N/A')})"
            for ts in item.get("ticker_sentiment", [])
        ])

        # Format topics
        topics = "; ".join([
            f"{tp.get('topic', '')} (relevance: {tp.get('relevance_score', 'N/A')})"
            for tp in item.get("topics", [])
        ])

        writer.writerow([
            item.get("title", ""),
            item.get("summary", ""),
            item.get("source", ""),
            item.get("url", ""),
            item.get("time_published", ""),
            item.get("overall_sentiment_score", ""),
            item.get("overall_sentiment_label", ""),
            tickers_sentiment,
            topics
        ])