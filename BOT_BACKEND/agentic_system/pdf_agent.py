import aiohttp
import ssl
import fitz  # PyMuPDF
import os
import tempfile
import asyncio

async def fetch_and_read_pdf(url: str) -> str:
    """Live downloads and extracts text from a PDF url."""
    print(f"[PDF AGENT] Attempting to download and read PDF: {url}")
    try:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_ctx, timeout=30) as response:
                if response.status != 200:
                    return f"Error downloading PDF: HTTP {response.status}"
                
                pdf_bytes = await response.read()
                
        # Save to temp file to read with PyMuPDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
            
        text_content = ""
        try:
            doc = fitz.open(tmp_path)
            for page in doc:
                text_content += page.get_text() + "\n"
            doc.close()
        except Exception as e:
            text_content = f"[PDF AGENT OCR REQUIRED] Could not read native text: {e}"
        finally:
            os.remove(tmp_path)
            
        # Clean extra spaces
        clean_text = ' '.join(text_content.split())
        
        # Truncate if too long
        if len(clean_text) > 15000:
            clean_text = clean_text[:15000] + "... [PDF Truncated]"
            
        if not clean_text.strip():
            return "PDF appears to be scanned images (requires OCR, text extraction resulted in empty string)."
            
        print(f"[PDF AGENT] Successfully read PDF ({len(clean_text)} chars).")
        return clean_text
        
    except Exception as e:
        print(f"[PDF AGENT ERROR] {url}: {e}")
        return f"Failed to read PDF document at {url}. Error: {e}"
