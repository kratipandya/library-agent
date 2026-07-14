"""Local HTTP API for the library chatbot — the pre-Azure dress rehearsal.

Wraps the orchestrator in FastAPI. The browser (or curl) POSTs a message and
a session_id; the thread for each session carries conversation state between
requests. Sessions live in process memory — fine for local dev, replaced by
Cosmos DB chat history in Phase 4.

Run:
    uv run uvicorn api.app:app --reload
Then:
    curl -X POST localhost:8000/chat -H 'content-type: application/json' \
         -d '{"message": "When was Dracula published?", "session_id": "demo"}'
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from semantic_kernel.agents import ChatHistoryAgentThread

from agents.llm import get_model_id, invoke_with_retry
from agents.orchestrator import build_orchestrator

app = FastAPI(title="Library Agent API")

# CORS: the browser blocks cross-origin calls unless the API allows them.
# The frontend dev server (and later the Static Web App) is a different
# origin than this API, so without this header no browser request arrives.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["content-type"],
)

orchestrator = build_orchestrator()
sessions: dict[str, ChatHistoryAgentThread] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": get_model_id()}


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    thread = sessions.get(request.session_id)
    response = await invoke_with_retry(
        lambda: orchestrator.get_response(messages=request.message, thread=thread)
    )
    sessions[request.session_id] = response.thread
    return ChatResponse(reply=str(response.message.content), session_id=request.session_id)
