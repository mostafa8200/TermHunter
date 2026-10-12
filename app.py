"""
app.py - Term Hunter: the window you actually see.

Run with:  double-click run.bat   (or:  python app.py)

Layout:   header (status)  ->  controls  ->  settings  ->  table  ->  footer
The background search runs in monitor.py; it sends messages through a queue
and this file turns them into table rows / status text (keeps the window smooth).
"""
import csv
import logging
import queue
import sys
import time
import tkinter as tk
import webbrowser
from logging.handlers import RotatingFileHandler
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from domains import slugify
from monitor import Monitor
from storage import DATA_DIR, Storage

# The system-tray icon is optional: the app still works without it.
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except Exception:  # pragma: no cover
    TRAY_AVAILABLE = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

logging.basicConfig(
    handlers=[RotatingFileHandler(DATA_DIR / "termhunter.log", maxBytes=500_000, backupCount=2,
                                  encoding="utf-8")],
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

COLUMNS = [  # (id, heading, width)
    ("term", "New word / term", 170),
    ("domains", "Suggested domain name(s)", 430),
    ("source", "Where it was found", 200),
    ("found", "Date & time discovered", 150),
]
GREEN, RED, GREY = "#3ecf8e", "#ef5350", "#8a8d98"


def format_domains(domains, limit=5):
    """Show likely-free names first, e.g.  '✓ word.ai   ✓ word.io   ✗ word.com'."""
    ordered = sorted(domains, key=lambda d: 0 if d.get("free") else 1)
    parts = []
    for d in ordered[:limit]:
        mark = "✓ " if d.get("free") is True else ("✗ " if d.get("free") is False else "")
        parts.append(mark + d["name"])
    return "    ".join(parts)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Term Hunter - new AI & science words")
        self.geometry("1120x700")
        self.minsize(900, 560)

        self.db = Storage()
        self.events = queue.Queue()
        self.monitor = Monitor(self.db, self.events)
        self.rows = []                 # newest first
        self.row_by_iid = {}
        self.sort = ("found", True)    # (column, descending)
        self.next_check = None
        self.tray = None

        self._build_ui()
        self._style_table()
        self.load_rows()
        self._setup_tray()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(300, self._poll_events)
        self.after(1000, self._tick)
        if self.db.get_setting("auto_start"):
            self.after(1500, self.start)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Term Hunter", font=ctk.CTkFont(size=26, weight="bold")
                     ).grid(row=0, column=0, sticky="w")
        self.status_dot = ctk.CTkLabel(header, text="●", text_color=GREY, font=ctk.CTkFont(size=16))
        self.status_dot.grid(row=0, column=2, padx=(0, 6))
        self.status_label = ctk.CTkLabel(header, text="Stopped", text_color=GREY)
        self.status_label.grid(row=0, column=3, sticky="e")
        ctk.CTkLabel(header, text="Finds newly coined AI & science words and suggests domain names.",
                     text_color=GREY).grid(row=1, column=0, columnspan=4, sticky="w")

        # Controls + settings
        bar = ctk.CTkFrame(self)
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        self.start_btn = ctk.CTkButton(bar, text="▶  Start", width=100, command=self.start,
                                       fg_color="#2e9d6b", hover_color="#25805a")
        self.start_btn.grid(row=0, column=0, padx=(12, 6), pady=12)
        self.stop_btn = ctk.CTkButton(bar, text="■  Stop", width=100, command=self.stop,
                                      fg_color="#c0504d", hover_color="#9c3f3d", state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=6)
        ctk.CTkButton(bar, text="Search now", width=110, command=self.monitor.search_now,
                      fg_color="#3b6fd4").grid(row=0, column=2, padx=6)

        ctk.CTkLabel(bar, text="Check every").grid(row=0, column=3, padx=(24, 6))
        self.interval_slider = ctk.CTkSlider(bar, from_=20, to=60, number_of_steps=40, width=150,
                                             command=self._on_interval)
        self.interval_slider.set(self.db.get_setting("interval_minutes"))
        self.interval_slider.grid(row=0, column=4)
        self.interval_label = ctk.CTkLabel(bar, text="", width=70)
        self.interval_label.grid(row=0, column=5, padx=(6, 0))
        self._on_interval(self.interval_slider.get(), save=False)

        self.opt_free = self._checkbox(bar, "Check if domains look free", "check_availability", 1, 0)
        self.opt_tray = self._checkbox(bar, "Hide to tray when closed", "minimize_to_tray", 1, 3)
        self.opt_auto = self._checkbox(bar, "Start automatically on launch", "auto_start", 1, 5)
        if not TRAY_AVAILABLE:
            self.opt_tray.configure(state="disabled")

        # Search box
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.refresh_table())
        ctk.CTkEntry(self, textvariable=self.filter_var, placeholder_text="🔍  Filter the table...",
                     height=34).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))

        # Table
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, sticky="nsew", padx=20)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for cid, heading, width in COLUMNS:
            self.tree.heading(cid, text=heading, command=lambda c=cid: self.sort_by(c))
            self.tree.column(cid, width=width, anchor="w", stretch=(cid == "domains"))
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        ys.grid(row=0, column=1, sticky="ns", pady=6, padx=(0, 6))
        self.tree.bind("<Double-1>", lambda e: self.open_article())
        self.tree.bind("<Button-3>", self._context_menu)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Copy term", command=self.copy_term)
        self.menu.add_command(label="Copy domain names", command=self.copy_domains)
        self.menu.add_command(label="Open source article", command=self.open_article)
        self.menu.add_command(label="Check on Namecheap (opens browser)", command=self.open_registrar)

        # Footer
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=4, column=0, sticky="ew", padx=20, pady=(8, 14))
        foot.grid_columnconfigure(0, weight=1)
        self.count_label = ctk.CTkLabel(foot, text="", text_color=GREY)
        self.count_label.grid(row=0, column=0, sticky="w")
        self.next_label = ctk.CTkLabel(foot, text="", text_color=GREY)
        self.next_label.grid(row=0, column=1, padx=12)
        for i, (text, cmd) in enumerate([("Copy domains", self.copy_domains),
                                         ("Export CSV", self.export_csv),
                                         ("Clear all", self.clear_all)]):
            ctk.CTkButton(foot, text=text, width=105, fg_color="#3a3d4c", hover_color="#4a4e61",
                          command=cmd).grid(row=0, column=2 + i, padx=4)

    def _checkbox(self, parent, text, setting, row, col):
        var = tk.BooleanVar(value=bool(self.db.get_setting(setting)))
        cb = ctk.CTkCheckBox(parent, text=text, variable=var,
                             command=lambda: self.db.set_setting(setting, var.get()))
        cb.grid(row=row, column=col, columnspan=3, sticky="w", padx=(12, 6), pady=(0, 12))
        return cb

    def _style_table(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background="#1e1f26", fieldbackground="#1e1f26",
                    foreground="#e6e6e6", rowheight=30, borderwidth=0, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background="#2b2d38", foreground="#ffffff",
                    font=("Segoe UI", 10, "bold"), relief="flat", padding=6)
        s.map("Treeview", background=[("selected", "#3b6fd4")])
        s.map("Treeview.Heading", background=[("active", "#3a3d4c")])

    # --------------------------------------------------------- table logic
    def load_rows(self):
        self.rows = self.db.all_terms()
        self.refresh_table()

    def _sort_key(self, row):
        col = self.sort[0]
        if col == "term":
            return row["term"].lower()
        if col == "domains":
            return row["domains"][0]["name"] if row["domains"] else ""
        if col == "source":
            return row["source"].lower()
        return row["found_at"]

    def refresh_table(self):
        needle = self.filter_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.row_by_iid.clear()
        rows = sorted(self.rows, key=self._sort_key, reverse=self.sort[1])
        shown = 0
        for r in rows:
            text = f"{r['term']} {format_domains(r['domains'], 99)} {r['source']}".lower()
            if needle and needle not in text:
                continue
            iid = str(r["id"])
            self.row_by_iid[iid] = r
            self.tree.insert("", "end", iid=iid, values=(
                r["term"], format_domains(r["domains"]), r["source"], r["found_at"]))
            shown += 1
        self.count_label.configure(text=f"{shown} shown  •  {len(self.rows)} saved")

    def sort_by(self, col):
        self.sort = (col, not self.sort[1]) if self.sort[0] == col else (col, col == "found")
        self.refresh_table()

    def _selected(self):
        sel = self.tree.selection()
        return self.row_by_iid.get(sel[0]) if sel else None

    def _context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.menu.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------- actions
    def start(self):
        self.monitor.start()

    def stop(self):
        self.monitor.stop()

    def _on_interval(self, value, save=True):
        minutes = int(round(float(value)))
        self.interval_label.configure(text=f"{minutes} min")
        if save:
            self.db.set_setting("interval_minutes", minutes)

    def _clip(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def copy_term(self):
        r = self._selected()
        if r:
            self._clip(r["term"])

    def copy_domains(self):
        r = self._selected()
        if r:
            self._clip("\n".join(d["name"] for d in r["domains"]))
        else:
            messagebox.showinfo("Copy domains", "Click a row in the table first.")

    def open_article(self):
        r = self._selected()
        if r and r.get("url"):
            webbrowser.open(r["url"])

    def open_registrar(self):
        r = self._selected()
        if r:
            webbrowser.open("https://www.namecheap.com/domains/registration/results/?domain="
                            + slugify(r["term"]))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="term_hunter.csv",
                                            filetypes=[("CSV (opens in Excel)", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Term", "Domains", "Source", "Discovered", "Link"])
            for r in self.rows:
                w.writerow([r["term"], ", ".join(d["name"] for d in r["domains"]),
                            r["source"], r["found_at"], r["url"]])
        messagebox.showinfo("Export", f"Saved {len(self.rows)} rows to:\n{path}")

    def clear_all(self):
        if messagebox.askyesno("Clear all", "Delete ALL saved terms? This cannot be undone."):
            self.db.clear_terms()
            self.load_rows()

    # ---------------------------------------------- background -> window
    def _poll_events(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "status":
                    self.status_label.configure(text=data)
                elif kind == "state":
                    on = bool(data)
                    self.start_btn.configure(state="disabled" if on else "normal")
                    self.stop_btn.configure(state="normal" if on else "disabled")
                    self.status_dot.configure(text_color=GREEN if on else GREY)
                    self.status_label.configure(text_color=GREEN if on else GREY)
                elif kind == "next":
                    self.next_check = data
                elif kind == "new":
                    self.rows.insert(0, data)
                    self.refresh_table()
                elif kind == "done" and data and self.tray and self.state() == "withdrawn":
                    self.tray.notify(f"{data} new term(s) found", "Term Hunter")
        except queue.Empty:
            pass
        self.after(300, self._poll_events)

    def _tick(self):
        if self.next_check and self.monitor.running:
            left = max(0, int(self.next_check - time.time()))
            self.next_label.configure(text=f"Next check in {left // 60}:{left % 60:02d}")
        else:
            self.next_label.configure(text="")
        self.after(1000, self._tick)

    # ----------------------------------------------------------- tray/exit
    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        try:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((2, 2, 62, 62), fill=(59, 111, 212, 255))
            d.text((24, 22), "TH", fill="white")
            menu = pystray.Menu(
                pystray.MenuItem("Open Term Hunter", lambda: self.after(0, self.show_window), default=True),
                pystray.MenuItem("Search now", lambda: self.monitor.search_now()),
                pystray.MenuItem("Quit", lambda: self.after(0, self.quit_app)))
            self.tray = pystray.Icon("TermHunter", img, "Term Hunter", menu)
            self.tray.run_detached()
        except Exception:
            logging.exception("Tray icon unavailable")
            self.tray = None

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        if self.tray and self.db.get_setting("minimize_to_tray"):
            self.withdraw()      # keep running in the background
            return
        if self.monitor.running and not messagebox.askyesno(
                "Quit", "Monitoring is running. Quit and stop it?"):
            return
        self.quit_app()

    def quit_app(self):
        self.monitor.stop()
        if self.tray:
            self.tray.stop()
        self.destroy()


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        logging.exception("Fatal error")
        raise
