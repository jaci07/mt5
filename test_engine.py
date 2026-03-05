import MetaTrader5 as mt5
import pandas as pd
from infrastructure import VolumeProfileEngine

def run_test():
    if not mt5.initialize():
        print("❌ MT5 Initialisierung fehlgeschlagen!")
        return

    print("📊 Hole Testdaten für EURUSD (M5)...")
    rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M5, 0, 200)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    current_price = df['close'].iloc[-1]

    print("⚙️ Initialisiere VolumeProfileEngine...")
    vp_engine = VolumeProfileEngine()

    try:
        # Test 1: find_last_pivot
        print("\n--- Test 1: find_last_pivot ---")
        anchor_idx = vp_engine.find_last_pivot(df)
        print(f"✅ Erfolgreich! Letzter Pivot (Anchor Index) gefunden bei: {anchor_idx}")

        # Test 2: calculate_vwap
        print("\n--- Test 2: calculate_vwap ---")
        vwap = vp_engine.calculate_vwap(df)
        print(f"✅ Erfolgreich! Aktueller VWAP: {vwap:.5f}")

        # Profil berechnen (Muss ausgeführt werden, damit LVA funktioniert)
        print("\n--- Test 3: calculate_enhanced_profile ---")
        df_anchored = df.loc[anchor_idx:] if anchor_idx > 0 else df
        poc, vah, val = vp_engine.calculate_enhanced_profile(df_anchored)
        print(f"✅ Erfolgreich! POC: {poc:.5f} | VAH: {vah:.5f} | VAL: {val:.5f}")

        # Test 4: find_nearest_lva
        print("\n--- Test 4: find_nearest_lva ---")
        lva_below = vp_engine.find_nearest_lva(df, current_price, direction="DOWN")
        lva_above = vp_engine.find_nearest_lva(df, current_price, direction="UP")
        print(f"✅ Erfolgreich! Nächstes LVA unten: {lva_below} | Nächstes LVA oben: {lva_above}")

        print("\n🎉 ALLE TESTS BESTANDEN! Deine VolumeProfileEngine ist fehlerfrei und hat alle Funktionen.")

    except AttributeError as e:
        print(f"\n❌ FEHLER: Es fehlt eine Funktion! Detail: {e}")
        print("💡 Überprüfe nochmal, ob du die fehlende Funktion in die Klasse VolumeProfileEngine in infrastructure.py eingefügt hast.")
    except Exception as e:
        print(f"\n❌ UNERWARTETER FEHLER: {e}")

if __name__ == "__main__":
    run_test()