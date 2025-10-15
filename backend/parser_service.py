import pdfplumber
import io
import re

# --- Data Cleaning & Post-Processing Functions ---

def post_process_amount(value):
    try:
        value = re.sub(r'[^\d.-]', '', value)
        return float(value)
    except (ValueError, TypeError):
        return None

def post_process_name(value):
    return re.sub(r'\s+', ' ', value).strip()

def post_process_date(value):
    return value.strip().replace('\n', ' ')

# --- UNIVERSAL PATTERNS TO BE USED BY EACH BANK'S CONFIG ---
GSTIN_PATTERN = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b")

# --- CONFIGURATION: The "Brain" of the Rule-Based Parser ---
PARSER_CONFIG = {
    "HDFC": {
        "issuer_keywords": ["HDFC Bank"],
        "extractors": [
            {"key": "cardholder_name", "patterns": [re.compile(r"Name\s*:\s*([A-Z\s]+)"), re.compile(r"Dear\s+([A-Z\s]+),")], "post_process": post_process_name},
            {"key": "payment_due_date", "patterns": [re.compile(r"Payment\s*Due\s*Date[^\n]+\n\"(\d{2}/\d{2}/\d{4})"), re.compile(r"Payment\s*Due\s*Date\s*:\s*(\d{2}/\d{2}/\d{4})")], "post_process": post_process_date},
            {"key": "total_due", "patterns": [re.compile(r"Total\s*Dues[^\n]+\n\"[^\"]+\"\s*,\s*\"([\d,]+\.\d{2})"), re.compile(r"Total\s*Amount\s*Due\s*Rs\.?\s*([\d,]+\.\d{2})")], "post_process": post_process_amount},
            {"key": "gstin", "patterns": [GSTIN_PATTERN]}
        ]
    },
    "ICICI": {
        "issuer_keywords": ["ICICI Bank"],
        "extractors": [
            {"key": "cardholder_name", "patterns": [re.compile(r"MR\s+([A-Za-z\s]+)")], "post_process": post_process_name},
            {"key": "payment_due_date", "patterns": [re.compile(r"PAYMENT\s*DUE\s*DATE\s*\n\s*(\w+\s*\d{1,2},\s*\d{4})", re.IGNORECASE)], "post_process": post_process_date},
            {"key": "total_due", "patterns": [re.compile(r"Total\s*Amount\s*due\s*\n\s*([\d,]+\.\d{2})", re.IGNORECASE)], "post_process": post_process_amount},
            {"key": "gstin", "patterns": [GSTIN_PATTERN]}
        ]
    },
    # Add simplified rules for other banks
    "SBI": {
        "issuer_keywords": ["SBI Card"],
        "extractors": [
            {"key": "cardholder_name", "patterns": [re.compile(r"Name\s*:\s*([A-Z\s]+)")], "post_process": post_process_name},
            {"key": "payment_due_date", "patterns": [re.compile(r"Payment\s*due\s*by\s*([\d]{2}-[\w]{3}-[\d]{2})")], "post_process": post_process_date},
            {"key": "total_due", "patterns": [re.compile(r"Total\s*Payment\s*Due\s*Rs\.\s*([\d,]+\.\d{2})")], "post_process": post_process_amount},
            {"key": "gstin", "patterns": [GSTIN_PATTERN]}
        ]
    },
    "AXIS": {
        "issuer_keywords": ["AXIS BANK"],
        "extractors": [
            {"key": "cardholder_name", "patterns": [re.compile(r"PREPARED\s*FOR\s+([A-Z\s]+)")], "post_process": post_process_name},
            {"key": "payment_due_date", "patterns": [re.compile(r"PAYMENT\s*DUE\s*DATE\s*([\d]{2}-[\w]{3}-[\d]{4})")], "post_process": post_process_date},
            {"key": "total_due", "patterns": [re.compile(r"TOTAL\s*AMOUNT\s*DUE\s*₹\s*([\d,]+\.\d{2})")], "post_process": post_process_amount},
            {"key": "gstin", "patterns": [GSTIN_PATTERN]}
        ]
    },
    # Simplified configs for the rest
    "KOTAK": {"issuer_keywords": ["Kotak"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "AMEX": {"issuer_keywords": ["AMERICAN EXPRESS"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "CITI": {"issuer_keywords": ["citibank"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "RBL": {"issuer_keywords": ["RBL Bank"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "SC": {"issuer_keywords": ["Standard Chartered"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "BOB": {"issuer_keywords": ["Bank of Baroda"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]},
    "IDFC": {"issuer_keywords": ["IDFC"], "extractors": [{"key": "gstin", "patterns": [GSTIN_PATTERN]}]}
}

def parse_pdf_statement(file_bytes):
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2, layout=True)
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        return {"error": f"Failed to read PDF: {e}"}

    detected_issuer = "Unknown"
    for issuer_name, config in PARSER_CONFIG.items():
        for keyword in config["issuer_keywords"]:
            if re.search(keyword, text, re.IGNORECASE):
                detected_issuer = issuer_name
                break
        if detected_issuer != "Unknown":
            break
    
    if detected_issuer == "Unknown":
        return {"error": "Could not identify the bank from the statement."}

    extracted_data = {"issuer": detected_issuer}
    issuer_config = PARSER_CONFIG[detected_issuer]

    for extractor in issuer_config.get("extractors", []):
        key = extractor["key"]
        found_value = "N/A"
        
        for pattern in extractor["patterns"]:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                if "post_process" in extractor:
                    value = extractor["post_process"](value)
                found_value = value
                break
        
        extracted_data[key] = found_value

    # Ensure all 5 fields are present in the output, even if not found
    for key in ["cardholder_name", "payment_due_date", "total_due", "gstin"]:
        if key not in extracted_data:
            extracted_data[key] = "N/A"

    return extracted_data