#!/usr/bin/env python3
"""
ROBÔ DE TRADING INTELIGENTE PARA CRIPTOMOEDAS
Otimizado para execução em Celular (Termux) e Servidores.
"""

import sys
import os
import time
import argparse
import asyncio
from datetime import datetime
import pandas as pd

from config.settings import (
    CCXT_EXCHANGE,
    CCXT_API_KEY,
    CCXT_SECRET,
    MAX_POSITION,
    MAX_DRAWDOWN
)
from utils.logger import logger
from decision.strategy import TradingStrategy

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("[ERRO] ccxt nao esta instalado. Execute: pip install ccxt")
    sys.exit(1)

BANNER = """
======================================================
  🤖 ROBÔ DE TRADING INTELIGENTE - CRIPTO (TERMUX) 🚀
======================================================
  Ativo: {symbol} | Tempo Gráfico: {timeframe}
  Modo: {mode_label}
  Gestão de Risco: ~R$ 5,00 por operação ({max_pos} {base_curr})
======================================================
"""

class TradingBot:
    def __init__(self, symbol: str, timeframe: str, mode: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.mode = mode.lower()
        self.strategy = TradingStrategy()
        
        # Configuração do CCXT
        exchange_class = getattr(ccxt, CCXT_EXCHANGE.lower(), ccxt.binance)
        self.exchange = exchange_class({
            "apiKey": CCXT_API_KEY,
            "secret": CCXT_SECRET,
            "enableRateLimit": True,
        })
        
        # Estado do Robô
        self.in_position = False
        self.entry_price = 0.0
        self.virtual_balance = 50.0  # R$ 50 virtual para simulação
        self.trade_count = 0
        self.candles_history = []

    async def fetch_candles(self, limit: int = 60) -> pd.DataFrame:
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            logger.warning(f"Erro ao buscar velas da corretora: {e}")
            return pd.DataFrame()

    async def execute_trade(self, action: str, price: float, reason: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        if self.mode == "paper":
            if action == "BUY" and not self.in_position:
                self.in_position = True
                self.entry_price = price
                self.trade_count += 1
                print(f"\n🟢 [{now_str}] [SIMULAÇÃO - COMPRA] Preço: ${price:,.2f} | Motivo: {reason}")
                print(f"💰 Posição Aberta: {MAX_POSITION} {self.symbol.split('/')[0]} (~R$ 5,00)\n")
            elif action == "SELL" and self.in_position:
                pnl_pct = ((price - self.entry_price) / self.entry_price) * 100
                pnl_val = (price - self.entry_price) * MAX_POSITION
                self.in_position = False
                self.entry_price = 0.0
                print(f"\n🔴 [{now_str}] [SIMULAÇÃO - VENDA] Preço: ${price:,.2f} | Motivo: {reason}")
                lucro_cor = "🟢 Lucro" if pnl_pct >= 0 else "🔴 Prejuízo"
                print(f"📊 Resultado: {lucro_cor} de {pnl_pct:+.2f}% (${pnl_val:+.4f})\n")
        else:
            # MODO REAL (LIVE)
            if not CCXT_API_KEY or not CCXT_SECRET:
                print("\n❌ [ERRO CRÍTICO] Chaves de API não configuradas no .env para modo LIVE!")
                return
            try:
                if action == "BUY" and not self.in_position:
                    order = await self.exchange.create_market_buy_order(self.symbol, MAX_POSITION)
                    self.in_position = True
                    self.entry_price = price
                    print(f"\n🟢 [{now_str}] [ORDEM REAL EXECUTADA - COMPRA] ID: {order.get('id')} Preço: ${price:,.2f}")
                elif action == "SELL" and self.in_position:
                    order = await self.exchange.create_market_sell_order(self.symbol, MAX_POSITION)
                    self.in_position = False
                    self.entry_price = 0.0
                    print(f"\n🔴 [{now_str}] [ORDEM REAL EXECUTADA - VENDA] ID: {order.get('id')} Preço: ${price:,.2f}")
            except Exception as e:
                logger.error(f"Falha ao enviar ordem para a Binance: {e}")

    async def run(self):
        base_curr = self.symbol.split('/')[0]
        mode_label = "🟢 SIMULAÇÃO (PAPER TRADING)" if self.mode == "paper" else "🚨 MODO REAL (LIVE TRADING)"
        print(BANNER.format(
            symbol=self.symbol,
            timeframe=self.timeframe,
            mode_label=mode_label,
            max_pos=MAX_POSITION,
            base_curr=base_curr
        ))

        print("🔍 Analisando mercado e sincronizando histórico de preços...")
        
        while True:
            try:
                df = await self.fetch_candles(limit=60)
                if not df.empty and len(df) >= 25:
                    analysis = self.strategy.analyze(df)
                    price = analysis["price"]
                    rsi = analysis["rsi"]
                    ema9 = analysis["ema9"]
                    ema21 = analysis["ema21"]
                    signal = analysis["signal"]
                    reason = analysis["reason"]

                    now = datetime.now().strftime("%H:%M:%S")
                    status_pos = f"EM OPERAÇÃO (${self.entry_price:,.2f})" if self.in_position else "AGUARDANDO SINAL"
                    print(f"[{now}] Preço: ${price:,.2f} | RSI: {rsi:.1f} | EMA(9/21): {ema9:.1f}/{ema21:.1f} | Sinal: {signal} | Status: {status_pos}")

                    # Gestão de Stop-Loss e Take-Profit automático se estiver posicionado
                    if self.in_position:
                        pnl_pct = ((price - self.entry_price) / self.entry_price) * 100
                        if pnl_pct <= -1.5:  # Stop Loss de 1.5%
                            await self.execute_trade("SELL", price, "STOP LOSS acionado (-1.5%)")
                        elif pnl_pct >= 2.5: # Take Profit de 2.5%
                            await self.execute_trade("SELL", price, "TAKE PROFIT acionado (+2.5%)")
                        elif signal == "SELL":
                            await self.execute_trade("SELL", price, reason)
                    else:
                        if signal == "BUY":
                            await self.execute_trade("BUY", price, reason)

                await asyncio.sleep(5)  # Checa a cada 5 segundos
            except KeyboardInterrupt:
                print("\n🛑 Robô finalizado pelo usuário.")
                break
            except Exception as e:
                logger.error(f"Erro no loop de análise: {e}")
                await asyncio.sleep(5)

        await self.exchange.close()

def main():
    parser = argparse.ArgumentParser(description="Robô de Trading de Criptomoedas")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Par de negociação (Ex: BTC/USDT)")
    parser.add_argument("--timeframe", type=str, default="1m", help="Tempo gráfico (Ex: 1m, 5m, 15m)")
    parser.add_argument("--mode", type=str, default="paper", choices=["paper", "live"], help="Modo: paper (simulação) ou live (real)")

    args = parser.parse_args()
    bot = TradingBot(symbol=args.symbol, timeframe=args.timeframe, mode=args.mode)
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()
