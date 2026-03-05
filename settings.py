# settings.py
import os
from config_manager import load_config

user_settings = load_config()

class Config:
    # --- DYNAMISCHE MT5 ZUGANGSDATEN ---
    # Wandelt den String aus der JSON sicher in einen Integer für MT5 um
    MT5_LOGIN = int(user_settings.get("mt5_account_number", 0)) if user_settings.get("mt5_account_number") else 0
    MT5_PASSWORD = user_settings.get("mt5_password", "")
    MT5_SERVER = user_settings.get("mt5_server", "")

    # --- TRADING CONFIG ---

    SYMBOLS = user_settings.get("symbols", ["EURUSD", "GBPUSD", "USDJPY"])
    
    MAX_ACCOUNT_RISK = user_settings.get("daily_max_drawdown_percent")

    MAX_POSITION_SIZE = user_settings.get("risk_per_trade_percent")

    # Datenbank Name
    DB_NAME = "trading_bot.db"

cfg = Config()