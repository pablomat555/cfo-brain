from fastapi import FastAPI
from loguru import logger

from core.database import init_db
from api.routers import ingest, report, observer, capital, verdict

app = FastAPI(title="CFO Brain API", version="0.1.0")

# Включаем роутеры
app.include_router(ingest.router)
app.include_router(report.router)
app.include_router(observer.router)
app.include_router(capital.router)
app.include_router(verdict.router)


@app.on_event("startup")
def on_startup():
    """Инициализация при запуске"""
    logger.info("Starting CFO Brain API")
    init_db()
    logger.info("Database initialized")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)