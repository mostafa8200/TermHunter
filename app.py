"""
app.py - Term Hunter 2.0: the window you actually see.

Run with:  double-click run.bat   (or:  python app.py)

Layout:  sidebar (controls, sectors, theme)  |  dashboard (stat cards, filters, table)
The background search lives in monitor.py and talks to this window through a queue,
which keeps the interface smooth while it works.
"""
import csv
import logging
import queue
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from logging.handlers import RotatingFileHandler
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from domains import (ALL_EXTENSIONS, POPULAR_EXTENSIONS, STYLE_DEFS, check_availability,
                     score_term, selected_extensions, slugify, suggest_domains)
from monitor import Monitor
from sectors import SECTORS
from storage import DATA_DIR, Storage

# The system-tray icon is optional: the app still works without it.
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except Exception:  # pragma: no cover
    TRAY_AVAILABLE = False

logging.basicConfig(
    handlers=[RotatingFileHandler(DATA_DIR / "termhunter.log", maxBytes=500_000, backupCount=2,
                                  encoding="utf-8")],
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---- Design tokens: (light, dark) pairs switch automatically with the theme ----
SIDEBAR = ("#f3f4fa", "#101118")
CARD = ("#f0f2f9", "#1b1d27")
TEXT = ("#1b1d26", "#f1f2f6")
MUTED = ("#6b7085", "#8b8fa3")
ACCENT, ACCENT_H = ("#4f7cff", "#4f7cff"), ("#3a64e0", "#6b90ff")
GREEN, GREEN_H = ("#1fae6e", "#2fbf7f"), ("#17935c", "#25a06c")
RED, RED_H = ("#e5484d", "#d9534f"), ("#c93b40", "#b9433f")
NEUTRAL, NEUTRAL_H = ("#e2e5f0", "#2a2d3b"), ("#d2d6e6", "#383c4f")
PREMIUM_SCORE = 75

TABLE_PALETTE = {
    "Dark": dict(field="#171922", fg="#e8e9ee", head="#232634", odd="#171922", even="#1c1e29",
                 hot="#ffcf6b", sel="#4f7cff"),
    "Light": dict(field="#ffffff", fg="#1b1d26", head="#e9ecf5", odd="#ffffff", even="#f5f6fb",
                  hot="#b35f00", sel="#4f7cff"),
}


def mark(d):
    """✓ = looks free, ✗ = taken, nothing = not checked."""
    if not d:
        return ""
    return "✓ " if d.get("free") is True else ("✗ " if d.get("free") is False else "")


class App(ctk.CTk):
    def __init__(self):
        db = Storage()
        ctk.set_appearance_mode(db.get_setting("appearance"))
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.db = db
        self.title("Term Hunter - domain opportunity radar")
        self.geometry("1400x800")
        self.minsize(1100, 680)

        self.events = queue.Queue()
        self.monitor = Monitor(self.db, self.events)
        self.rows = []
        self.row_by_iid = {}
        self.sort = ("found", True)          # (column id, descending?)
        self.next_check = None
        self.tray = None
        self.columns = []
        self.settings_win = None

        self._build_sidebar()
        self._build_main()
        self.restyle_table()
        self.rebuild_columns()
        self.load_rows()
        self._setup_tray()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(300, self._poll_events)
        self.after(1000, self._tick)
        if self.db.get_setting("auto_start"):
            self.after(1500, self.start)

    # =================================================================== sidebar
    def _build_sidebar(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sb = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sb, text="◆  Term Hunter", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w", padx=22, pady=(24, 0))
        ctk.CTkLabel(sb, text="Domain opportunity radar", text_color=MUTED
                     ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 14))

        pill = ctk.CTkFrame(sb, corner_radius=20, fg_color=CARD)
        pill.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        pill.grid_columnconfigure(1, weight=1)
        self.status_dot = ctk.CTkLabel(pill, text="●", text_color=MUTED, font=ctk.CTkFont(size=14))
        self.status_dot.grid(row=0, column=0, padx=(14, 6), pady=8)
        self.status_label = ctk.CTkLabel(pill, text="Stopped", text_color=MUTED, anchor="w",
                                         wraplength=170, justify="left")
        self.status_label.grid(row=0, column=1, sticky="w", pady=8, padx=(0, 10))

        self.start_btn = ctk.CTkButton(sb, text="▶   Start monitoring", height=40, command=self.start,
                                       fg_color=GREEN, hover_color=GREEN_H, corner_radius=10)
        self.start_btn.grid(row=3, column=0, sticky="ew", padx=18, pady=3)
        self.stop_btn = ctk.CTkButton(sb, text="■   Stop", height=40, command=self.stop,
                                      fg_color=RED, hover_color=RED_H, corner_radius=10,
                                      state="disabled")
        self.stop_btn.grid(row=4, column=0, sticky="ew", padx=18, pady=3)
        ctk.CTkButton(sb, text="⟳   Search now", height=38, command=self.monitor.search_now,
                      fg_color=NEUTRAL, hover_color=NEUTRAL_H, text_color=TEXT, corner_radius=10
                      ).grid(row=5, column=0, sticky="ew", padx=18, pady=3)

        self.interval_label = ctk.CTkLabel(sb, text="", text_color=MUTED, anchor="w")
        self.interval_label.grid(row=6, column=0, sticky="ew", padx=22, pady=(14, 0))
        self.interval_slider = ctk.CTkSlider(sb, from_=20, to=60, number_of_steps=40,
                                             command=self._on_interval, button_color=ACCENT,
                                             progress_color=ACCENT)
        self.interval_slider.set(self.db.get_setting("interval_minutes"))
        self.interval_slider.grid(row=7, column=0, sticky="ew", padx=20, pady=(4, 10))
        self._on_interval(self.interval_slider.get(), save=False)

        # Sectors
        head = ctk.CTkFrame(sb, fg_color="transparent")
        head.grid(row=8, column=0, sticky="ew", padx=18)
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="SECTORS", text_color=MUTED, font=ctk.CTkFont(size=11, weight="bold")
                     ).grid(row=0, column=0, sticky="w", padx=4)
        for i, (txt, val) in enumerate((("All", True), ("None", False))):
            ctk.CTkButton(head, text=txt, width=42, height=22, fg_color="transparent",
                          text_color=ACCENT, hover_color=NEUTRAL, font=ctk.CTkFont(size=11),
                          command=lambda v=val: self._set_all_sectors(v)
                          ).grid(row=0, column=1 + i)
        box = ctk.CTkScrollableFrame(sb, fg_color="transparent", height=250)
        box.grid(row=9, column=0, sticky="nsew", padx=10, pady=(2, 6))
        sb.grid_rowconfigure(9, weight=1)
        chosen = set(self.db.get_setting("sectors"))
        self.sector_vars = {}
        for name, info in SECTORS.items():
            var = tk.BooleanVar(value=name in chosen)
            self.sector_vars[name] = var
            ctk.CTkCheckBox(box, text=f"{info['icon']}  {name}", variable=var, text_color=TEXT,
                            command=self._save_sectors, checkbox_width=20, checkbox_height=20,
                            fg_color=ACCENT, hover_color=ACCENT_H
                            ).pack(anchor="w", pady=4, padx=8)

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.grid(row=10, column=0, sticky="ew", padx=18, pady=(4, 18))
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(bottom, text="⚙   Settings & domain extensions", height=38,
                      command=self.open_settings, fg_color=ACCENT, hover_color=ACCENT_H,
                      corner_radius=10).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.theme_btn = ctk.CTkSegmentedButton(
            bottom, values=["Light", "Dark", "System"], command=self.set_theme,
            selected_color=ACCENT, selected_hover_color=ACCENT_H)
        self.theme_btn.set(self.db.get_setting("appearance"))
        self.theme_btn.grid(row=1, column=0, sticky="ew")

    # ================================================================ main area
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(22, 22), pady=(18, 14))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="Discoveries", font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text="Newly coined words, ranked by domain potential.",
                     text_color=MUTED).grid(row=1, column=0, sticky="w")

        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=14)
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1, uniform="card")
        self.card_total = self._card(cards, 0, "Terms saved")
        self.card_today = self._card(cards, 1, "Found today")
        self.card_hot = self._card(cards, 2, f"Premium picks (score ≥ {PREMIUM_SCORE})")
        self.card_next = self._card(cards, 3, "Next check")

        bar = ctk.CTkFrame(main, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.refresh_table())
        ctk.CTkEntry(bar, textvariable=self.filter_var, placeholder_text="🔍  Search words, domains, sources…",
                     width=270, height=34).grid(row=0, column=0, padx=(0, 10))
        self.sector_filter = ctk.CTkOptionMenu(bar, values=["All sectors"] + list(SECTORS), width=150,
                                               height=34, command=lambda _: self.refresh_table(),
                                               fg_color=NEUTRAL, button_color=NEUTRAL_H,
                                               button_hover_color=ACCENT, text_color=TEXT)
        self.sector_filter.grid(row=0, column=1, padx=(0, 10))
        ctk.CTkLabel(bar, text="Min score", text_color=MUTED).grid(row=0, column=2, padx=(6, 4))
        self.score_slider = ctk.CTkSlider(bar, from_=0, to=90, number_of_steps=18, width=110,
                                          command=self._on_min_score, button_color=ACCENT,
                                          progress_color=ACCENT)
        self.score_slider.set(0)
        self.score_slider.grid(row=0, column=3)
        self.score_label = ctk.CTkLabel(bar, text="0", width=28, text_color=TEXT)
        self.score_label.grid(row=0, column=4, padx=(4, 12))
        self.fav_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(bar, text="★ Favorites", variable=self.fav_var, command=self.refresh_table,
                      progress_color=ACCENT, text_color=TEXT).grid(row=0, column=5, padx=4)
        bar.grid_columnconfigure(6, weight=1)
        ctk.CTkButton(bar, text="Export CSV", width=100, height=34, command=self.export_csv,
                      fg_color=NEUTRAL, hover_color=NEUTRAL_H, text_color=TEXT
                      ).grid(row=0, column=7, padx=4)
        ctk.CTkButton(bar, text="Clear all", width=80, height=34, command=self.clear_all,
                      fg_color=NEUTRAL, hover_color=RED, text_color=TEXT
                      ).grid(row=0, column=8, padx=(4, 0))

        frame = ctk.CTkFrame(main, corner_radius=12, fg_color=CARD)
        frame.grid(row=3, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, show="headings", selectmode="browse")
        ys = ctk.CTkScrollbar(frame, command=self.tree.yview)
        xs = ctk.CTkScrollbar(frame, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        ys.grid(row=0, column=1, sticky="ns", pady=(8, 0), padx=(2, 4))
        xs.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 4))
        self.tree.bind("<Double-1>", lambda e: self.open_article())
        self.tree.bind("<Button-3>", self._context_menu)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        self.menu = tk.Menu(self, tearoff=0)
        for label, cmd in (("★ Favorite / unfavorite", self.toggle_favorite),
                           ("Copy term", self.copy_term),
                           ("Copy all domain names", self.copy_domains),
                           ("Copy best pick", self.copy_best),
                           ("Open source article", self.open_article),
                           ("Check on Namecheap", self.open_namecheap),
                           ("Check on GoDaddy", self.open_godaddy),
                           ("Re-check domains now", self.recheck_selected),
                           ("Delete row", self.delete_selected)):
            self.menu.add_command(label=label, command=cmd)

        self.footer = ctk.CTkLabel(
            main, text="", text_color=MUTED, anchor="w")
        self.footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))

    def _card(self, parent, col, caption):
        f = ctk.CTkFrame(parent, corner_radius=14, fg_color=CARD)
        f.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        value = ctk.CTkLabel(f, text="0", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT)
        value.pack(anchor="w", padx=18, pady=(12, 0))
        ctk.CTkLabel(f, text=caption, text_color=MUTED).pack(anchor="w", padx=18, pady=(0, 12))
        return value

    # ============================================================ table helpers
    def restyle_table(self):
        mode = ctk.get_appearance_mode()
        p = TABLE_PALETTE["Light" if mode == "Light" else "Dark"]
        s = ttk.Style(self)
        s.theme_use("clam")
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])   # no outer border
        s.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                    rowheight=34, borderwidth=0, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background=p["head"], foreground=p["fg"], relief="flat",
                    font=("Segoe UI", 10, "bold"), padding=(8, 8), borderwidth=0)
        s.map("Treeview", background=[("selected", p["sel"])], foreground=[("selected", "#ffffff")])
        s.map("Treeview.Heading", background=[("active", p["head"])])
        self.tree.tag_configure("odd", background=p["odd"])
        self.tree.tag_configure("even", background=p["even"])
        self.tree.tag_configure("hot", foreground=p["hot"])

    def rebuild_columns(self):
        """Columns: fixed ones + one column per chosen extension (each domain separate)."""
        self.exts = selected_extensions(self.db)
        cols = [("term", "New word / term", 170), ("sector", "Sector", 120),
                ("score", "Score", 70), ("best", "Best pick", 165)]
        cols += [(f"x_{e}", f".{e}", 150) for e in self.exts]
        cols += [("ideas", "Other ideas", 300), ("source", "Where found", 190),
                 ("found", "Date & time discovered", 160)]
        self.columns = cols
        self.tree.configure(columns=[c[0] for c in cols], displaycolumns="#all")
        for cid, _, width in cols:
            self.tree.column(cid, width=width, minwidth=60, anchor="w", stretch=False)
        self._update_headings()
        self.refresh_table()

    def _update_headings(self):
        for cid, text, _ in self.columns:
            arrow = ""
            if cid == self.sort[0]:
                arrow = "  ▼" if self.sort[1] else "  ▲"
            self.tree.heading(cid, text=text + arrow, command=lambda c=cid: self.sort_by(c))

    def _free_rank(self, row, ext):
        slug = slugify(row["term"])
        for d in row["domains"]:
            if d["name"] == f"{slug}.{ext}":
                return 0 if d.get("free") is True else (2 if d.get("free") is False else 1)
        return 3

    def _sort_key(self, r):
        col = self.sort[0]
        if col == "term":
            return r["term"].lower()
        if col == "sector":
            return r["sector"]
        if col == "score":
            return r["score"]
        if col == "source":
            return r["source"].lower()
        if col.startswith("x_"):
            return self._free_rank(r, col[2:])
        return r["found_at"]

    def _best_pick(self, r):
        for d in r["domains"]:
            if d.get("free") is True:
                return "✓ " + d["name"]
        return "—"

    def _values(self, r):
        slug = slugify(r["term"])
        lookup = {d["name"]: d for d in r["domains"]}
        vals = [("★ " if r["fav"] else "") + r["term"], r["sector"] or "—", r["score"],
                self._best_pick(r)]
        for e in self.exts:
            name = f"{slug}.{e}"
            vals.append(mark(lookup.get(name)) + name)
        ideas = [d for d in r["domains"] if d["name"].split(".", 1)[0] != slug]
        ideas.sort(key=lambda d: 0 if d.get("free") is True else 1)
        vals.append("   ".join(mark(d) + d["name"] for d in ideas[:3]) or "—")
        vals += [r["source"], r["found_at"]]
        return vals

    def refresh_table(self):
        needle = self.filter_var.get().strip().lower()
        sector = self.sector_filter.get()
        min_score = int(self.score_slider.get())
        favs = self.fav_var.get()
        self.tree.delete(*self.tree.get_children())
        self.row_by_iid.clear()
        shown = 0
        for r in sorted(self.rows, key=self._sort_key, reverse=self.sort[1]):
            if sector != "All sectors" and r["sector"] != sector:
                continue
            if r["score"] < min_score or (favs and not r["fav"]):
                continue
            if needle:
                hay = (f"{r['term']} {r['sector']} {r['source']} "
                       + " ".join(d["name"] for d in r["domains"])).lower()
                if needle not in hay:
                    continue
            tags = ["odd" if shown % 2 else "even"]
            if r["score"] >= PREMIUM_SCORE:
                tags.append("hot")
            iid = str(r["id"])
            self.row_by_iid[iid] = r
            self.tree.insert("", "end", iid=iid, values=self._values(r), tags=tags)
            shown += 1
        today = datetime.now().strftime("%Y-%m-%d")
        self.card_total.configure(text=str(len(self.rows)))
        self.card_today.configure(text=str(sum(r["found_at"].startswith(today) for r in self.rows)))
        self.card_hot.configure(text=str(sum(r["score"] >= PREMIUM_SCORE for r in self.rows)))
        self.footer.configure(text=f"{shown} shown   •   ✓ looks free   ✗ taken   "
                                   f"•   gold rows = premium score   •   double-click opens the "
                                   f"article, right-click for more")

    def load_rows(self):
        self.rows = self.db.all_terms()
        self.refresh_table()

    def sort_by(self, col):
        self.sort = (col, not self.sort[1]) if self.sort[0] == col else (col, col in ("found", "score"))
        self._update_headings()
        self.refresh_table()

    def _selected(self):
        sel = self.tree.selection()
        return self.row_by_iid.get(sel[0]) if sel else None

    def _context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.menu.tk_popup(event.x_root, event.y_root)

    # ================================================================== actions
    def start(self):
        if not self.db.get_setting("sectors"):
            messagebox.showinfo("Term Hunter", "Tick at least one sector in the sidebar first.")
            return
        self.monitor.start()

    def stop(self):
        self.monitor.stop()

    def _on_interval(self, value, save=True):
        minutes = int(round(float(value)))
        self.interval_label.configure(text=f"Check every {minutes} minutes")
        if save:
            self.db.set_setting("interval_minutes", minutes)

    def _on_min_score(self, value):
        self.score_label.configure(text=str(int(value)))
        self.refresh_table()

    def _save_sectors(self):
        self.db.set_setting("sectors", [n for n, v in self.sector_vars.items() if v.get()])

    def _set_all_sectors(self, value):
        for v in self.sector_vars.values():
            v.set(value)
        self._save_sectors()

    def set_theme(self, mode):
        self.db.set_setting("appearance", mode)
        ctk.set_appearance_mode(mode)
        self.after(50, lambda: (self.restyle_table(), self.refresh_table()))

    def open_settings(self):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.focus()
            return
        self.settings_win = SettingsDialog(self)

    def apply_settings(self):
        self.interval_slider.set(self.db.get_setting("interval_minutes"))
        self._on_interval(self.interval_slider.get(), save=False)
        self.theme_btn.set(self.db.get_setting("appearance"))
        self.rebuild_columns()

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
            messagebox.showinfo("Copy", "Click a row in the table first.")

    def copy_best(self):
        r = self._selected()
        if r:
            self._clip(self._best_pick(r).replace("✓ ", "").replace("—", ""))

    def open_article(self):
        r = self._selected()
        if r and r.get("url"):
            webbrowser.open(r["url"])

    def open_namecheap(self):
        r = self._selected()
        if r:
            webbrowser.open("https://www.namecheap.com/domains/registration/results/?domain="
                            + slugify(r["term"]))

    def open_godaddy(self):
        r = self._selected()
        if r:
            webbrowser.open("https://www.godaddy.com/domainsearch/find?domainToCheck="
                            + slugify(r["term"]))

    def toggle_favorite(self):
        r = self._selected()
        if r:
            r["fav"] = 0 if r["fav"] else 1
            self.db.set_favorite(r["id"], r["fav"])
            self.refresh_table()

    def delete_selected(self):
        r = self._selected()
        if r:
            self.db.delete_term(r["id"])
            self.rows = [x for x in self.rows if x["id"] != r["id"]]
            self.refresh_table()

    def recheck_selected(self):
        r = self._selected()
        if not r:
            return
        self.status_label.configure(text=f"Re-checking {r['term']}…")

        def work():
            names = suggest_domains(r["term"], selected_extensions(self.db),
                                    list(self.db.get_setting("styles")),
                                    int(self.db.get_setting("style_ext_count")))
            domains = check_availability(names)
            score = score_term(r["term"], r["sector"], domains)
            self.db.update_domains(r["id"], domains, score)
            self.events.put(("updated", dict(r, domains=domains, score=score)))
            self.events.put(("status", f"Re-checked {r['term']}"))
        threading.Thread(target=work, daemon=True).start()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="term_hunter.csv",
                                            filetypes=[("CSV (opens in Excel)", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Term", "Sector", "Score", "Free domains", "All domains", "Source",
                        "Discovered", "Link"])
            for r in self.rows:
                free = ", ".join(d["name"] for d in r["domains"] if d.get("free") is True)
                w.writerow([r["term"], r["sector"], r["score"], free,
                            ", ".join(d["name"] for d in r["domains"]),
                            r["source"], r["found_at"], r["url"]])
        messagebox.showinfo("Export", f"Saved {len(self.rows)} rows to:\n{path}")

    def clear_all(self):
        if messagebox.askyesno("Clear all", "Delete ALL saved terms? This cannot be undone."):
            self.db.clear_terms()
            self.load_rows()

    # ================================================ background -> window
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
                    self.status_dot.configure(text_color=GREEN if on else MUTED)
                elif kind == "next":
                    self.next_check = data
                elif kind == "new":
                    self.rows.insert(0, data)
                    self.refresh_table()
                elif kind == "updated":
                    self.rows = [data if x["id"] == data["id"] else x for x in self.rows]
                    self.refresh_table()
                elif kind == "done" and data and self.tray and self.state() == "withdrawn" \
                        and self.db.get_setting("notify"):
                    self.tray.notify(f"{data} new term(s) found", "Term Hunter")
        except queue.Empty:
            pass
        self.after(300, self._poll_events)

    def _tick(self):
        if self.next_check and self.monitor.running:
            left = max(0, int(self.next_check - time.time()))
            self.card_next.configure(text=f"{left // 60}:{left % 60:02d}")
        else:
            self.card_next.configure(text="Running…" if self.monitor.running else "Paused")
        self.after(1000, self._tick)

    # ============================================================ tray / exit
    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        try:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((2, 2, 62, 62), radius=16, fill=(79, 124, 255, 255))
            d.polygon([(32, 12), (50, 32), (32, 52), (14, 32)], fill="white")
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
            self.withdraw()
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


