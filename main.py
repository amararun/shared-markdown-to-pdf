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
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    h1, h2, h3 {
        color: #2c3e50;
        margin-top: 1.5em;
    }
    code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
    }
    pre {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
    }
"""

class MarkdownRequest(BaseModel):
    text: str

class FixedInputRequest(BaseModel):
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
        # Prepare the form data
        form_data = {
            "markdown": markdown_req.text,
            "engine": "wkhtmltopdf",
            "css": PDF_CSS
        }

        # Make the request to the external API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://md-to-pdf.fly.dev",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"External API error: {response.text}"
                )

            # Get the PDF content
            pdf_content = response.content

            # Save PDF and get URL
            pdf_url = await save_pdf_get_url(pdf_content, request)

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fixed-input")
async def fixed_input_to_pdf(request: Request, input_req: FixedInputRequest):
    if input_req.text.lower() != "go":
        raise HTTPException(
            status_code=400,
            detail="Invalid input. Only 'go' is accepted."
        )
    
    try:
        # Fixed markdown content
        fixed_markdown = "# Hello World\n\nThis is a fixed markdown content."
        
        # Prepare the form data
        form_data = {
            "markdown": fixed_markdown,
            "engine": "wkhtmltopdf",
            "css": PDF_CSS
        }

        # Make the request to the external API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://md-to-pdf.fly.dev",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"External API error: {response.text}"
                )

            # Get the PDF content
            pdf_content = response.content

            # Save PDF and get URL
            pdf_url = await save_pdf_get_url(pdf_content, request)

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
                        "Content-Disposition": "attachment; filename=fixed_output.pdf"
                    }
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to Markdown to PDF Converter API"} 