from fastapi import FastAPI

app = FastAPI(title="Quant Bets API")

@app.get("/")
def root():
    return {
        "message": "Quant Bets API is running 🚀",
        "version": "0.1.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