class SettingsDialog(ctk.CTkToplevel):
    """Pop-up window with tabs: Domains / Search / App."""

    def __init__(self, app):
        super().__init__(app)
        self.app, self.db = app, app.db
        self.title("Settings")
        self.geometry("760x700")
        self.transient(app)
        self.after(200, lambda: (self.lift(), self.focus_force()))

        tabs = ctk.CTkTabview(self, segmented_button_selected_color=ACCENT,
                              segmented_button_selected_hover_color=ACCENT_H)
        tabs.pack(fill="both", expand=True, padx=16, pady=(12, 4))
        self._tab_domains(tabs.add("Domains"))
        self._tab_search(tabs.add("Search"))
        self._tab_app(tabs.add("App"))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkButton(row, text="Save & apply", width=140, height=38, fg_color=ACCENT,
                      hover_color=ACCENT_H, command=self.save).pack(side="right")
        ctk.CTkButton(row, text="Cancel", width=100, height=38, fg_color=NEUTRAL,
                      hover_color=NEUTRAL_H, text_color=TEXT, command=self.destroy
                      ).pack(side="right", padx=8)

    # ---- Domains tab
    def _tab_domains(self, tab):
        ctk.CTkLabel(tab, text="Domain extensions to suggest", font=ctk.CTkFont(size=15, weight="bold")
                     ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(tab, text="Each ticked extension gets its own column in the table (includes .si).",
                     text_color=MUTED).pack(anchor="w")
        quick = ctk.CTkFrame(tab, fg_color="transparent")
        quick.pack(anchor="w", pady=6)
        for text, fn in (("Popular", lambda: self._set_exts(POPULAR_EXTENSIONS)),
                         ("Select all", lambda: self._set_exts(list(self.ext_vars))),
                         ("Select none", lambda: self._set_exts([]))):
            ctk.CTkButton(quick, text=text, width=96, height=28, fg_color=NEUTRAL,
                          hover_color=NEUTRAL_H, text_color=TEXT, command=fn
                          ).pack(side="left", padx=(0, 6))

        self.ext_frame = ctk.CTkScrollableFrame(tab, height=190)
        self.ext_frame.pack(fill="x")
        chosen = set(self.db.get_setting("extensions"))
        self.ext_vars = {}
        for ext in ALL_EXTENSIONS + list(self.db.get_setting("custom_extensions")):
            self._add_ext_checkbox(ext, ext in chosen)

        add = ctk.CTkFrame(tab, fg_color="transparent")
        add.pack(anchor="w", pady=6)
        self.custom_entry = ctk.CTkEntry(add, width=150, placeholder_text="custom e.g. co.uk")
        self.custom_entry.pack(side="left")
        ctk.CTkButton(add, text="Add extension", width=110, command=self._add_custom,
                      fg_color=NEUTRAL, hover_color=NEUTRAL_H, text_color=TEXT
                      ).pack(side="left", padx=8)

        ctk.CTkLabel(tab, text="Name styles (added on top of the exact word)",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(8, 2))
        sf = ctk.CTkFrame(tab, fg_color="transparent")
        sf.pack(anchor="w")
        styles = set(self.db.get_setting("styles"))
        self.style_vars = {}
        for i, (key, pattern) in enumerate(STYLE_DEFS):
            var = tk.BooleanVar(value=key in styles)
            self.style_vars[key] = var
            ctk.CTkCheckBox(sf, text=pattern.replace("{word}", "word"), variable=var, width=150
                            ).grid(row=i // 5, column=i % 5, padx=6, pady=4, sticky="w")
        line = ctk.CTkFrame(tab, fg_color="transparent")
        line.pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(line, text="Apply styles to the first").pack(side="left")
        self.style_n = ctk.CTkOptionMenu(line, values=["1", "2", "3", "4"], width=64,
                                         fg_color=NEUTRAL, button_color=NEUTRAL_H, text_color=TEXT)
        self.style_n.set(str(self.db.get_setting("style_ext_count")))
        self.style_n.pack(side="left", padx=6)
        ctk.CTkLabel(line, text="extensions").pack(side="left")
        self.var_check = tk.BooleanVar(value=bool(self.db.get_setting("check_availability")))
        ctk.CTkSwitch(tab, text="Check if domains look free (quick DNS check)",
                      variable=self.var_check, progress_color=ACCENT).pack(anchor="w", pady=10)

    def _add_ext_checkbox(self, ext, value):
        var = tk.BooleanVar(value=value)
        i = len(self.ext_vars)
        self.ext_vars[ext] = var
        ctk.CTkCheckBox(self.ext_frame, text=f".{ext}", variable=var, width=110
                        ).grid(row=i // 5, column=i % 5, padx=6, pady=4, sticky="w")

    def _set_exts(self, selected):
        for ext, var in self.ext_vars.items():
            var.set(ext in selected)

    def _add_custom(self):
        ext = self.custom_entry.get().strip().lower().lstrip(".")
        if not ext or not all(c.isalnum() or c == "." for c in ext) or len(ext) > 24:
            messagebox.showwarning("Extension", "Use letters/numbers only, e.g.  co.uk")
            return
        if ext not in self.ext_vars:
            self._add_ext_checkbox(ext, True)
        else:
            self.ext_vars[ext].set(True)
        self.custom_entry.delete(0, "end")

    # ---- Search tab
    def _tab_search(self, tab):
        ctk.CTkLabel(tab, text="How often to search", font=ctk.CTkFont(size=15, weight="bold")
                     ).pack(anchor="w", pady=(4, 0))
        self.interval_lbl = ctk.CTkLabel(tab, text="", text_color=MUTED)
        self.interval_lbl.pack(anchor="w")
        self.s_interval = ctk.CTkSlider(tab, from_=20, to=60, number_of_steps=40, width=380,
                                        command=lambda v: self.interval_lbl.configure(
                                            text=f"Every {int(round(v))} minutes"),
                                        button_color=ACCENT, progress_color=ACCENT)
        self.s_interval.set(self.db.get_setting("interval_minutes"))
        self.s_interval.pack(anchor="w", pady=6)
        self.interval_lbl.configure(text=f"Every {int(round(self.s_interval.get()))} minutes")
        self.var_rare = tk.BooleanVar(value=bool(self.db.get_setting("rare_words")))
        ctk.CTkSwitch(tab, text="Also detect unknown/rare words (more results, more noise)",
                      variable=self.var_rare, progress_color=ACCENT).pack(anchor="w", pady=14)
        ctk.CTkLabel(tab, text="Sectors are chosen in the sidebar. Only feeds and searches for the "
                               "ticked sectors are used, and each word is tagged with the sector "
                               "of the article it came from.", text_color=MUTED, wraplength=600,
                     justify="left").pack(anchor="w")

    # ---- App tab
    def _tab_app(self, tab):
        ctk.CTkLabel(tab, text="Appearance", font=ctk.CTkFont(size=15, weight="bold")
                     ).pack(anchor="w", pady=(4, 4))
        self.s_theme = ctk.CTkSegmentedButton(tab, values=["Light", "Dark", "System"],
                                              selected_color=ACCENT, selected_hover_color=ACCENT_H,
                                              command=self.app.set_theme)
        self.s_theme.set(self.db.get_setting("appearance"))
        self.s_theme.pack(anchor="w", pady=(0, 14))
        self.var_tray = tk.BooleanVar(value=bool(self.db.get_setting("minimize_to_tray")))
        self.var_auto = tk.BooleanVar(value=bool(self.db.get_setting("auto_start")))
        self.var_notify = tk.BooleanVar(value=bool(self.db.get_setting("notify")))
        for text, var in (("Hide to the system tray when the window is closed", self.var_tray),
                          ("Start monitoring automatically when the app opens", self.var_auto),
                          ("Show a notification when new terms are found (while hidden)", self.var_notify)):
            ctk.CTkSwitch(tab, text=text, variable=var, progress_color=ACCENT).pack(anchor="w", pady=8)

    def save(self):
        exts = [e for e, v in self.ext_vars.items() if v.get()]
        if not exts:
            messagebox.showwarning("Settings", "Tick at least one domain extension.")
            return
        db = self.db
        db.set_setting("extensions", exts)
        db.set_setting("custom_extensions", [e for e in self.ext_vars if e not in ALL_EXTENSIONS])
        db.set_setting("styles", [k for k, v in self.style_vars.items() if v.get()])
        db.set_setting("style_ext_count", int(self.style_n.get()))
        db.set_setting("check_availability", self.var_check.get())
        db.set_setting("interval_minutes", int(round(self.s_interval.get())))
        db.set_setting("rare_words", self.var_rare.get())
        db.set_setting("minimize_to_tray", self.var_tray.get())
        db.set_setting("auto_start", self.var_auto.get())
        db.set_setting("notify", self.var_notify.get())
        self.app.apply_settings()
        self.destroy()


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        logging.exception("Fatal error")
        raise
