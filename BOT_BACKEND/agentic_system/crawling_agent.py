import ssl
import aiohttp
from bs4 import BeautifulSoup
import time
import asyncio
from typing import Optional

# Import the PDF agent's fetch method
try:
    from .pdf_agent import fetch_and_read_pdf
except ImportError:
    fetch_and_read_pdf = None

# Import Image OCR agent
try:
    from .image_agent import extract_text_from_images
except ImportError:
    extract_text_from_images = None

# In-memory simple cache for 10 minutes (600 seconds)
# Format: { "url": {"content": "...", "timestamp": float} }
PAGE_CACHE = {}
CACHE_TTL = 600

async def fetch_page_text(url: str) -> str:
    """Async crawler that fetches a URL and extracts clean text."""
    current_time = time.time()
    
    # Check Cache
    if url in PAGE_CACHE:
        if current_time - PAGE_CACHE[url]["timestamp"] < CACHE_TTL:
            print(f"[{time.strftime('%H:%M:%S')}] CRAWLER (Cache Hit): {url}")
            return PAGE_CACHE[url]["content"]
            
    print(f"[{time.strftime('%H:%M:%S')}] CRAWLER (Live Fetch): {url}")
    try:
        # Avoid SSL cert verification issues
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout = aiohttp.ClientTimeout(total=6, connect=3)  # Reduced from 12s to 6s
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return ""
                
                content_type = response.headers.get('Content-Type', '').lower()
                
                # If it's a PDF based on extension or mime type
                if url.lower().endswith('.pdf') or 'application/pdf' in content_type:
                    if fetch_and_read_pdf:
                        clean_text = await fetch_and_read_pdf(url)
                    else:
                        clean_text = "PDF Agent not available to parse this document."
                    
                    # Cache the PDF text
                    PAGE_CACHE[url] = {
                        "content": clean_text,
                        "timestamp": current_time
                    }
                    return clean_text
                    
                html = await response.text()
                
        # Parse HTML if it's not a PDF
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noisy elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            script.decompose()
            
        # Get raw text
        text = soup.get_text(separator=' ', strip=True)
        # Clean extra spaces
        clean_text = ' '.join(text.split())
        
        # Truncate to reasonable length to avoid exceeding context window
        if len(clean_text) > 8000:
            clean_text = clean_text[:8000] + "... [Truncated]"
            
        # Store in cache
        PAGE_CACHE[url] = {
            "content": clean_text,
            "timestamp": current_time
        }
        return clean_text
        
    except asyncio.TimeoutError:
        print(f"CRAWLER TIMEOUT for {url}")
        return ""
    except Exception as e:
        print(f"CRAWLER ERROR for {url}: {e}")
        return ""

async def fetch_multiple_urls(urls: list) -> str:
    """Fetch multiple URLs concurrently with an overall cap of 8 seconds."""
    tasks = [fetch_page_text(url) for url in urls]
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=8  # Hard cap: never wait more than 8s for all crawls
        )
    except asyncio.TimeoutError:
        print("[CRAWLER] Overall timeout hit — returning empty context")
        return ""
    
    combined = []
    for url, res in zip(urls, results):
        if isinstance(res, Exception) or not res:
            continue  # Skip failed/empty results silently
        combined.append(f"--- Data from {url} ---\n{res}\n")
    return "\n".join(combined)
