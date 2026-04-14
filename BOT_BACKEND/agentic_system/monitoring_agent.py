import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time
from .crawling_agent import fetch_page_text, PAGE_CACHE

MONITOR_URLS = [
    "https://svsu.ac.in/tender-notice",
    "https://svsu.ac.in/office-orders",
    "https://svsu.ac.in/news-events",
    "https://svsu.ac.in/announcements"
]

async def check_for_updates():
    print(f"\n--- [MONITORING AGENT] Tracked Updates at {time.strftime('%H:%M:%S')} ---")
    for url in MONITOR_URLS:
        try:
            # Force cache clear for these specific URLs to get live data
            if url in PAGE_CACHE:
                del PAGE_CACHE[url]
            # This triggers a live fetch, which re-populates the cache
            await fetch_page_text(url)
        except Exception as e:
            print(f"[MONITORING AGENT] Background task error for {url}: {e}")
    print("--- [MONITORING AGENT] Background refresh complete ---\n")

def start_monitoring():
    """Initializes the periodic monitoring agent on start."""
    # We create an async scheduler
    scheduler = AsyncIOScheduler()
    
    from datetime import datetime, timedelta
    scheduler.add_job(check_for_updates, 'date', run_date=datetime.now() + timedelta(seconds=5))
    
    # Schedule repeating task every 15 minutes to stay updated
    scheduler.add_job(check_for_updates, 'interval', minutes=15)
    
    scheduler.start()
    print("[MONITORING AGENT] Up and running. Tracking SVSU changes every 15 minutes.")
