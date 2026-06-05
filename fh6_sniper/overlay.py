"""Overlay di stato + menu impostazioni — tema ROG CecchinoDelleAste."""
from __future__ import annotations
import ctypes
import time
import tkinter as tk

# ── Palette ROG ─────────────────────────────────────────────────────────────
_BORDER   = "#FF0028"   # bordo esterno 1 px — rosso ROG pieno
_BG_HDR   = "#020000"   # header (quasi nero)
_BG       = "#080000"   # corpo principale
_BG_MID   = "#0c0000"   # zona status / pulsante
_BG_BOT   = "#160000"   # footer
_CARD     = "#0e0000"   # card statistiche / campi

_DIVIDER  = "#2a0000"   # separatori
_ROG      = "#FF0028"   # rosso ROG — accento primario
_ROG_DIM  = "#c40020"
_TEXT     = "#f4f4f6"   # testo bianco
_DIM      = "#7a3535"   # testo dimmed rosso-grigio
_FAINT    = "#7a3535"   # etichette card / firma — stesso rosso dei keybind (_DIM)
_AMBER    = "#f0a83c"
_RED_STAT = "#ff4060"
_STOP     = "#b80000"
_STOP_HV  = "#8f0000"
_START_HV = "#cc001e"
_TRACK    = "#3a2222"   # binario spento di toggle/slider

# Colori bandiera italiana per il titolo
_IT_GREEN = "#1aa64b"
_IT_WHITE = "#ffffff"
_IT_RED   = "#e23744"

WIDTH = 344 + 2   # larghezza overlay (+1 px bordo per lato)


