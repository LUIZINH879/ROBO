import pandas as pd

class DataValidationError(Exception):
    pass

def validate_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if df is None or df.empty:
        raise DataValidationError("DataFrame OHLCV vazio.")
    
    required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in df.columns:
            raise DataValidationError(f"Coluna obrigatória ausente: {col}")
            
    df = df.sort_values("timestamp").reset_index(drop=True)
    df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    return df
