import customtkinter as ctk
import requests
from config_manager import load_config, save_config
import threading
from main import EnterpriseBot
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import math
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import queue
import sys
import logging

# --- FIREBASE KONFIGURATION ---
FIREBASE_PROJECT_ID = "key-store-bd70f" 

# --- HILFSKLASSEN FÜR THREAD-SICHERHEIT ---
class TextboxRedirector:
    """Leitet print() Ausgaben sicher in eine Warteschlange um."""
    def __init__(self, log_queue):
        self.log_queue = log_queue
    def write(self, text):
        if text.strip():
            self.log_queue.put(text + "\n")
    def flush(self):
        pass

class TextboxLogHandler(logging.Handler):
    """Leitet logging Ausgaben sicher in eine Warteschlange um."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg + "\n")

# --- LOGIN FENSTER ---
class JaciLabsLogin(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_config()
        
        self.title("JaciLabs | Core Architecture")
        self.geometry("500x350")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title_lbl = ctk.CTkLabel(self, text="JACI LABS", font=("Montserrat", 28, "bold"))
        self.title_lbl.pack(pady=(40, 10))

        self.subtitle_lbl = ctk.CTkLabel(self, text="Enter your Architecture License Key", text_color="gray")
        self.subtitle_lbl.pack(pady=(0, 20))

        self.key_entry = ctk.CTkEntry(self, width=300, placeholder_text="JACI-XXXX-XXXX-XXXX")
        self.key_entry.insert(0, self.settings.get("license_key", ""))
        self.key_entry.pack(pady=10)

        self.login_btn = ctk.CTkButton(self, text="INITIALIZE ENGINE", command=self.verify_license, fg_color="#10b981", hover_color="#059669")
        self.login_btn.pack(pady=20)

        self.status_lbl = ctk.CTkLabel(self, text="")
        self.status_lbl.pack()

    def verify_license(self):
        entered_key = self.key_entry.get().strip()
        self.status_lbl.configure(text="Verifying...", text_color="yellow")
        self.update()

        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Jacikeys/{entered_key}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                status = data['fields']['status']['stringValue']
                
                if status == "active":
                    self.status_lbl.configure(text="Access Granted. Booting Engine...", text_color="#10b981")
                    self.settings["license_key"] = entered_key
                    save_config(self.settings)
                    self.start_trading_engine()
                else:
                    self.status_lbl.configure(text="License is Revoked or Expired.", text_color="red")
            else:
                self.status_lbl.configure(text="Invalid License Key.", text_color="red")
        except Exception as e:
            self.status_lbl.configure(text="Connection Error.", text_color="red")

    def start_trading_engine(self):
        try:
            dashboard = JaciLabsDashboard()
            self.withdraw() # Login Fenster nur verstecken (vermeidet Animations-Fehler)
            
            # Bot-Thread starten
            bot_thread = threading.Thread(target=dashboard.run_bot_in_background, daemon=True)
            bot_thread.start()
            
            # Chart Update nach 2 Sekunden im Haupt-Thread triggern
            dashboard.after(2000, dashboard.update_chart_data)
            
            dashboard.mainloop()
            self.destroy() # Alles schließen, wenn Dashboard beendet wird
        except Exception as e:
            self.status_lbl.configure(text=f"Dashboard Error: {e}", text_color="red")

# --- DASHBOARD FENSTER ---
class JaciLabsDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("JaciLabs")
        self.geometry("1000x650")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Seitenleiste
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="JACI LABS", font=("Montserrat", 24, "bold"))
        self.logo_label.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: ENGINE RUNNING", text_color="#10b981")
        self.status_label.pack(pady=10)

        # Hauptbereich
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.chart_label = ctk.CTkLabel(self.main_frame, text="Equity Curve & Balance History", font=("Montserrat", 18))
        self.chart_label.pack(anchor="w")
        
        # Timeframes
        self.timeframe_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.timeframe_frame.pack(fill="x", pady=(5, 10))

        self.timeframes = {"1D": 1, "1W": 7, "1M": 30, "1J": 365}
        self.current_tf = 30 

        for tf, days in self.timeframes.items():
            btn = ctk.CTkButton(self.timeframe_frame, text=tf, width=40, height=24, 
                                fg_color="#2b2b2b", hover_color="#3b3b3b", font=("Montserrat", 12),
                                command=lambda d=days: self.change_timeframe(d))
            btn.pack(side="left", padx=(0, 8))

        # Graph Frame
        self.graph_frame = ctk.CTkFrame(self.main_frame, height=350, fg_color="#1e1e1e")
        self.graph_frame.pack(fill="x", pady=5)

        # Matplotlib Setup
        self.fig = Figure(figsize=(6, 3), dpi=100, facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.yaxis.tick_right()
        self.ax.tick_params(colors="#888888", labelsize=10)
        self.ax.spines['bottom'].set_color('#333333')
        for spine in ['top', 'left', 'right']: self.ax.spines[spine].set_color('none')

        self.line, = self.ax.plot([], [], color="#10b981", linewidth=2)
        self.dot, = self.ax.plot([], [], marker='o', color="#3b82f6", markersize=6)
        self.dot_size = 6.0
        self.dot_growing = True

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Log Textbox
        self.log_textbox = ctk.CTkTextbox(self.main_frame, height=150)
        self.log_textbox.pack(fill="both", expand=True, pady=10)
        self.log_textbox.configure(state="disabled")

        # --- LOGGING & QUEUE SYSTEM ---
        self.log_queue = queue.Queue()
        sys.stdout = TextboxRedirector(self.log_queue)
        sys.stderr = TextboxRedirector(self.log_queue)
        
        # Logging Handler integrieren
        handler = TextboxLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

        # Polling starten & Animation
        self.poll_log_queue()
        self.animate_dot()

    def poll_log_queue(self):
        """Prüft die Queue und schreibt Text in die UI (läuft im Haupt-Thread)."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.poll_log_queue)

    def run_bot_in_background(self):
        """Läuft im Hintergrund-Thread. Nutzt nur print(), keine direkten UI Befehle."""
        print("[SYSTEM] Initialisiere JaciLabs Core Engine...")
        try:
            bot = EnterpriseBot()
            bot.run_strategy_loop()
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Engine Crash: {e}")

    def animate_dot(self):
        if self.dot_growing:
            self.dot_size += 0.2
            if self.dot_size >= 9.0: self.dot_growing = False
        else:
            self.dot_size -= 0.2
            if self.dot_size <= 6.0: self.dot_growing = True
        
        if self.dot.get_xdata().size > 0:
            self.dot.set_markersize(self.dot_size)
            self.canvas.draw_idle()
        self.after(50, self.animate_dot)

    def change_timeframe(self, days):
        self.current_tf = days
        self.update_chart_data()

    def update_chart_data(self):
        """Wird im Haupt-Thread aufgerufen."""
        try:
            if not mt5.initialize(): return 
            acc = mt5.account_info()
            if not acc: return
            
            balance = acc.balance
            date_to = datetime.now()
            date_from = date_to - timedelta(days=self.current_tf)
            deals = mt5.history_deals_get(date_from, date_to)

            self.ax.clear()
            self.ax.yaxis.tick_right()
            self.ax.tick_params(colors="#888888", labelsize=10)
            self.ax.spines['bottom'].set_color('#333333')
            for spine in ['top', 'left', 'right']: self.ax.spines[spine].set_color('none')

            if not deals:
                times, equity = [date_from, date_to], [balance, balance]
            else:
                df = pd.DataFrame([d._asdict() for d in deals])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                fee = df['fee'] if 'fee' in df.columns else 0
                df['p'] = df['profit'] + df['commission'] + df['swap'] + fee
                start_bal = balance - df['p'].sum()
                df['curve'] = start_bal + df['p'].cumsum()
                times, equity = df['time'].tolist(), df['curve'].tolist()
                if len(times) == 1:
                    times.append(date_to); equity.append(equity[0])

            self.line, = self.ax.plot(times, equity, color="#10b981", linewidth=2)
            self.dot, = self.ax.plot(times[-1], equity[-1], marker='o', color="#3b82f6", markersize=self.dot_size)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
            self.fig.autofmt_xdate()
            self.canvas.draw()
        except Exception as e:
            print(f"[CHART ERROR] {e}")

if __name__ == "__main__":
    app = JaciLabsLogin()
    app.mainloop()