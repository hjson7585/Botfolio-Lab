from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai_logs_router import router as ai_logs_router
from app.routes.portfolio_router import router as portfolio_router  # ✅ 추가

api = FastAPI()

api.include_router(ai_logs_router)
api.include_router(portfolio_router)  # ✅ 추가

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
