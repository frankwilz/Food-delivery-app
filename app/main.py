from fastapi import FastAPI

from app.api.routes import restaurants

app = FastAPI(title="Food Delivery API")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(restaurants.router)