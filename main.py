from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import io
import os
import tempfile
from datetime import datetime, timedelta
import uuid
import shutil
from typing import Optional, Dict
import asyncio
from pathlib import Path

app = FastAPI(title="Markdown to PDF Converter")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create temporary directory for PDFs
TEMP_PDF_DIR = os.path.join(tempfile.gettempdir(), "markdown_pdfs")
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

# Create static directory for serving PDF files
PDF_DIR = "static/pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# Mount static directory
app.mount("/pdfs", StaticFiles(directory=PDF_DIR), name="pdfs")

# Store PDF files and their expiry times
pdf_files: Dict[str, datetime] = {}

# Define CSS style once
PDF_CSS = """
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 10px 0;
        color: #333;
        padding: 0;
    }

    .content-wrapper {
        max-width: 100%;
        margin: 0;
        padding: 0;
    }

    p {
        font-size: 17px;
        margin-bottom: 12px;
        text-align: justify;
        color: #333;
        padding: 0;
    }

    h1 {
        font-size: 36px;
        font-weight: 800;
        color: #1e3a8a;
        margin: 0 0 20px 0;
        padding: 0 0 8px 0;
        border-bottom: 2px solid #1e3a8a;
        line-height: 1.2;
    }

    h2 {
        font-size: 28px;
        font-weight: 700;
        color: #1e40af;
        margin: 20px 0 12px 0;
        line-height: 1.2;
    }

    h3 {
        font-size: 22px;
        font-weight: 600;
        color: #333;
        margin: 16px 0 6px 0;
        line-height: 1.2;
    }

    h4 {
        font-size: 20px;
        font-weight: 600;
        color: #4f46e5;
        margin: 14px 0 8px 0;
        line-height: 1.2;
    }

    ul, ol {
        margin-left: 16px;
        margin-bottom: 4px;
        padding-left: 12px;
        line-height: 1.1;
    }

    li {
        margin-bottom: 4px;
        font-size: 17px;
        color: #333;
        line-height: 1.7;
        padding-top: 0;
        padding-bottom: 0;
    }

    li p {
        margin: 0;
        line-height: 1.7;
    }

    li > ul, li > ol {
        margin-top: 0px;
        margin-bottom: 0px;
        padding-left: 12px;
    }

    li > ul li, li > ol li {
        margin-bottom: 0px;
    }

    ul:last-child, ol:last-child {
        margin-bottom: 4px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }

    th {
        background-color: #f8fafc;
        padding: 12px;
        text-align: left;
        font-weight: 600;
        color: #1e40af;
        border: 1px solid #e2e8f0;
    }

    td {
        padding: 12px;
        border: 1px solid #e2e8f0;
        color: #333;
    }

    code {
        background-color: #f1f5f9;
        padding: 2px 4px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 14px;
    }

    pre code {
        display: block;
        padding: 12px;
        margin: 16px 0;
        overflow-x: auto;
    }
"""

class MarkdownRequest(BaseModel):
    text: str

async def cleanup_old_files():
    """Clean up expired PDF files."""
    while True:
        current_time = datetime.now()
        # Check each file
        expired_files = [
            filename for filename, expiry_time in pdf_files.items()
            if current_time > expiry_time
        ]
        
        # Remove expired files
        for filename in expired_files:
            file_path = os.path.join(PDF_DIR, filename)
            try:
                os.remove(file_path)
                del pdf_files[filename]
            except (OSError, KeyError):
                pass
        
        # Run every 10 minutes
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    """Start the cleanup task when the app starts."""
    asyncio.create_task(cleanup_old_files())

async def save_pdf_get_url(pdf_content: bytes, request: Request) -> str:
    """Save PDF content and return its URL."""
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"doc_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(PDF_DIR, filename)
    
    # Save the file
    with open(filepath, "wb") as f:
        f.write(pdf_content)
    
    # Set expiry (1 hour from now)
    pdf_files[filename] = datetime.now() + timedelta(hours=1)
    
    # Construct the full URL
    return f"{request.base_url}pdfs/{filename}"

@app.post("/text-input")
async def text_input_to_pdf(request: Request, markdown_req: MarkdownRequest):
    try:
        # Log the request details
        print(f"Received markdown request with text length: {len(markdown_req.text)}")
        
        # Check if the markdown content is too large
        if len(markdown_req.text) > 100000:  # 100KB limit
            print(f"Markdown content too large: {len(markdown_req.text)} bytes")
            raise HTTPException(
                status_code=400,
                detail=f"Markdown content too large: {len(markdown_req.text)} bytes. Maximum allowed is 100KB."
            )
        
        # Prepare the form data
        form_data = {
            "markdown": markdown_req.text,
            "engine": "wkhtmltopdf",
            "css": PDF_CSS
        }

        # Make the request to the external API
        async with httpx.AsyncClient() as client:
            print(f"Sending request to external API: https://md-to-pdf.fly.dev")
            try:
                # Log the first 100 characters of the markdown for debugging
                print(f"Markdown preview: {markdown_req.text[:100]}...")
                
                response = await client.post(
                    "https://md-to-pdf.fly.dev",
                    data=form_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0  # Add a timeout
                )
                
                print(f"External API response status: {response.status_code}")
                print(f"External API response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    error_detail = f"External API error: {response.text}"
                    print(f"Error from external API: {error_detail}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                # Get the PDF content
                pdf_content = response.content
                print(f"Received PDF content with size: {len(pdf_content)} bytes")
                
                # Save PDF and get URL
                pdf_url = await save_pdf_get_url(pdf_content, request)
                print(f"Saved PDF and generated URL: {pdf_url}")
                
                # Return both the direct PDF and the URL
                if request.headers.get("accept") == "application/json":
                    return JSONResponse({
                        "pdf_url": pdf_url,
                        "message": "PDF generated successfully"
                    })
                else:
                    # Return the PDF directly as before
                    return StreamingResponse(
                        io.BytesIO(pdf_content),
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": "attachment; filename=converted.pdf"
                        }
                    )
            except httpx.RequestError as e:
                print(f"Request error to external API: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Request error to external API: {str(e)}")
            except httpx.TimeoutException as e:
                print(f"Timeout error to external API: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Timeout error to external API: {str(e)}")

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in text_input_to_pdf: {str(e)}")
        print(f"Traceback: {error_traceback}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to Markdown to PDF Converter API"} 