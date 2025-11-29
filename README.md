# Bill Extraction API

A robust, AI-powered API for extracting structured data from bills and invoices. This project leverages Google's Gemini Flash Lite model to accurately parse line items, amounts, and totals from both PDF documents and images, including those with handwritten text.

## Features

-   **AI-Powered Extraction**: Uses Gemini Flash Lite for high-accuracy data extraction.
-   **Multi-Format Support**: Handles PDF documents and image files (JPG, PNG).
-   **Handwriting Recognition**: Integrated OCR (Tesseract) and Vision capabilities to decipher handwritten bills.
-   **Large Document Handling**: Automatically splits and processes multi-page PDFs in parallel.
-   **Robust Error Handling**: Includes JSON repair logic to handle malformed AI outputs.
-   **Standardized Output**: Returns a clean, structured JSON response suitable for downstream integration.

## Prerequisites

-   Python 3.9+
-   Tesseract OCR installed and added to system PATH.
-   Poppler installed and added to system PATH (for PDF processing).
-   Google Gemini API Key.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd bill_extractor
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r bill_extractor/requirements.txt
    ```

4.  **Environment Setup:**
    Create a `.env` file in the `bill_extractor` directory (or root) with your API key:
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```

## Usage

### Starting the Server

Run the FastAPI server using uvicorn:

```bash
python -m uvicorn bill_extractor.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

### API Endpoint

**POST** `/extract-bill-data`

Extracts line items and totals from a given document URL.

**Request Body:**

```json
{
  "document": "https://example.com/path/to/bill.pdf"
}
```

**Response:**

```json
{
  "is_success": true,
  "token_usage": {
    "total_tokens": 1500,
    "input_tokens": 1200,
    "output_tokens": 300
  },
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "page_type": "Bill Detail",
        "bill_items": [
          {
            "item_name": "Paracetamol",
            "item_amount": 50.0,
            "item_rate": 5.0,
            "item_quantity": 10.0
          }
        ]
      }
    ],
    "total_item_count": 1
  }
}
```

## Project Structure

-   `bill_extractor/main.py`: FastAPI application and endpoint definition.
-   `bill_extractor/extractor.py`: Core logic for document processing, OCR, and Gemini interaction.
-   `bill_extractor/utils.py`: Utility functions for file downloading and cleanup.
