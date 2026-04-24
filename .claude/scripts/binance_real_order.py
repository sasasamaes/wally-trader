"""Binance Futures real order submission — STUB v1.

In v1.0 this module is a stub that documents the interface and returns
NotImplementedError. Full implementation in v4 per spec rollout.
"""
from __future__ import annotations


class BinanceRealOrderStub(NotImplementedError):
    pass


def submit_limit_order(
    symbol: str, side: str, qty: float, price: float,
    sl: float, tp: float,
) -> str:
    raise BinanceRealOrderStub(
        "--real not implemented in v1. See docs/superpowers/specs/"
        "2026-04-24-watcher-pending-orders-design.md §Plan de rollout."
    )


def cancel_order(order_id: str) -> None:
    raise BinanceRealOrderStub("cancel_order not implemented in v1")


def get_order_status(order_id: str) -> dict:
    raise BinanceRealOrderStub("get_order_status not implemented in v1")
