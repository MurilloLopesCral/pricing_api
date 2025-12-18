from fastapi import FastAPI

from analytics.routes import router as analytics_router
from clients.routes import router as clients_router
from segments.routes import router as segments_router

app = FastAPI(title="Pricing Analytics API", version="1.1.0")

app.include_router(analytics_router, prefix="/analytics")
app.include_router(segments_router, prefix="/segments")
app.include_router(clients_router, prefix="/clients")


@app.get("/health")
def health():
    return {"ok": True}
