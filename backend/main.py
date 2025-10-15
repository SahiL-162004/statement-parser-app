# backend/main.py

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from parser_service import parse_pdf_statement
from ml_parser_service import parse_with_ml
from models import ChatRequest
import uuid
import pdfplumber
import io
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_CACHE = {}

def extract_text_from_bytes(file_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2)
                if page_text:
                    text += page_text + "\n"
    except Exception:
        return ""
    return text

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    content = await file.read()
    data = parse_pdf_statement(content)
    if "error" in data:
        return {"status": "error", "message": data["error"]}
    full_text = extract_text_from_bytes(content)
    session_id = str(uuid.uuid4())
    PDF_CACHE[session_id] = {"text": full_text, "data": data}
    return {"status": "success", "data": data, "session_id": session_id}

@app.post("/api/upload-ml")
async def upload_pdf_ml(file: UploadFile = File(...)):
    content = await file.read()
    data = parse_with_ml(content)
    if "error" in data:
        return {"status": "error", "message": data["error"]}
    full_text = extract_text_from_bytes(content)
    session_id = str(uuid.uuid4())
    PDF_CACHE[session_id] = {"text": full_text, "data": data}
    return {"status": "success", "data": data, "session_id": session_id}

@app.post("/api/chat")
async def chat_with_document(request: ChatRequest):
    session_data = PDF_CACHE.get(request.session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload again.")

    prompt_lower = request.prompt.lower()
    
    if "summary" in prompt_lower or "summarise" in prompt_lower:
        parsed_data = session_data.get("data", {})
        if not parsed_data:
            return {"response": "No summary data was found. Try parsing the document again."}
        summary_lines = ["Here is a summary of the document:"]
        for key, value in parsed_data.items():
            display_key = key.replace('_', ' ').title()
            summary_lines.append(f"- **{display_key}:** {value}")
        return {"response": "\n".join(summary_lines)}

    else:
        full_text = session_data.get("text", "")
        if not full_text:
            return {"response": "Could not retrieve document text."}

        # --- NEW AI-POWERED RELEVANCY SEARCH (TF-IDF) ---
        try:
            # 1. Split text into sentences
            sentences = re.split(r'(?<=[.?!])\s+', full_text.replace('\n', ' '))
            if len(sentences) < 2: # Handle case with very short text
                sentences = full_text.split()

            # 2. Create TF-IDF vectors
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # 3. Vectorize the user's question
            prompt_vector = vectorizer.transform([request.prompt])
            
            # 4. Calculate similarity
            cosine_similarities = cosine_similarity(prompt_vector, tfidf_matrix).flatten()
            
            # 5. Find the most similar sentence
            most_similar_sentence_index = cosine_similarities.argmax()
            
            # Check if the similarity is above a certain threshold
            if cosine_similarities[most_similar_sentence_index] > 0.1:
                return {"response": sentences[most_similar_sentence_index]}
            else:
                return {"response": "Sorry, I couldn't find a relevant answer in the document."}

        except Exception as e:
            return {"response": f"An error occurred during AI processing: {e}"}