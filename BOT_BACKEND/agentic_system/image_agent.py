import pytesseract
from PIL import Image
from io import BytesIO
import asyncio
import aiohttp

async def process_image_url(image_url: str, session: aiohttp.ClientSession, ssl_ctx) -> str:
    """Downloads an image and runs OCR on it. Gracefully fails if tesseract is missing."""
    try:
        # Skip small icons like svsu logo or SVGs
        lower_url = image_url.lower()
        if 'logo' in lower_url or 'icon' in lower_url or lower_url.endswith('.svg'):
            return ""

        async with session.get(image_url, ssl=ssl_ctx, timeout=8) as response:
            if response.status == 200:
                img_data = await response.read()
                img = Image.open(BytesIO(img_data))
                
                # We skip very small images to save time
                if img.width < 100 or img.height < 100:
                    return ""
                
                # Perform OCR
                text = pytesseract.image_to_string(img)
                clean_text = " ".join(text.split())
                if len(clean_text) > 5:  # Only return if it actually extracted meaningful text
                    print(f"[IMAGE AGENT] Found text in image {image_url[-20:]}: {clean_text[:50]}...")
                    return f"\n[IMAGE OCR TEXT from {image_url}]: {clean_text}\n"
    except pytesseract.TesseractNotFoundError:
        # Tesseract executable not found on host, silently fail
        pass
    except Exception as e:
        print(f"[IMAGE AGENT ERROR] {image_url}: {e}")
    
    return ""

async def extract_text_from_images(image_urls: list, ssl_ctx) -> str:
    """Takes a list of image URLs, downloads them concurrently, and extracts text."""
    if not image_urls:
        return ""
    
    # Cap maximum images per page to avoid extreme sluggishness
    capped_urls = image_urls[:5] 
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_image_url(url, session, ssl_ctx) for url in capped_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    combined_image_text = ""
    for res in results:
        if isinstance(res, str) and res:
            combined_image_text += res
            
    return combined_image_text
