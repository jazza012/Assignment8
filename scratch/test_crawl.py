import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        r = await crawler.arun(url="https://en.wikipedia.org/wiki/Claude_Shannon")
        print(f"Status code: {r.status_code}")
        print(f"Markdown length: {len(r.markdown or '')}")
        print(f"Markdown content preview:\n{r.markdown[:1000] if r.markdown else 'None'}")

if __name__ == "__main__":
    asyncio.run(main())
