from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
from chatbot.chat import chat

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

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

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
        
        # Run the async chat function
        response = await chat(session_id, message)
        
        return ChatResponse(response=response, session_id=session_id)
    
    except Exception as e:
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
