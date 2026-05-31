"""
_TEMPLATE — esqueleto en blanco de una estrategia Jesse.

Copia este archivo, renómbralo (la CLASE debe coincidir con el nombre del archivo) y rellena
las reglas. Docs: https://docs.jesse.trade/docs/strategies

Flujo de validación antes de confiar en una estrategia (gate del video):
  1. /rst         — ¿la entrada tiene edge?  (o tools de robustez de Jesse)
  2. backtest     — año completo
  3. OOS          — otros años (2023/2025)
  4. /montecarlo  — reshuffle de trades + candles sintéticos
  5. veredicto honesto
"""
from jesse.strategies import Strategy
from jesse import ta, utils


class _TEMPLATE(Strategy):

    def hyperparameters(self):
        return [
            # {"name": "param", "type": int, "min": 1, "max": 100, "default": 14},
        ]

    def should_long(self) -> bool:
        return False

    def should_short(self) -> bool:
        return False

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry * 0.98  # define tu SL
        qty = utils.risk_to_qty(self.available_margin, 2.0, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        pass

    def update_position(self):
        pass
