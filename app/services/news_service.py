import feedparser

RSS_FEEDS = [
    "https://finance.yahoo.com/rss/headline?s=SOXX",
    "https://finance.yahoo.com/rss/headline?s=NVDA",
    "https://finance.yahoo.com/rss/headline?s=QQQ",
]


def get_latest_news():

    news = []

    for url in RSS_FEEDS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries[:1]:

                news.append(entry.title)

        except Exception as e:

            print(e)

    return news
