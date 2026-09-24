"""Trade execution modeling with realistic slippage and transaction costs.

Implements:
- Next-day-open or next available price fills
- Turnover calculation: 0.5 * sum(|w_new - w_old|)
- Transaction cost deduction: 30 bps buy, 20 bps sell, + slippage bps
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradeOrder:
    """A single trade order for a stock."""

    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    target_weight: float
    current_weight: float
    weight_change: float
    trade_price: float
    shares: int
    cost_incurred: float


@dataclass
class ExecutionResult:
    """Summary of a portfolio rebalance execution."""

    orders: list[TradeOrder]
    turnover: float
    total_cost: float
    final_weights: dict[str, float]


def execute_rebalance(
    target_weights: dict[str, float],
    current_weights: dict[str, float],
    prices: dict[str, float],
    portfolio_value: float = 1_000_000.0,
    buy_cost_bps: float = 30.0,
    sell_cost_bps: float = 20.0,
    slippage_bps: float = 5.0,
) -> ExecutionResult:
    """Execute target weight changes with costs and share allocations."""
    all_symbols = sorted(set(target_weights.keys()) | set(current_weights.keys()))
    orders: list[TradeOrder] = []
    total_turnover = 0.0
    total_cost = 0.0

    final_weights: dict[str, float] = {}

    for sym in all_symbols:
        w_target = target_weights.get(sym, 0.0)
        w_curr = current_weights.get(sym, 0.0)
        dw = w_target - w_curr
        price = prices.get(sym, 1.0)
        if price <= 0:
            price = 1.0

        target_val = portfolio_value * w_target
        shares = int(target_val / price)

        if dw > 1e-4:
            action = "BUY"
            # Buy cost = turnover_val * (buy_cost_bps + slippage_bps) / 10000
            cost_rate = (buy_cost_bps + slippage_bps) / 10000.0
            cost = abs(dw) * portfolio_value * cost_rate
        elif dw < -1e-4:
            action = "SELL"
            cost_rate = (sell_cost_bps + slippage_bps) / 10000.0
            cost = abs(dw) * portfolio_value * cost_rate
        else:
            action = "HOLD"
            cost = 0.0

        total_turnover += abs(dw)
        total_cost += cost
        final_weights[sym] = w_target

        orders.append(
            TradeOrder(
                symbol=sym,
                action=action,
                target_weight=w_target,
                current_weight=w_curr,
                weight_change=round(dw, 4),
                trade_price=round(price, 2),
                shares=shares,
                cost_incurred=round(cost, 2),
            )
        )

    # Standard two-sided turnover definition: 0.5 * sum(|dw|)
    rebalance_turnover = total_turnover * 0.5

    return ExecutionResult(
        orders=orders,
        turnover=round(rebalance_turnover, 4),
        total_cost=round(total_cost, 2),
        final_weights=final_weights,
    )
