from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.app.services.odds_fetcher import fetch_odds

app = FastAPI(title="Quant Bets API")


# ---- Request Model ----
class BetRequest(BaseModel):
    american_odds: int
    true_probability: float  # Your model probability (0-1)


# ---- Helper Function ----
def american_to_implied_probability(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


# ---- Root ----
@app.get("/")
def root():
    return {"message": "Quant Bets API is running 🚀"}


# ---- Edge Calculator ----
@app.post("/calculate-edge")
def calculate_edge(bet: BetRequest):
    implied_prob = american_to_implied_probability(bet.american_odds)
    edge = bet.true_probability - implied_prob

    return {
        "american_odds": bet.american_odds,
        "implied_probability": round(implied_prob, 4),
        "true_probability": bet.true_probability,
        "edge": round(edge, 4),
        "is_positive_ev": edge > 0
    }
