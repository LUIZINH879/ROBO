#!/usr/bin/env python3
"""
===================================================================
 🤖 ROBÔ DE TRADING INTELIGENTE - CRIPTOMOEDAS (TERMUX / MOBILE)
 100% Python Nativo - Zero dependências externas (Sem erros de C++)
===================================================================
"""

import os
import sys
import time
import json
import hmac
import hashlib
import urllib.request
import urllib.error
import urllib.parse
import argparse
from datetime import datetime

# Leitor automático de .env nativo
def load_env():
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

load_env()

API_KEY = os.getenv("CCXT_API_KEY", "")
API_SECRET = os.getenv("CCXT_SECRET", "")
MAX_POSITION = float(os.getenv("MAX_POSITION", "0.00005"))

# ==========================================
# CÁLCULOS MATEMÁTICOS DE INDICADORES (NATIVO)
# ==========================================
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

# ==========================================
# CLIENTE NATIVO DA BINANCE
# ==========================================
class BinanceClient:
    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key="", api_secret=""):
        self.api_key = api_key
        self.api_secret = api_secret

    def get_klines(self, symbol="BTCUSDT", interval="1m", limit=50):
        clean_symbol = symbol.replace("/", "").upper()
        url = f"{self.BASE_URL}/api/v3/klines?symbol={clean_symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Binance-Termux-Bot"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                # Estrutura: [ [time, open, high, low, close, volume, ...], ... ]
                candles = []
                for c in data:
                    candles.append({
                        "time": c[0],
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5])
                    })
                return candles
        except Exception as e:
            return []

    def create_order(self, symbol="BTCUSDT", side="BUY", quantity=0.00005):
        if not self.api_key or not self.api_secret:
            raise ValueError("Chaves de API não configuradas no .env!")

        clean_symbol = symbol.replace("/", "").upper()
        ts = int(time.time() * 1000)
        params = {
            "symbol": clean_symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": f"{quantity:.5f}",
            "timestamp": ts
        }
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        url = f"{self.BASE_URL}/api/v3/order?{query_string}&signature={signature}"
        req = urllib.request.Request(
            url,
            data=b"",
            headers={
                "X-MBX-APIKEY": self.api_key,
                "User-Agent": "Binance-Termux-Bot"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

# ==========================================
# MOTOR DO ROBÔ
# ==========================================
class TradingBot:
    def __init__(self, symbol="BTC/USDT", timeframe="1m", mode="paper"):
        self.symbol = symbol
        self.clean_symbol = symbol.replace("/", "").upper()
        self.timeframe = timeframe
        self.mode = mode.lower()
        self.client = BinanceClient(API_KEY, API_SECRET)
        
        self.in_position = False
        self.entry_price = 0.0
        self.trade_count = 0

    def analyze(self, candles):
        if len(candles) < 25:
            return {"signal": "HOLD", "reason": "Sincronizando velas...", "rsi": 50, "ema9": 0, "ema21": 0, "price": 0}

        closes = [c["close"] for c in candles]
        current_price = closes[-1]

        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)

        prev_closes = closes[:-1]
        prev_ema9 = calculate_ema(prev_closes, 9)
        prev_ema21 = calculate_ema(prev_closes, 21)

        rsi = calculate_rsi(closes, 14)

        bullish_cross = (prev_ema9 <= prev_ema21) and (ema9 > ema21)
        bearish_cross = (prev_ema9 >= prev_ema21) and (ema9 < ema21)

        signal = "HOLD"
        reason = "Monitorando mercado..."

        if bullish_cross or (rsi < 30.0 and current_price > ema9):
            signal = "BUY"
            reason = f"Cruzamento de Alta (EMA9={ema9:.2f} > EMA21={ema21:.2f} | RSI={rsi:.1f})"
        elif bearish_cross or (rsi > 70.0 and current_price < ema9):
            signal = "SELL"
            reason = f"Cruzamento de Baixa (EMA9={ema9:.2f} < EMA21={ema21:.2f} | RSI={rsi:.1f})"

        return {
            "signal": signal,
            "reason": reason,
            "rsi": rsi,
            "ema9": ema9,
            "ema21": ema21,
            "price": current_price
        }

    def execute_trade(self, action, price, reason):
        now_str = datetime.now().strftime("%H:%M:%S")
        base_asset = self.symbol.split("/")[0]

        if self.mode == "paper":
            if action == "BUY" and not self.in_position:
                self.in_position = True
                self.entry_price = price
                self.trade_count += 1
                print(f"\n🟢 [{now_str}] [SIMULAÇÃO - COMPRA EXECUTADA]")
                print(f"   Preço Entrada: ${price:,.2f}")
                print(f"   Motivo: {reason}")
                print(f"   Posição: {MAX_POSITION} {base_asset} (~R$ 5,00)\n")
            elif action == "SELL" and self.in_position:
                pnl_pct = ((price - self.entry_price) / self.entry_price) * 100
                pnl_val = (price - self.entry_price) * MAX_POSITION
                self.in_position = False
                self.entry_price = 0.0
                resultado = "🟢 LUCRO" if pnl_pct >= 0 else "🔴 PREJUÍZO"
                print(f"\n🔴 [{now_str}] [SIMULAÇÃO - VENDA EXECUTADA]")
                print(f"   Preço Saída: ${price:,.2f}")
                print(f"   Motivo: {reason}")
                print(f"   Resultado: {resultado} de {pnl_pct:+.2f}% (${pnl_val:+.4f})\n")
        else:
            # MODO REAL
            try:
                if action == "BUY" and not self.in_position:
                    order = self.client.create_order(self.clean_symbol, "BUY", MAX_POSITION)
                    self.in_position = True
                    self.entry_price = price
                    print(f"\n🟢 [{now_str}] [ORDEM REAL EXECUTADA - COMPRA] ID: {order.get('orderId')} Preço: ${price:,.2f}\n")
                elif action == "SELL" and self.in_position:
                    order = self.client.create_order(self.clean_symbol, "SELL", MAX_POSITION)
                    self.in_position = False
                    self.entry_price = 0.0
                    print(f"\n🔴 [{now_str}] [ORDEM REAL EXECUTADA - VENDA] ID: {order.get('orderId')} Preço: ${price:,.2f}\n")
            except Exception as e:
                print(f"\n❌ [ERRO NA CORRETORA] {e}\n")

    def run(self):
        base_asset = self.symbol.split("/")[0]
        mode_label = "🟢 SIMULAÇÃO (PAPER TRADING)" if self.mode == "paper" else "🚨 MODO REAL (LIVE TRADING)"
        
        print(f"\n======================================================")
        print(f"  🤖 ROBÔ DE TRADING INTELIGENTE - TERMUX MOBILE 🚀")
        print(f"======================================================")
        print(f"  Par: {self.symbol} | Tempo Gráfico: {self.timeframe}")
        print(f"  Modo: {mode_label}")
        print(f"  Gestão de Risco: {MAX_POSITION} {base_asset} (~R$ 5,00)")
        print(f"======================================================\n")
        print("🔍 Conectando diretamente à Binance e analisando mercado...")

        while True:
            try:
                candles = self.client.get_klines(symbol=self.clean_symbol, interval=self.timeframe, limit=50)
                if candles and len(candles) >= 25:
                    analysis = self.analyze(candles)
                    price = analysis["price"]
                    rsi = analysis["rsi"]
                    ema9 = analysis["ema9"]
                    ema21 = analysis["ema21"]
                    signal = analysis["signal"]
                    reason = analysis["reason"]

                    now = datetime.now().strftime("%H:%M:%S")
                    status_pos = f"EM POSIÇÃO (${self.entry_price:,.2f})" if self.in_position else "AGUARDANDO SINAL"
                    print(f"[{now}] Preço: ${price:,.2f} | RSI: {rsi:.1f} | EMA(9/21): {ema9:.1f}/{ema21:.1f} | Sinal: {signal} | Status: {status_pos}")

                    # Gestão de Stop-Loss e Take-Profit automático
                    if self.in_position:
                        pnl_pct = ((price - self.entry_price) / self.entry_price) * 100
                        if pnl_pct <= -1.5:
                            self.execute_trade("SELL", price, "STOP LOSS acionado (-1.5%)")
                        elif pnl_pct >= 2.5:
                            self.execute_trade("SELL", price, "TAKE PROFIT acionado (+2.5%)")
                        elif signal == "SELL":
                            self.execute_trade("SELL", price, reason)
                    else:
                        if signal == "BUY":
                            self.execute_trade("BUY", price, reason)

                time.sleep(3)  # Atualiza a cada 3 segundos
            except KeyboardInterrupt:
                print("\n🛑 Robô finalizado com sucesso.")
                break
            except Exception as e:
                print(f"Erro momentâneo: {e}")
                time.sleep(3)

def main():
    parser = argparse.ArgumentParser(description="Robô de Trading de Criptomoedas")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Par de negociação (Ex: BTC/USDT)")
    parser.add_argument("--timeframe", type=str, default="1m", help="Tempo gráfico (Ex: 1m, 5m, 15m)")
    parser.add_argument("--mode", type=str, default="paper", choices=["paper", "live"], help="Modo: paper ou live")

    args = parser.parse_args()
    bot = TradingBot(symbol=args.symbol, timeframe=args.timeframe, mode=args.mode)
    bot.run()

if __name__ == "__main__":
    main()
