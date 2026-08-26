import pandas as pd
import numpy as np

try:
    import ta
except ImportError:
    ta = None

class TradingStrategy:
    def __init__(self, rsi_period=14, rsi_oversold=30, rsi_overbought=70):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < 30:
            return {"signal": "HOLD", "reason": "Aguardando dados suficientes (mínimo 30 velas)", "rsi": 50, "ema9": 0, "ema21": 0}

        df = df.copy()
        
        # Cálculo de Médias Móveis Exponenciais (EMA 9 e EMA 21)
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        # Cálculo do RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        rsi_val = float(last_row["rsi"])
        ema9_val = float(last_row["ema9"])
        ema21_val = float(last_row["ema21"])
        close_val = float(last_row["close"])

        # Lógica de Cruzamento e IFR (RSI)
        bullish_cross = (prev_row["ema9"] <= prev_row["ema21"]) and (last_row["ema9"] > last_row["ema21"])
        bearish_cross = (prev_row["ema9"] >= prev_row["ema21"]) and (last_row["ema9"] < last_row["ema21"])

        signal = "HOLD"
        reason = "Aguardando oportunidade técnica clara"

        if bullish_cross or (rsi_val < self.rsi_oversold and close_val > ema9_val):
            signal = "BUY"
            reason = f"Cruzamento de Alta (EMA9={ema9_val:.2f} > EMA21={ema21_val:.2f}) e RSI={rsi_val:.1f}"
        elif bearish_cross or (rsi_val > self.rsi_overbought and close_val < ema9_val):
            signal = "SELL"
            reason = f"Cruzamento de Baixa (EMA9={ema9_val:.2f} < EMA21={ema21_val:.2f}) e RSI={rsi_val:.1f}"

        return {
            "signal": signal,
            "reason": reason,
            "rsi": rsi_val,
            "ema9": ema9_val,
            "ema21": ema21_val,
            "price": close_val
        }
