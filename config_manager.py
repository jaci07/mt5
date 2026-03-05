import json
import os

CONFIG_FILE = "config.json"

# Deine elitären Standard-Einstellungen
DEFAULT_CONFIG = {
    "license_key": "", #MUST-- Enter our license
    "mt5_account_number": "", #MUST-- Enter your MT5 account number
    "mt5_password": "", #MUST-- Enter your MT5 password; Your Password is saved on your local computer and is never shared with us. It is only used to connect to the MT5 API on your machine.
    "mt5_server": "", #MUST-- Enter your MT5 server
    "risk_per_trade_percent": 1.0,
    "daily_max_drawdown_percent": 5,
    "daily_max_win_percent": 3,
    "discord_webhook_url": "", #OPTIONAL-- For Account Control via Discord
    "theme": "dark",
    "symbols": ["EURUSD", "GBPUSD", "USDCHF", "USDJPY", "USDCAD"] #--Add as you like
}

def load_config():
    """Lädt die Config oder erstellt eine neue, falls sie fehlt."""
    # Wenn die Datei nicht existiert, erstelle sie mit den Standardwerten
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as file:
            json.dump(DEFAULT_CONFIG, file, indent=4)
        print("[SYSTEM] Neue jacilabs_config.json generiert.")
        return DEFAULT_CONFIG
    
    # Wenn sie existiert, lese die Daten des Kunden aus
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_config(new_data):
    """Speichert Änderungen (z.B. wenn der Kunde im UI seinen Key eingibt)."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(new_data, file, indent=4)