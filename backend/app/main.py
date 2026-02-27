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
def pick_best_american_price(outcomes: list[dict]) -> dict:
    """
    For American odds:
    - Higher number is better for the bettor.
      Example: +120 is better than +110; -105 is better than -110.
    """
    best = None
    for o in outcomes:
        price = o.get("price")
        if price is None:
            continue
        if best is None or price > best["price"]:
            best = {"name": o.get("name"), "price": price}
    return best


@app.get("/odds-clean/{sport_key}")
def odds_clean(sport_key: str):
    try:
        raw_games = fetch_odds(sport_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    cleaned = []

    for game in raw_games:
        game_id = game.get("id")
        home = game.get("home_team")
        away = game.get("away_team")
        commence = game.get("commence_time")

        best = {
            "h2h": {},       # moneyline best per team
            "spreads": {},   # best spread price per team
            "totals": {}     # best over/under price
        }

        for book in game.get("bookmakers", []):
            book_title = book.get("title")

            for market in book.get("markets", []):
                mkey = market.get("key")
                outcomes = market.get("outcomes", [])

                # MONEYLINE
                if mkey == "h2h":
                    for team in [home, away]:
                        team_outcomes = [o for o in outcomes if o.get("name") == team]
                        if not team_outcomes:
                            continue
                        candidate = pick_best_american_price(team_outcomes)
                        if not candidate:
                            continue

                        current = best["h2h"].get(team)
                        if current is None or candidate["price"] > current["price"]:
                            best["h2h"][team] = {
                                "price": candidate["price"],
                                "book": book_title
                            }

                # SPREADS
                elif mkey == "spreads":
                    for o in outcomes:
                        team = o.get("name")
                        point = o.get("point")
                        price = o.get("price")
                        if team not in [home, away] or price is None:
                            continue

                        key = f"{team} {point}"
                        current = best["spreads"].get(key)
                        if current is None or price > current["price"]:
                            best["spreads"][key] = {
                                "price": price,
                                "book": book_title
                            }

                # TOTALS
                elif mkey == "totals":
                    for o in outcomes:
                        name = o.get("name")  # "Over" or "Under"
                        point = o.get("point")
                        price = o.get("price")
                        if name not in ["Over", "Under"] or price is None:
                            continue

                        key = f"{name} {point}"
                        current = best["totals"].get(key)
                        if current is None or price > current["price"]:
                            best["totals"][key] = {
                                "price": price,
                                "book": book_title
                            }

        cleaned.append({
            "id": game_id,
            "sport_key": sport_key,
            "commence_time": commence,
            "home_team": home,
            "away_team": away,
            "best": best
        })

    return {"sport_key": sport_key, "games_returned": len(cleaned), "games": cleaned}
