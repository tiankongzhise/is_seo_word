from src.is_seo_word.main_async_by_man import main_async
if __name__ == '__main__':
    concurrency = 50
    batch = 100
    import asyncio
    results = asyncio.run(main_async(max_concurrency=concurrency, batch_size=batch))
