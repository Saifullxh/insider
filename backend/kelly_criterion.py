from dataclasses import dataclass
from typing import Optional

@dataclass
class KellyResult:
    side: str                # "YES" or "NO"
    fraction: float          # Fraction of bankroll to risk
    bet_amount: float        # Dollar amount to stake
    expected_value: float    # Expected value of the bet
    edge: float              # p - price (YES) or (1-p) - (1-price)


def kelly_prediction_market(
    bankroll: float,
    market_price: float,             # Price of YES share (0–1)
    estimated_probability: float,    # Your p estimate (0–1)
    uncertainty: float = 0.03,       # Reduce p by uncertainty margin
    volatility_penalty: float = 0.85,# Reduce size based on exposure
    fractional_kelly: float = 0.5,   # Half Kelly by default
    max_fraction: float = 0.25       # Hard cap at 25%
) -> KellyResult:

    # Validate
    if not (0 < market_price < 1):
        return KellyResult("NONE", 0, 0, 0, 0)
    if not (0 < estimated_probability < 1):
        return KellyResult("NONE", 0, 0, 0, 0)

    # Apply Bayesian safety: reduce overconfidence
    p = max(min(estimated_probability - uncertainty, 0.99), 0.01)
    q = 1 - p
    price = market_price

    # Determine which side has edge
    edge_yes = p - price
    edge_no = (1 - p) - (1 - price)

    if edge_yes <= 0 and edge_no <= 0:
        return KellyResult("NONE", 0, 0, 0, max(edge_yes, edge_no))

    # YES side Kelly
    # Payoff: win = +1, lose = -price
    # b = (1-price) / price
    b_yes = (1 - price) / price
    f_yes = (b_yes * p - q) / b_yes

    # NO side Kelly
    # Short NO at price gives: win = +price, lose = -(1-price)
    b_no = price / (1 - price)
    f_no = (b_no * q - p) / b_no

    # Choose best side
    if edge_yes > edge_no:
        side = "YES"
        f = f_yes
        edge = edge_yes
        payoff_if_win = 1 - price
        payoff_if_lose = price
    else:
        side = "NO"
        f = f_no
        edge = edge_no
        payoff_if_win = price
        payoff_if_lose = 1 - price

    # Kelly cannot be negative
    f = max(f, 0)

    # Apply volatility penalty and fractional Kelly
    f *= volatility_penalty
    f *= fractional_kelly

    # Cap sizing
    f = min(f, max_fraction)

    bet_amount = round(bankroll * f, 2)

    # Expected value in dollars
    expected_value = round((p * payoff_if_win - q * payoff_if_lose) * bet_amount, 2)

    return KellyResult(
        side=side,
        fraction=round(f, 4),
        bet_amount=bet_amount,
        expected_value=expected_value,
        edge=round(edge, 4),
    )
