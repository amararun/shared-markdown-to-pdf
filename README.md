# Markdown to PDF Converter API

A FastAPI-based service that converts Markdown text to PDF using an external API.

## Setup

1. Create a virtual environment (recommended):
```powershell
python -m venv venv
.\venv\Scripts\activate
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Run the server:
```powershell
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

## API Usage

### Convert Markdown to PDF

**Endpoint:** `POST /convert`

**Request Body:**
```json
{
    "text": "# Your Markdown Content\n\nThis is a sample markdown text."
}
```

**Response:**
- Returns a PDF file with the converted content
- Content-Type: application/pdf
- Filename: converted.pdf

### Example using curl:

```bash
curl -X POST "http://localhost:8000/convert" \
     -H "Content-Type: application/json" \
     -d '{"text": "# Hello World\n\nThis is a test."}' \
     --output output.pdf
```

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): `http://your-server-url.com/docs`
- Alternative API docs (ReDoc): `http://your-server-url.com/redoc` 
