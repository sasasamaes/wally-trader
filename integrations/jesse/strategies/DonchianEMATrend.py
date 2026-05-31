"""
DonchianEMATrend — port fiel de la estrategia del video
"Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot" (Algo-trading with Saleh).

Trend-following: Donchian breakout + filtro de tendencia EMA, long-only.
  - Entrada LONG: close rompe el high del Donchian previo Y close > EMA(tendencia).
  - SL: entry - ATR * sl_atr_mult.
  - Sizing: utils.risk_to_qty con risk_pct% del margen disponible.
  - Salida: estructural cuando el close cae por debajo de la banda baja del Donchian.

Long-only a propósito: como advierte el video, un long-only trend follower BRILLA en un
uptrend limpio (2024) y se CAE en chop/downtrend (2025). Eso es feature, no bug — el punto
es ver el comportamiento honesto across regímenes con OOS + Monte Carlo antes de ir live.

Copia este archivo a la carpeta `strategies/` de tu proyecto Jesse.
"""
from jesse.strategies import Strategy
from jesse import ta, utils


class DonchianEMATrend(Strategy):

    def hyperparameters(self):
        return [
            {"name": "don_len", "type": int, "min": 10, "max": 50, "default": 20},
            {"name": "ema_len", "type": int, "min": 50, "max": 300, "default": 200},
            {"name": "atr_len", "type": int, "min": 7, "max": 28, "default": 14},
            {"name": "sl_atr_mult", "type": float, "min": 1.0, "max": 4.0, "default": 2.0},
            {"name": "risk_pct", "type": float, "min": 0.5, "max": 3.0, "default": 2.0},
        ]

    # ── indicadores ──
    @property
    def donchian(self):
        return ta.donchian(self.candles, period=self.hp["don_len"], sequential=False)

    @property
    def trend_ema(self):
        return ta.ema(self.candles, period=self.hp["ema_len"], sequential=False)

    @property
    def atr(self):
        return ta.atr(self.candles, period=self.hp["atr_len"], sequential=False)

    # ── reglas de entrada ──
    def should_long(self) -> bool:
        return self.close > self.donchian.upperband and self.close > self.trend_ema

    def should_short(self) -> bool:
        return False  # long-only (ver caveat del video sobre shorts en bull year)

    def should_cancel_entry(self) -> bool:
        return True

    # ── ejecución ──
    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp["sl_atr_mult"]
        qty = utils.risk_to_qty(
            self.available_margin, self.hp["risk_pct"], entry, stop,
            fee_rate=self.fee_rate,
        )
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        pass

    # ── gestión de posición ──
    def update_position(self):
        # salida estructural: close por debajo de la banda baja del Donchian
        if self.is_long and self.close < self.donchian.lowerband:
            self.liquidate()
