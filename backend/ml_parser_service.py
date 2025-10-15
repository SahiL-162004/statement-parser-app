import pdfplumber
import io
import re
from datetime import datetime

# --- IMPORTANT ---
# Your Project and Processor IDs should be filled in here.
PROJECT_ID = "pdf-parser-assignment"
LOCATION = "us" 
PROCESSOR_ID = "a4c291d982e5a7d4" 

def find_value_by_proximity(text, keywords, value_pattern, window=100):
    for value_match in re.finditer(value_pattern, text, re.IGNORECASE):
        start = max(0, value_match.start() - window)
        end = min(len(text), value_match.end() + window)
        snippet = text[start:end]
        
        for keyword in keywords:
            if re.search(keyword, snippet, re.IGNORECASE):
                return value_match.group(0).strip().replace('\n', ' ')
    return "N/A"

def parse_with_ml(file_bytes: bytes) -> dict:
    from google.cloud import documentai_v1 as documentai

    opts = {"api_endpoint": f"{LOCATION}-documentai.googleapis.com"}
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{PROCESSOR_ID}"
    raw_document = documentai.RawDocument(content=file_bytes, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    try:
        result = client.process_document(request=request)
        document = result.document
    except Exception as e:
        return {"error": f"Error calling Document AI: {e}"}
        
    text = document.text

    # --- Issuer Detection ---
    ISSUER_KEYWORDS = {
        "HDFC": ["HDFC Bank"], "SBI": ["SBI Card"], "ICICI": ["ICICI Bank"],
        "AXIS": ["AXIS BANK"], "KOTAK": ["Kotak"], "AMEX": ["AMERICAN EXPRESS"],
        "CITI": ["citibank"], "RBL": ["RBL Bank"], "SC": ["Standard Chartered"],
        "BOB": ["Bank of Baroda"], "IDFC": ["IDFC FIRST Bank", "IDFC"]
    }
    detected_issuer = "Unknown"
    for issuer_name, keywords in ISSUER_KEYWORDS.items():
        for keyword in keywords:
            if re.search(keyword, text, re.IGNORECASE):
                detected_issuer = issuer_name
                break
        if detected_issuer != "Unknown":
            break

    # --- GSTIN Extraction ---
    gstin = "N/A"
    gstin_match = re.search(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b", text)
    if gstin_match:
        gstin = gstin_match.group(1)

    # --- Extraction Logic ---
    extracted_data = {
        "issuer": detected_issuer,
        "gstin": gstin,
    }
    
    # Define patterns for various fields
    date_pattern_generic = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s\d{1,2},\s*\d{4}|\d{1,2}[- ]\w{3}[- ]\d{2,4})\b"
    money_pattern = r"([\d,]+\.\d{2})"
    
    name_patterns = [
        re.compile(r"Name\s*:\s*([A-Z\s]+)"),
        re.compile(r"Dear\s+([A-Z\s]+),", re.IGNORECASE),
        re.compile(r"MR\s+([A-Za-z\s]+)"),
        re.compile(r"PREPARED\s*FOR\s+([A-Z\s]+)"),
        # New pattern for Axis Bank format
        re.compile(r"AXIS BANK\n([A-Z\s]+)\nJoint Holder", re.IGNORECASE),
    ]

    # Use simple, direct search for name first
    def find_first_match(patterns):
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip().replace('\n', ' ')
        return "N/A"

    extracted_data["cardholder_name"] = find_first_match(name_patterns)
    
    # Use proximity search for dates and amounts
    extracted_data["payment_due_date"] = find_value_by_proximity(text, ["due date", "payment due"], date_pattern_generic)
    
    # Smart search for Total Due / Closing Balance
    total_due = find_value_by_proximity(text, ["total amount due", "total dues", "new balance", "amount payable"], money_pattern)
    if total_due == "N/A":
        # Fallback to bank account statement terms if credit card terms fail
        total_due = find_value_by_proximity(text, ["closing balance"], money_pattern)
    extracted_data["total_due"] = total_due

    return extracted_data