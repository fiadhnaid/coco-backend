from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models.session import SessionCreate, SessionResponse, FinishResponse
from app.api import routes


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    @app.get("/")
    async def root():
        return {"status": f"{settings.APP_NAME} running (OpenAI mode)"}

    @app.post("/session", response_model=SessionResponse)
    async def create_session(session_data: SessionCreate):
        """Create a new conversation session"""
        return await routes.create_session(session_data)

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for live audio streaming"""
        await routes.websocket_handler(websocket, session_id)

    @app.post("/session/{session_id}/finish", response_model=FinishResponse)
    async def finish_session(session_id: str):
        """End session and generate summary"""
        return await routes.finish_session(session_id)

    return app


app = create_app()
