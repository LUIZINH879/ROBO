def calculate_ema(prices, span):
    if len(prices) < span:
        return prices[-1] if prices else 0.0
    alpha = 2.0 / (span + 1.0)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * alpha + ema * (1.0 - alpha)
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))
            
    recent_gains = gains[-period:]
    recent_losses = losses[-period:]
    
    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

class TradingStrategy:
    def __init__(self, rsi_period=14, rsi_oversold=30.0, rsi_overbought=70.0):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def analyze(self, candles):
        # candles é uma lista de [timestamp, open, high, low, close, volume]
        if len(candles) < 25:
            return {
                "signal": "HOLD",
                "reason": "Aguardando mais velas de histórico (mínimo 25)",
                "rsi": 50.0,
                "ema9": 0.0,
                "ema21": 0.0,
                "price": candles[-1][4] if candles else 0.0
            }

        closes = [c[4] for c in candles]
        current_price = closes[-1]

        # Médias Móveis Exponenciais
        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)

        # Média anterior para verificar cruzamento
        prev_closes = closes[:-1]
        prev_ema9 = calculate_ema(prev_closes, 9)
        prev_ema21 = calculate_ema(prev_closes, 21)

        # RSI (IFR)
        rsi = calculate_rsi(closes, self.rsi_period)

        bullish_cross = (prev_ema9 <= prev_ema21) and (ema9 > ema21)
        bearish_cross = (prev_ema9 >= prev_ema21) and (ema9 < ema21)

        signal = "HOLD"
        reason = "Aguardando oportunidade técnica"

        if bullish_cross or (rsi < self.rsi_oversold and current_price > ema9):
            signal = "BUY"
            reason = f"Sinal de Alta (EMA9={ema9:.2f} > EMA21={ema21:.2f} | RSI={rsi:.1f})"
        elif bearish_cross or (rsi > self.rsi_overbought and current_price < ema9):
            signal = "SELL"
            reason = f"Sinal de Baixa (EMA9={ema9:.2f} < EMA21={ema21:.2f} | RSI={rsi:.1f})"

        return {
            "signal": signal,
            "reason": reason,
            "rsi": rsi,
            "ema9": ema9,
            "ema21": ema21,
            "price": current_price
        }
