from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.rag import generate_answer
import uuid
import os
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()  # ✅ this will load the .env file before anything else

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static folder at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))

class ChatInput(BaseModel):
    session_id: str = None
    query: str

@app.post("/chat")
def chat(input: ChatInput):
    session_id = input.session_id or str(uuid.uuid4())
    answer, sources = generate_answer(input.query, session_id)
    return {"session_id": session_id, "answer": answer, "sources": sources}