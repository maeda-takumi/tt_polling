import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

from selenium.webdriver.support.ui import WebDriverWait

from auth import login
from browser import create_driver
from scraper import scrape_events
from storage import DB_PATH, export_events_to_csv, get_connection, init_db, save_events

GREEN = "#22c55e"
GREEN_DARK = "#15803d"
BG = "#f8fafc"
CARD = "#ffffff"
TEXT = "#0f172a"
MUTED = "#64748b"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TimeTree Scraper")
        self.root.geometry("860x620")
        self.root.configure(bg=BG)

        self.status = tk.StringVar(value="待機中")
        self.start_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.keyword = tk.StringVar(value="")
        self.db_path = tk.StringVar(value=str(DB_PATH))
        self.csv_path = tk.StringVar(value="events_export.csv")

        self._setup_style()
        self._build()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED)
        style.configure("CardLabel.TLabel", background=CARD, foreground=TEXT)
        style.configure("TEntry", padding=6)
        style.configure("Accent.TButton", background=GREEN, foreground="white", padding=(16, 8), borderwidth=0)
        style.map("Accent.TButton", background=[("active", GREEN_DARK)])
        style.configure("Ghost.TButton", background="#e2e8f0", foreground=TEXT, padding=(14, 8), borderwidth=0)

    def _build(self):
        wrap = ttk.Frame(self.root, padding=24)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="TimeTree Scraper", style="Title.TLabel").pack(anchor="w")
        ttk.Label(wrap, text="全カレンダー対象 / 指定日から31日 / SQLite + CSV", style="Sub.TLabel").pack(anchor="w", pady=(4, 18))

        card = ttk.Frame(wrap, style="Card.TFrame", padding=20)
        card.pack(fill="x")

        self._field(card, 0, "開始日 (YYYY-MM-DD)", self.start_date)
        self._field(card, 1, "キーワード（任意）", self.keyword)
        self._field(card, 2, "DBファイル", self.db_path)
        self._field(card, 3, "CSV出力ファイル", self.csv_path)

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.scrape_btn = ttk.Button(buttons, text="スクレイピング実行", style="Accent.TButton", command=self.start_scrape)
        self.scrape_btn.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="CSV出力", style="Ghost.TButton", command=self.export_csv).grid(row=0, column=1, padx=8)
        ttk.Button(buttons, text="保存先選択", style="Ghost.TButton", command=self.select_csv).grid(row=0, column=2, padx=8)

        status_wrap = ttk.Frame(wrap)
        status_wrap.pack(fill="x", pady=(16, 0))
        ttk.Label(status_wrap, text="Status:", style="Sub.TLabel").pack(side="left")
        ttk.Label(status_wrap, textvariable=self.status).pack(side="left", padx=(8, 0))

        self.log = tk.Text(wrap, height=16, bg="#0b1220", fg="#d1fae5", font=("Consolas", 10), relief="flat")
        self.log.pack(fill="both", expand=True, pady=(10, 0))

    def _field(self, parent, row: int, label: str, var: tk.StringVar):
        ttk.Label(parent, text=label, style="CardLabel.TLabel").grid(row=row, column=0, sticky="w", pady=8)
        ttk.Entry(parent, textvariable=var, width=70).grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        parent.columnconfigure(1, weight=1)

    def _append_log(self, msg: str):
        self.log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log.see("end")

    def select_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.csv_path.set(path)

    def start_scrape(self):
        self.scrape_btn.state(["disabled"])
        threading.Thread(target=self._run_scrape, daemon=True).start()

    def _run_scrape(self):
        try:
            start_date = datetime.strptime(self.start_date.get().strip(), "%Y-%m-%d").date()
            keyword = self.keyword.get().strip()
            db_path = self.db_path.get().strip() or str(DB_PATH)

            self.root.after(0, self.status.set, "ログイン中...")
            driver = create_driver()
            try:
                login(driver, WebDriverWait(driver, 20))
                self.root.after(0, self.status.set, "取得中...")
                events = scrape_events(driver, start_date=start_date, keyword=keyword)
            finally:
                driver.quit()

            with get_connection(db_path) as conn:
                init_db(conn)
                count = save_events(conn, events)

            self.root.after(0, self.status.set, f"完了: {count}件保存")
            self.root.after(0, self._append_log, f"DB保存完了 {db_path} ({count}件)")
        except Exception as exc:
            self.root.after(0, self.status.set, "エラー")
            self.root.after(0, self._append_log, f"エラー: {exc}")
            self.root.after(0, messagebox.showerror, "Error", str(exc))
        finally:
            self.root.after(0, lambda: self.scrape_btn.state(["!disabled"]))

    def export_csv(self):
        try:
            start = datetime.strptime(self.start_date.get().strip(), "%Y-%m-%d").date()
            end = start + timedelta(days=30)
            db_path = self.db_path.get().strip() or str(DB_PATH)
            csv_path = self.csv_path.get().strip() or "events_export.csv"

            with get_connection(db_path) as conn:
                init_db(conn)
                count = export_events_to_csv(
                    conn=conn,
                    output_path=csv_path,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    keyword=self.keyword.get().strip(),
                )

            self.status.set(f"CSV出力完了: {count}件")
            self._append_log(f"CSV出力 {csv_path} ({count}件)")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._append_log(f"CSV出力失敗: {exc}")


def main():
    root = tk.Tk()
    app = App(root)
    app._append_log("アプリ起動")
    root.mainloop()


if __name__ == "__main__":
    main()
