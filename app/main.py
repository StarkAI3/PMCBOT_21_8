from fastapi import FastAPI
from pydantic import BaseModel
from app.rag import generate_answer
import uuid
from dotenv import load_dotenv
load_dotenv()  # ✅ this will load the .env file before anything else

import uuid
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static folder at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
def read_index():
    return FileResponse(os.path.join("static", "index.html"))


class ChatInput(BaseModel):
    session_id: str = None
    query: str

@app.post("/chat")
def chat(input: ChatInput):
    session_id = input.session_id or str(uuid.uuid4())
    answer, sources = generate_answer(input.query, session_id)
    return {"session_id": session_id, "answer": answer, "sources": sources}

from fastapi.responses import FileResponse
import os

@app.get("/")
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))