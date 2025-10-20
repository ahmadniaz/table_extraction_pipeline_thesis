"""
Minimal PDF Proxy for CORS-compliant PDF viewing
Proxies GCS signed URLs through backend to avoid CORS issues
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/pdf-proxy")
async def proxy_pdf(url: str = Query(..., description="GCS signed URL to proxy")):
    """
    Simple proxy that fetches PDF from GCS signed URL and returns it with CORS headers.
    This avoids browser CORS restrictions when loading PDFs directly from GCS.
    """
    try:
        if not url or not url.strip():
            raise HTTPException(status_code=400, detail="Missing or invalid url parameter")
        
        # Validate it's a GCS URL
        if "storage.googleapis.com" not in url:
            raise HTTPException(status_code=400, detail="Invalid URL: must be a Google Cloud Storage URL")
        
        logger.info(f"🔄 Proxying PDF from: {url[:100]}...")
        
        # Fetch PDF from GCS signed URL
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch PDF: HTTP {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch PDF from storage: {response.status_code}"
                )
            
            # Return PDF with CORS headers
            return Response(
                content=response.content,
                media_type="application/pdf",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Content-Disposition": "inline; filename=\"document.pdf\"",
                    "Cache-Control": "public, max-age=3600",
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PDF proxy error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to proxy PDF: {str(e)}")

@router.options("/pdf-proxy")
async def pdf_proxy_options():
    """CORS preflight handler"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        }
    )

