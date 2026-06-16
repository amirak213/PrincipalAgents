from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import uuid
from chatbot.chat import chat
from googletrans import Translator
from langdetect import detect, DetectorFactory

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Initialize translator
translator = Translator()

app = FastAPI(title="Dourbia Chatbot API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store session contexts
sessions = {}

# Translation utility functions
def detect_language(text: str) -> str:
    """Detect the language of the input text"""
    try:
        lang = detect(text)
        return lang
    except:
        return "fr"  # Default to French if detection fails

def translate_to_french(text: str, source_lang: str) -> str:
    """Translate text to French"""
    if source_lang == "fr":
        return text
    try:
        translation = translator.translate(text, src_language=source_lang, dest_language="fr")
        return translation['text']
    except:
        return text  # Return original if translation fails

def translate_from_french(text: str, target_lang: str) -> str:
    """Translate text from French to target language"""
    if target_lang == "fr":
        return text
    try:
        translation = translator.translate(text, src_language="fr", dest_language=target_lang)
        return translation['text']
    except:
        return text  # Return original if translation fails

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None  # User's language (auto-detected if not provided)

class ChatResponse(BaseModel):
    response: str
    session_id: str
    detected_language: str  # Language detected from input

class SessionResponse(BaseModel):
    session_id: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        message = request.message
        session_id = request.session_id
        
        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = True
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Detect the language of the input message
        detected_language = request.language if request.language else detect_language(message)
        
        print(f"[Dourbia] Detected language: {detected_language}")
        
        # Translate the message to French for the chatbot
        message_fr = translate_to_french(message, detected_language)
        print(f"[Dourbia] Original message: {message}")
        print(f"[Dourbia] Translated to FR: {message_fr}")
        
        # Run the async chat function with French message
        response_fr = await chat(session_id, message_fr)
        
        # Translate the response back to the user's language
        response = translate_from_french(response_fr, detected_language)
        print(f"[Dourbia] Response in FR: {response_fr}")
        print(f"[Dourbia] Response translated to {detected_language}: {response}")
        
        return ChatResponse(
            response=response, 
            session_id=session_id,
            detected_language=detected_language
        )
    
    except Exception as e:
        print(f"[Dourbia] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = True
    return SessionResponse(session_id=session_id)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Dourbia Chatbot API"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
