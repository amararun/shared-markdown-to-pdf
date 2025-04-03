# Markdown to PDF Converter API 📄

A FastAPI-based service that converts markdown text to beautifully formatted PDF documents with professional styling.

## Setup & Running Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/amararun/shared-markdown-to-pdf.git .
```
The repository will be cloned into the current directory

### 2. Running Locally
```bash
# Install required packages
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`

### 3. Deployment on Render
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## 📖 API Documentation

Interactive API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## 🔍 API Endpoints Overview

### PDF Generation

1. **Convert Markdown to PDF** 
   - Endpoint: `POST /text-input`
   - Description: Converts markdown text to a professionally formatted PDF
   - Request Body:
   ```json
   {
       "text": "# Your Markdown Content\n\nThis is a sample markdown text."
   }
   ```
   - Response:
     - When Accept header is 'application/json':
     ```json
     {
         "pdf_url": "URL to download the generated PDF",
         "message": "PDF generated successfully"
     }
     ```
     - When Accept header is not specified: Returns the PDF file directly
   - Example Request:
   ```bash
   # Get JSON response with PDF URL
   curl -X POST "http://localhost:8000/text-input" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d '{"text": "# Hello World\n\nThis is a test."}'

   # Get direct PDF file
   curl -X POST "http://localhost:8000/text-input" \
        -H "Content-Type: application/json" \
        -d '{"text": "# Hello World\n\nThis is a test."}' \
        --output output.pdf
   ```

## ✨ Features

- 🎨 Professional PDF styling with proper spacing and typography
- 📄 Supports both direct PDF download and URL generation
- 📁 Automatic file cleanup after 1 hour
- 🌐 CORS enabled for cross-origin requests
- ⚡ Fast and efficient PDF generation

## 📝 Notes

- PDFs are automatically deleted after 1 hour
- The API supports all standard markdown syntax
- Generated PDFs include proper styling for headings, lists, tables, and code blocks
- CORS is enabled for all origins

## 🔒 Security

The API includes CORS middleware configuration for secure cross-origin requests.

## 📫 Support

For issues and feature requests, please open an issue in the repository. 