# ── Specifica del menu impostazioni ──────────────────────────────────────────
# Ogni voce: chiave del Config, etichetta, descrizione sintetica, tipo di
# controllo e (per i numeri) intervallo/passo. I tuple ("section", "...") sono
# intestazioni di gruppo. resolution e lime_hsv sono volutamente esclusi: non
# vanno cambiati (template tarati su 1080p, rilevamento non basato su HSV).
SETTINGS_SPEC = [
    ("section", "Velocità"),
    {"key": "match_threshold", "label": "Soglia riconoscimento", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Quanto una schermata deve somigliare al template. Più alta = più severa."},
    {"key": "poll_interval_ms", "label": "Intervallo controllo (ms)", "kind": "range",
     "lo": 5, "hi": 150, "step": 1, "int": True,
     "desc": "Ogni quanto ricontrolla lo schermo. Più basso = reagisce prima."},
    {"key": "key_hold_ms", "label": "Tenuta tasti (ms)", "kind": "range",
     "lo": 5, "hi": 80, "step": 1, "int": True,
     "desc": "Durata di ogni pressione. Più bassa = più veloce (troppo bassa perde tasti)."},
    {"key": "between_keys_ms", "label": "Pausa tra tasti (ms)", "kind": "range",
     "lo": 5, "hi": 120, "step": 1, "int": True,
     "desc": "Pausa dopo ogni tasto. Più bassa = navigazione più rapida."},
    {"key": "loop_pace_s", "label": "Pausa tra cicli (s)", "kind": "slider",
     "lo": 0.0, "hi": 1.0, "step": 0.01, "int": False,
     "desc": "Pausa tra una ricerca e l'altra. Più bassa = più tentativi al minuto."},
    {"key": "buyout_select_delay_ms", "label": "Ritardo conferma (ms)", "kind": "slider",
     "lo": 0, "hi": 500, "step": 5, "int": True,
     "desc": "Attesa extra prima di confermare l'acquisto. 0 = massima velocità."},

    ("section", "Stop automatico"),
    {"key": "auto_stop_enabled", "label": "Stop automatico", "kind": "toggle",
     "desc": "Ferma il bot al raggiungimento dei limiti qui sotto."},
    {"key": "max_cars", "label": "Auto da comprare", "kind": "slider",
     "lo": 1, "hi": 100, "step": 1, "int": True,
     "desc": "Quante auto comprare prima di fermarsi."},
    {"key": "max_minutes", "label": "Durata massima (min)", "kind": "slider",
     "lo": 1, "hi": 600, "step": 1, "int": False,
     "desc": "Minuti massimi di esecuzione prima dello stop."},

    ("section", "Comportamento"),
    {"key": "collect_after_buyout", "label": "Ritira dopo l'acquisto", "kind": "toggle",
     "desc": "Ritira subito l'auto comprata (più lento ma automatico)."},
    {"key": "notify_sound", "label": "Suono notifica", "kind": "toggle",
     "desc": "Beep di Windows a ogni acquisto riuscito."},
    {"key": "notify_toast", "label": "Notifica Windows", "kind": "toggle",
     "desc": "Avviso toast di Windows a ogni acquisto."},

    ("section", "Timeout (rete di sicurezza)"),
    {"key": "timeout_results_s", "label": "Timeout risultati (s)", "kind": "slider",
     "lo": 2, "hi": 30, "step": 0.5, "int": False,
     "desc": "Attesa massima dei risultati dopo una ricerca."},
    {"key": "timeout_outcome_s", "label": "Timeout esito (s)", "kind": "slider",
     "lo": 5, "hi": 60, "step": 1, "int": False,
     "desc": "Attesa massima dell'esito dell'acquisto."},
    {"key": "timeout_claim_s", "label": "Timeout ritiro (s)", "kind": "slider",
     "lo": 5, "hi": 60, "step": 1, "int": False,
     "desc": "Attesa massima per il ritiro dell'auto."},
    {"key": "timeout_generic_s", "label": "Timeout generico (s)", "kind": "slider",
     "lo": 2, "hi": 30, "step": 0.5, "int": False,
     "desc": "Attesa massima per altre transizioni di schermata."},

    ("section", "Avanzate (richiedono riavvio)"),
    {"key": "template_dir", "label": "Cartella template", "kind": "text",
     "desc": "Dove stanno le immagini di riconoscimento."},
    {"key": "log_path", "label": "File log acquisti", "kind": "text",
     "desc": "Percorso del CSV con lo storico acquisti."},
    {"key": "hotkey_start_stop", "label": "Tasto avvia/ferma", "kind": "text",
     "desc": "Scorciatoia globale, formato pynput (es. <f8>)."},
    {"key": "hotkey_panic", "label": "Tasto emergenza", "kind": "text",
     "desc": "Scorciatoia globale di stop immediato (es. <f9>)."},
]


# ── Helper puri (testabili senza tkinter) ─────────────────────────────────────
def _slider_value_from_x(x, track_x0, track_w, lo, hi, step, is_int):
    frac = 0.0 if track_w <= 0 else (x - track_x0) / track_w
    frac = max(0.0, min(1.0, frac))
    val = lo + frac * (hi - lo)
    val = round((val - lo) / step) * step + lo
    val = max(lo, min(hi, val))
    return int(round(val)) if is_int else round(val, 4)


def _slider_x_from_value(val, track_x0, track_w, lo, hi):
    frac = 0.0 if hi == lo else (val - lo) / (hi - lo)
    frac = max(0.0, min(1.0, frac))
    return track_x0 + frac * track_w


def _fmt(val, is_int):
    if is_int:
        return str(int(round(val)))
    return f"{val:.2f}".rstrip("0").rstrip(".")


# ── Widget: toggle rotondo ────────────────────────────────────────────────────
class ToggleSwitch(tk.Canvas):
    W, H = 46, 26

    def __init__(self, parent, value=False, command=None, bg=_BG):
        super().__init__(parent, width=self.W, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._value = bool(value)
        self._command = command
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _on_click(self, _e=None):
        self._value = not self._value
        self._draw()
        if self._command:
            self._command(self._value)

    def get(self):
        return self._value

    def set(self, v):
        self._value = bool(v)
        self._draw()

    def _draw(self):
        self.delete("all")
        track = _IT_GREEN if self._value else _TRACK
        W, H = self.W, self.H
        r = H / 2
        # Capsula perfetta: due cerchi alle estremità + rettangolo centrale.
        self.create_oval(0, 0, H, H, fill=track, outline="")
        self.create_oval(W - H, 0, W, H, fill=track, outline="")
        self.create_rectangle(r, 0, W - r, H, fill=track, outline="")
        # Pallino bianco con piccolo margine, scorre a destra quando acceso.
        m = 3
        d = H - 2 * m
        kx = (W - d - m) if self._value else m
        self.create_oval(kx, m, kx + d, m + d, fill="#ffffff", outline="")


# ── Widget: slider moderno ────────────────────────────────────────────────────
class Slider(tk.Canvas):
    H = 24
    KNOB = 14

    def __init__(self, parent, value, lo, hi, step, is_int,
                 width=150, bg=_BG, on_change=None):
        super().__init__(parent, width=width, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._lo, self._hi, self._step, self._int = lo, hi, step, is_int
        self._x0 = self.KNOB // 2 + 1
        self._tw = width - self.KNOB - 2
        self._value = self._coerce(value)
        self._on_change = on_change
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self._draw()

    def _coerce(self, v):
        v = max(self._lo, min(self._hi, v))
        return int(round(v)) if self._int else round(v, 4)

    def get(self):
        return self._value

    def _drag(self, e):
        self._value = _slider_value_from_x(
            e.x, self._x0, self._tw, self._lo, self._hi, self._step, self._int)
        self._draw()
        if self._on_change:
            self._on_change(self._value)

    def _draw(self):
        self.delete("all")
        cy = self.H // 2
        self.create_line(self._x0, cy, self._x0 + self._tw, cy,
                         fill=_TRACK, width=4, capstyle="round")
        kx = _slider_x_from_value(self._value, self._x0, self._tw,
                                  self._lo, self._hi)
        self.create_line(self._x0, cy, kx, cy, fill=_ROG, width=4,
                         capstyle="round")
        r = self.KNOB / 2
        self.create_oval(kx - r, cy - r, kx + r, cy + r,
                         fill="#ffffff", outline=_ROG, width=2)


class Overlay:
    """HUD di stato + menu impostazioni. run() blocca sul mainloop di Tk."""

    def __init__(self, cfg=None, on_save=None, hide_from_capture: bool = True):
        self._cfg = cfg
        self._on_save = on_save
        self._view = "hud"
        self._w = WIDTH
        self._setting_widgets = {}

        self.root = tk.Tk()
        self.root.title("CecchinoDelleAste - V.1.0.2")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg=_BORDER)

        self._status_var   = tk.StringVar(value="Inattivo")
        self._bought_var   = tk.StringVar(value="0")
        self._searches_var = tk.StringVar(value="0")
        self._fails_var    = tk.StringVar(value="0")
        self._time_var     = tk.StringVar(value="00:00")
        self._active  = False
        self._started = None
        self._running = False
        self._drag    = (0, 0)
        self._btn_base  = _ROG
        self._btn_hover = _START_HV

        self._build()
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        margin = 24
        x = self.root.winfo_screenwidth() - self._w - margin
        self.root.geometry(f"{self._w}x{h}+{x}+{margin}")
        if hide_from_capture:
            self._exclude_from_capture()
        self._tick()

    # ── Escludi dalla cattura ──────────────────────────────────────────────
    def _exclude_from_capture(self):
        try:
            user32 = ctypes.windll.user32
            hwnd   = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd   = parent
                parent = user32.GetParent(hwnd)
            user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception:
            pass

    # ── Layout principale ──────────────────────────────────────────────────
    def _build(self):
        inner = tk.Frame(self.root, bg=_BG_HDR)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Frame(inner, bg=_ROG, height=3).pack(fill="x")

        header = tk.Frame(inner, bg=_BG_HDR)
        header.pack(fill="x", padx=16, pady=(13, 0))

        self._dot = tk.Label(header, text="●", bg=_BG_HDR, fg=_DIM,
                             font=("Segoe UI", 9))
        self._dot.pack(side="left")

        title_frame = tk.Frame(header, bg=_BG_HDR)
        title_frame.pack(side="left", padx=(6, 0))
        for chunk, color in (("Cecchi", _IT_GREEN),
                             ("noDel",  _IT_WHITE),
                             ("leAste", _IT_RED)):
            tk.Label(title_frame, text=chunk, bg=_BG_HDR, fg=color,
                     font=("Segoe UI", 11, "bold"),
                     bd=0, padx=0, pady=0, highlightthickness=0).pack(side="left")
        tk.Label(title_frame, text=" - V.1.0.2", bg=_BG_HDR, fg=_TEXT,
                 font=("Segoe UI", 10)).pack(side="left")

        # Chiudi (X) — più a destra
        close = tk.Label(header, text="✕", bg=_BG_HDR, fg=_DIM,
                         font=("Segoe UI", 16), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.root.destroy())
        close.bind("<Enter>", lambda _e: close.config(fg=_ROG))
        close.bind("<Leave>", lambda _e: close.config(fg=_DIM))

        # Ingranaggio impostazioni — alla sinistra della X (solo se c'è il cfg)
        if self._cfg is not None:
            gear = tk.Label(header, text="\u2699", bg=_BG_HDR, fg=_DIM,
                            font=("Segoe UI", 13), cursor="hand2")
            gear.pack(side="right", padx=(0, 12))
            gear.bind("<Button-1>", lambda _e: self._toggle_settings())
            gear.bind("<Enter>", lambda _e: gear.config(fg=_ROG))
            gear.bind("<Leave>", lambda _e: gear.config(fg=_DIM))

        tk.Label(inner, text="Creato da d1ablo", bg=_BG_HDR, fg=_FAINT,
                 font=("Segoe UI", 7)).pack(anchor="w", padx=36, pady=(1, 0))

        for w in (header, self._dot, title_frame, inner):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        tk.Frame(inner, bg=_DIVIDER, height=1).pack(fill="x", padx=16, pady=(12, 0))

        # Corpo scambiabile: HUD <-> Impostazioni
        self._body = tk.Frame(inner, bg=_BG)
        self._body.pack(fill="both", expand=True)
        self._hud_body = tk.Frame(self._body, bg=_BG)
        self._build_hud(self._hud_body)
        self._hud_body.pack(fill="both", expand=True)

        if self._cfg is not None:
            self._settings_body = tk.Frame(self._body, bg=_BG)
            self._build_settings(self._settings_body)

    def _build_hud(self, parent):
        status_bg = tk.Frame(parent, bg=_BG_MID)
        status_bg.pack(fill="x")
        self._status = tk.Label(
            status_bg, textvariable=self._status_var, bg=_BG_MID, fg=_ROG,
            font=("Segoe UI", 12, "bold"), anchor="center",
            justify="center", wraplength=300, height=2)
        self._status.pack(fill="x", padx=16, pady=(10, 0))

        self._build_stats(parent)

        btn_wrap = tk.Frame(parent, bg=_BG_MID)
        btn_wrap.pack(fill="x", padx=16, pady=(13, 0))
        self._btn = tk.Button(
            btn_wrap, text="AVVIA", font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", height=2)
        self._btn.pack(fill="x")
        self._btn.bind("<Enter>", lambda _e: self._btn.config(bg=self._btn_hover))
        self._btn.bind("<Leave>", lambda _e: self._btn.config(bg=self._btn_base))
        self._set_button(running=False)

        footer = tk.Frame(parent, bg=_BG_BOT)
        footer.pack(fill="x")
        tk.Label(footer, text="F8  avvia / ferma          F9  emergenza",
                 bg=_BG_BOT, fg=_DIM, font=("Segoe UI", 8)).pack(pady=(11, 14))

    def _build_stats(self, parent):
        card = tk.Frame(parent, bg=_CARD)
        card.pack(fill="x", padx=16, pady=(12, 0))
        cells = (
            ("ACQUISTATI", self._bought_var,   _IT_GREEN),
            ("RICERCHE",   self._searches_var,  _TEXT),
            ("FALLITI",    self._fails_var,      _RED_STAT),
            ("ATTIVO",     self._time_var,       _TEXT),
        )
        for i, (caption, var, color) in enumerate(cells):
            if i:
                tk.Frame(card, bg=_DIVIDER, width=1).pack(
                    side="left", fill="y", pady=10)
            cell = tk.Frame(card, bg=_CARD)
            cell.pack(side="left", expand=True, fill="both")
            tk.Label(cell, textvariable=var, bg=_CARD, fg=color,
                     font=("Segoe UI", 15, "bold")).pack(pady=(11, 0))
            tk.Label(cell, text=caption, bg=_CARD, fg=_FAINT,
                     font=("Segoe UI", 7)).pack(pady=(2, 11))

    # ── Menu impostazioni ──────────────────────────────────────────────────
    def _build_settings(self, parent):
        head = tk.Frame(parent, bg=_BG_MID)
        head.pack(fill="x")
        back = tk.Label(head, text="\u2039  Impostazioni", bg=_BG_MID, fg=_ROG,
                        font=("Segoe UI", 11, "bold"), cursor="hand2")
        back.pack(side="left", padx=16, pady=10)
        back.bind("<Button-1>", lambda _e: self._show_hud())
        back.bind("<Enter>", lambda _e: back.config(fg=_TEXT))
        back.bind("<Leave>", lambda _e: back.config(fg=_ROG))

        # Area scorrevole
        area = tk.Frame(parent, bg=_BG)
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, bg=_BG, highlightthickness=0, height=360,
                           width=self._w - 4)
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=_BG)
        win = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
                  lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))

        def _wheel(e):
            canvas.yview_scroll(int(-e.delta / 120), "units")
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        for spec in SETTINGS_SPEC:
            if isinstance(spec, tuple) and spec[0] == "section":
                tk.Label(body, text=spec[1].upper(), bg=_BG, fg=_ROG,
                         font=("Segoe UI", 8, "bold")).pack(
                             anchor="w", padx=16, pady=(14, 2))
                tk.Frame(body, bg=_DIVIDER, height=1).pack(
                    fill="x", padx=16, pady=(0, 4))
            else:
                self._add_setting_row(body, spec)

        # Pulsante SALVA
        self._save_btn = tk.Button(
            parent, text="SALVA E APPLICA", font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", height=2,
            bg=_ROG, fg="#ffffff", activebackground=_START_HV,
            activeforeground="#ffffff", command=self._save_settings)
        self._save_btn.pack(fill="x", padx=16, pady=(8, 14))
        self._save_btn.bind(
            "<Enter>", lambda _e: self._save_btn.config(bg=_START_HV))
        self._save_btn.bind(
            "<Leave>", lambda _e: self._save_btn.config(bg=_ROG))

    def _add_setting_row(self, parent, spec):
        key, kind = spec["key"], spec["kind"]
        cur = getattr(self._cfg, key, None)
        row = tk.Frame(parent, bg=_BG)
        row.pack(fill="x", padx=16, pady=(6, 0))

        top = tk.Frame(row, bg=_BG)
        top.pack(fill="x")
        tk.Label(top, text=spec["label"], bg=_BG, fg=_TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")

        if kind == "toggle":
            tg = ToggleSwitch(top, value=bool(cur), bg=_BG)
            tg.pack(side="right")
            self._setting_widgets[key] = ("toggle", tg)

        elif kind == "slider":
            val_var = tk.StringVar(value=_fmt(cur, spec["int"]))
            tk.Label(top, textvariable=val_var, bg=_BG, fg=_ROG,
                     font=("Segoe UI", 9, "bold")).pack(side="right")
            sl = Slider(row, value=cur, lo=spec["lo"], hi=spec["hi"],
                        step=spec["step"], is_int=spec["int"],
                        width=self._w - 36, bg=_BG,
                        on_change=lambda v, var=val_var, i=spec["int"]:
                            var.set(_fmt(v, i)))
            sl.pack(fill="x", pady=(4, 0))
            self._setting_widgets[key] = ("slider", sl)

        elif kind == "range":
            lo_cur, hi_cur = (cur if isinstance(cur, (tuple, list))
                              else (spec["lo"], spec["hi"]))
            pair_frame = tk.Frame(row, bg=_BG)
            pair_frame.pack(fill="x", pady=(4, 0))
            sliders = []
            for sub, sval in (("min", lo_cur), ("max", hi_cur)):
                line = tk.Frame(pair_frame, bg=_BG)
                line.pack(fill="x", pady=1)
                tk.Label(line, text=sub, bg=_BG, fg=_DIM,
                         font=("Segoe UI", 8), width=4, anchor="w").pack(side="left")
                vv = tk.StringVar(value=_fmt(sval, spec["int"]))
                tk.Label(line, textvariable=vv, bg=_BG, fg=_ROG,
                         font=("Segoe UI", 8, "bold"), width=4,
                         anchor="e").pack(side="right")
                s = Slider(line, value=sval, lo=spec["lo"], hi=spec["hi"],
                           step=spec["step"], is_int=spec["int"],
                           width=self._w - 90, bg=_BG,
                           on_change=lambda v, var=vv, i=spec["int"]:
                               var.set(_fmt(v, i)))
                s.pack(side="right", padx=(6, 6))
                sliders.append(s)
            self._setting_widgets[key] = ("range", tuple(sliders))

        elif kind == "text":
            ent = tk.Entry(row, bg=_CARD, fg=_TEXT, insertbackground=_TEXT,
                           relief="flat", font=("Segoe UI", 9),
                           highlightthickness=1, highlightbackground=_DIVIDER,
                           highlightcolor=_ROG)
            ent.insert(0, "" if cur is None else str(cur))
            ent.pack(fill="x", pady=(4, 0), ipady=3)
            self._setting_widgets[key] = ("text", ent)

        tk.Label(row, text=spec["desc"], bg=_BG, fg=_DIM,
                 font=("Segoe UI", 7), anchor="w", justify="left",
                 wraplength=self._w - 40).pack(fill="x", pady=(2, 0))
        tk.Frame(row, bg=_BG, height=2).pack()

    def _collect(self):
        out = {}
        for key, (kind, w) in self._setting_widgets.items():
            if kind == "range":
                out[key] = (kind, (w[0].get(), w[1].get()))
            else:
                out[key] = (kind, w.get())
        return out

    @staticmethod
    def _apply_collected(cfg, collected):
        for key, (kind, val) in collected.items():
            if kind == "toggle":
                setattr(cfg, key, bool(val))
            elif kind == "slider":
                setattr(cfg, key, val)
            elif kind == "range":
                a, b = val
                lo, hi = (a, b) if a <= b else (b, a)
                setattr(cfg, key, (lo, hi))
            elif kind == "text":
                setattr(cfg, key, str(val).strip())

    def _save_settings(self):
        if self._cfg is None:
            return
        self._apply_collected(self._cfg, self._collect())   # applica subito
        if self._on_save:
            try:
                self._on_save(self._cfg)                     # persiste su disco
            except Exception:
                pass
        self._save_btn.config(text="SALVATO \u2713", bg=_IT_GREEN)
        self.root.after(1100, lambda: self._save_btn.config(
            text="SALVA E APPLICA", bg=_ROG))

    # ── Scambio viste ──────────────────────────────────────────────────────
    def _toggle_settings(self):
        self._show_hud() if self._view == "settings" else self._show_settings()

    def _show_settings(self):
        self._hud_body.pack_forget()
        self._settings_body.pack(fill="both", expand=True)
        self._view = "settings"
        self._fit()

    def _show_hud(self):
        self._settings_body.pack_forget()
        self._hud_body.pack(fill="both", expand=True)
        self._view = "hud"
        self._fit()

    def _fit(self):
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        try:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        except Exception:
            x, y = 24, 24
        self.root.geometry(f"{self._w}x{h}+{x}+{y}")

    # ── Drag ───────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        self.root.geometry(
            f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    # ── Pulsante AVVIA/FERMA ───────────────────────────────────────────────
    def _set_button(self, running: bool):
        if running:
            text, base, hover, fg = "FERMA", _STOP, _STOP_HV, "#ffffff"
        else:
            text, base, hover, fg = "AVVIA", _ROG, _START_HV, "#ffffff"
        self._btn_base, self._btn_hover = base, hover
        self._btn.config(text=text, bg=base, fg=fg,
                         activebackground=hover, activeforeground=fg)

    # ── Stato ──────────────────────────────────────────────────────────────
    def _retint(self):
        """Colora dot e testo in base allo stato REALE (running flag) + testo."""
        text = self._status_var.get().lower()
        if not self._running:
            color = _DIM
        elif "in pausa" in text:
            color = _AMBER
        else:
            color = _ROG
        self._dot.config(fg=color)
        self._status.config(fg=color)

    def _apply_status(self, text: str):
        # Solo messaggio + colore. Il PULSANTE non dipende più dal testo:
        # è guidato da set_running() (stato reale del thread), così dopo
        # auto-stop / stop / crash torna sempre correttamente su AVVIA.
        self._status_var.set(text)
        self._retint()

    def _apply_running(self, running: bool):
        self._running = bool(running)
        self._set_button(self._running)
        self._active = self._running
        if self._running and self._started is None:
            self._started = time.monotonic()
            self._time_var.set("00:00")
        self._retint()

    def _apply_stats(self, searches: int, bought: int, fails: int):
        self._searches_var.set(str(searches))
        self._bought_var.set(str(bought))
        self._fails_var.set(str(fails))

    def _tick(self):
        if self._active and self._started is not None:
            m, s = divmod(int(time.monotonic() - self._started), 60)
            self._time_var.set(f"{m:02d}:{s:02d}")
        try:
            self.root.after(1000, self._tick)
        except RuntimeError:
            pass

    # ── API pubblica ───────────────────────────────────────────────────────
    def set_status(self, text: str):
        try:
            self.root.after(0, self._apply_status, text)
        except RuntimeError:
            pass

    def set_running(self, running: bool):
        """Stato reale di esecuzione (thread vivo o no). Guida il pulsante."""
        try:
            self.root.after(0, self._apply_running, running)
        except RuntimeError:
            pass

    def set_stats(self, searches: int, bought: int, fails: int):
        try:
            self.root.after(0, self._apply_stats, searches, bought, fails)
        except RuntimeError:
            pass

    def on_toggle(self, callback):
        self._btn.config(command=callback)

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
