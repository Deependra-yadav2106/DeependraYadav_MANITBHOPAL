import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from .utils import download_file, cleanup_file
import PyPDF2
import io

import asyncio
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-2.5-flash-lite",
  generation_config=generation_config,
)

PROMPT = """
You are an expert data extraction assistant. Your task is to extract individual line item details from the provided bill/invoice document.

**Goal:** Extract the list of items purchased/services rendered so that their sum equals the bill's final total.

**Context from OCR (Handwriting/Text):**
{ocr_context}

**Rules:**
1. **Extract Line Items:** Extract individual products, medicines, services, or charges.
   - **EXCLUDE:** Subtotals, Previous Balances, Amount Due, Total, Net Total, or any aggregate fields. Do NOT extract these as line items.
   - **INCLUDE:** Taxes or Discounts ONLY if they are listed as separate line items with their own amount that contributes to the final total.
2. **Pagewise Extraction:** Group items by page. Identify the page number and page type.
   - Page Types: "Bill Detail", "Final Bill", "Pharmacy". Infer the type based on content.
3. **Item Details:**
   - `item_name`: Exactly as mentioned in the bill.
   - `item_amount`: The total amount for this line item (Rate * Quantity). If there is a discount specific to this item, use the net amount.
     - **CRITICAL:** MUST be a currency value. Do NOT extract Invoice Numbers, Dates (e.g., 20231012), Phone Numbers, or IDs as amounts.
   - `item_rate`: Rate per unit. If not present, infer from Amount/Quantity or set to null.
   - `item_quantity`: Quantity. If not present, set to 1.
4. **Totals:** Calculate the total count of items extracted.
5. **Accuracy:** Do not double count. The sum of `item_amount` of all extracted items MUST equal the Final Bill Total. Verify this internally before outputting.
   - **Handwriting:** The document may contain handwritten text. Use the provided OCR context to help decipher unclear text, but prioritize visual evidence from the image if OCR is garbled.
   - If handwriting is unclear, infer from context (e.g., rate * quantity = amount).
6. **Output Format:** The output MUST be a valid JSON object. To save tokens, `bill_items` MUST be a list of lists, where each inner list is `[item_name, item_amount, item_rate, item_quantity]`.

```json
{
  "pagewise_line_items": [
    {
      "page_no": "string",
      "page_type": "Bill Detail | Final Bill | Pharmacy",
      "bill_items": [
        ["item_name", item_amount, item_rate, item_quantity],
        ["item_name_2", item_amount_2, item_rate_2, item_quantity_2]
      ]
    }
  ],
  "total_item_count": integer
}
```

**CRITICAL:**
- `bill_items` is a list of lists. Do NOT use objects for items.
- Ensure all numbers are valid JSON numbers (e.g., use `4.0` or `4`, NOT `4.`).
- Do NOT use trailing commas.
- Ensure the JSON is complete and properly closed.
- **OUTPUT MINIFIED JSON:** Do not use unnecessary whitespace or indentation to save tokens.

If a field is missing or not applicable, use null or 0 as appropriate.
For `page_no`, if not explicitly marked, infer it (starting from 1).
"""

def extract_ocr_text(file_path: str, mime_type: str) -> str:
    """
    Extracts text from the file using Tesseract OCR.
    Handles Images directly. For PDFs, uses pdf2image to convert to images first.
    """
    ocr_text = ""
    try:
        if mime_type.startswith("image/"):
            image = Image.open(file_path)
            ocr_text = pytesseract.image_to_string(image)
        elif mime_type == "application/pdf":
            try:

                images = convert_from_path(file_path)
                for i, image in enumerate(images):
                    text = pytesseract.image_to_string(image)
                    ocr_text += f"\n[Page {i+1} OCR]: {text}\n"
            except Exception as e:
                print(f"PDF OCR failed (pdf2image): {e}")
                ocr_text = f"OCR failed for PDF: {e}"
            
            if not ocr_text:
                 ocr_text = "OCR not available for this PDF (Image extraction failed)."

    except Exception as e:
        print(f"OCR Failed: {e}")
        ocr_text = f"OCR Failed: {e}"
    
    return ocr_text

