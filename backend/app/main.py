"""
main.py — FastAPI application entry point.

No AI/LLM/ML APIs. No paid services.
Database: MongoDB (Atlas). Accounts use JWT tokens; every user's data is separate.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .routers import auth, expenses, summary, budgets, intents, preview, export, books, debts
from . import schemas

app = FastAPI(
    title="Monthly Budget Calculator",
    description=(
        "Rule-based expense tracker with per-user accounts. "
        "No AI/LLM — deterministic keyword + fuzzy matching."
    ),
    version="2.0.0",
)

# ── CORS — allow React Native / Expo to connect ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PyMongoError)
async def database_unavailable(request: Request, exc: PyMongoError):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable, please try again"})


# ── Register routers ──
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(debts.router)
app.include_router(expenses.router)
app.include_router(summary.router)
app.include_router(budgets.router)
app.include_router(intents.router)
app.include_router(preview.router)
app.include_router(export.router)


# ── Health check (does not touch the database) ──
@app.get("/api/health", response_model=schemas.HealthResponse, tags=["health"])
def health():
    return schemas.HealthResponse()
