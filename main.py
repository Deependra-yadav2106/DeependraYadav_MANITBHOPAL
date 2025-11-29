from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .extractor import process_document
import uvicorn
import traceback

app = FastAPI(title="HackRx Bill Extraction API")

class ExtractRequest(BaseModel):
    document: str

class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int

class BillItem(BaseModel):
    item_name: str
    item_amount: float | None = None
    item_rate: float | None = None
    item_quantity: float | None = None

class PageItem(BaseModel):
    page_no: str
    page_type: str
    bill_items: list[BillItem]

class ExtractedData(BaseModel):
    pagewise_line_items: list[PageItem]
    total_item_count: int

class ExtractResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsage | None = None
    data: ExtractedData | None = None
    message: str | None = None

@app.post("/extract-bill-data", response_model=ExtractResponse)
async def extract_bill_data(request: ExtractRequest):
    try:
        data, usage = await process_document(request.document)
        
        return ExtractResponse(
            is_success=True,
            token_usage=TokenUsage(**usage),
            data=ExtractedData(**data)
        )
    except Exception as e:
        traceback.print_exc()
        return ExtractResponse(
            is_success=False,
            message=f"Failed to process document. {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