async def _extract_with_gemini(file_path: str, mime_type: str):
    # Upload the file

    file_ref = genai.upload_file(file_path, mime_type=mime_type)
    

    loop = asyncio.get_running_loop()
    ocr_context = await loop.run_in_executor(None, extract_ocr_text, file_path, mime_type)
    
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n\n=== Processing {file_path} ===\n")
        f.write(f"OCR Context Length: {len(ocr_context)}\n")
        f.write(f"OCR Context Preview: {ocr_context[:200]}...\n")
    
    formatted_prompt = PROMPT.replace("{ocr_context}", ocr_context)

    # Generate content with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:

            response = await model.generate_content_async([formatted_prompt, file_ref])
            

            text = response.text
            
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"LLM Response Raw (Attempt {attempt+1}):\n{text}\n")
            

            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            

            
            try:
                extracted_data = json.loads(text)
            except json.JSONDecodeError:

                print("JSON parse failed, attempting repair...")
                text_repaired = text.replace("}}", "}")
                try:
                     extracted_data = json.loads(text_repaired)
                     print("JSON repair successful.")
                except:

                    if text.strip().endswith("}}"):
                        text_repaired = text.strip()[:-2] + "}"
                        extracted_data = json.loads(text_repaired)
                    else:
                        raise
            

            if "pagewise_line_items" in extracted_data:
                for page in extracted_data["pagewise_line_items"]:
                    if "bill_items" in page and isinstance(page["bill_items"], list):
                        new_items = []
                        for item in page["bill_items"]:
                            if isinstance(item, list) and len(item) >= 4:
                                new_items.append({
                                    "item_name": item[0],
                                    "item_amount": item[1],
                                    "item_rate": item[2],
                                    "item_quantity": item[3]
                                })
                            elif isinstance(item, dict):
                                new_items.append(item)
                        page["bill_items"] = new_items
            

            usage = response.usage_metadata
            token_usage = {
                "total_tokens": usage.total_token_count,
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            }

            return extracted_data, token_usage
            
        except json.JSONDecodeError:
            error_msg = f"Failed to parse LLM response as JSON. Length: {len(text)}. Start: {text[:200]}... End: ...{text[-200:]}"
            print(error_msg)
            if attempt == max_retries - 1:
                raise Exception(error_msg)
            print(f"JSON parse failed, retrying ({attempt + 1}/{max_retries})...")
            continue
        except Exception as e:
            import traceback
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"Exception in _extract_with_gemini: {e}\n")
                f.write(traceback.format_exc() + "\n")
            
            if attempt == max_retries - 1:
                raise e
            print(f"Generation failed: {e}, retrying ({attempt + 1}/{max_retries})...")
            continue

async def process_document(url: str):
    """
    Downloads the document, sends it to Gemini for extraction, and returns the structured data and token usage.
    Handles large PDFs by splitting them into chunks and processing in parallel.
    """
    file_path = download_file(url)
    try:
        mime_type = "application/pdf" if file_path.endswith(".pdf") else "image/jpeg"
        if file_path.endswith(".png"): mime_type = "image/png"


        if mime_type == "application/pdf":
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    num_pages = len(reader.pages)
                
                if num_pages > 2:
                    print(f"Large PDF detected ({num_pages} pages). Processing in chunks...")
                    
                    chunk_size = 1
                    all_pages_data = []
                    total_usage = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
                    
                    chunk_files = []
                    
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        
                        for i in range(0, num_pages, chunk_size):
                            chunk_writer = PyPDF2.PdfWriter()
                            end_page = min(i + chunk_size, num_pages)
                            for page_num in range(i, end_page):
                                chunk_writer.add_page(reader.pages[page_num])
                            

                            import tempfile
                            fd, chunk_path = tempfile.mkstemp(suffix=".pdf")
                            os.close(fd)
                            
                            with open(chunk_path, 'wb') as out_f:
                                chunk_writer.write(out_f)
                            
                            chunk_files.append(chunk_path)
                    
                    try:

                        tasks = [_extract_with_gemini(cp, mime_type) for cp in chunk_files]
                        results = await asyncio.gather(*tasks)
                        
                        for i, (data, usage) in enumerate(results):
                            print(f"Processed chunk {i+1}")
                            if data and "pagewise_line_items" in data:
                                all_pages_data.extend(data["pagewise_line_items"])
                            
                            if usage:
                                total_usage["total_tokens"] += usage["total_tokens"]
                                total_usage["input_tokens"] += usage["input_tokens"]
                                total_usage["output_tokens"] += usage["output_tokens"]
                                
                    finally:
                        for cp in chunk_files:
                            if os.path.exists(cp):
                                os.remove(cp)
                    

                    final_data = {
                        "pagewise_line_items": all_pages_data,
                        "total_item_count": sum(len(p.get("bill_items", [])) for p in all_pages_data)
                    }
                    return final_data, total_usage

            except Exception as e:
                print(f"Error processing PDF chunks: {e}. Falling back to single file processing.")



        return await _extract_with_gemini(file_path, mime_type)

    except Exception as e:
        print(f"Error in process_document: {e}")

        if "404" in str(e) or "not found" in str(e).lower():
             print("Model not found. Listing available models...")
             for m in genai.list_models():
                 if 'generateContent' in m.supported_generation_methods:
                     print(m.name)
        raise e

    finally:
        cleanup_file(file_path)
 
