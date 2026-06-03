"""Configuration dataclass e load/save su JSON.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class Config:
    # ── Gioco / cattura ──────────────────────────────────────────────────
    # Titolo ESATTO della finestra del gioco da catturare e portare in primo
    # piano. Deve combaciare con la barra del titolo di FH6. Non influisce
    # sulla velocita'.
    window_title: str = "Forza Horizon 6"

    # Risoluzione canonica interna a cui ogni frame viene normalizzato. I
    # template sono tarati su 1080p: NON cambiare, vale per qualsiasi
    # risoluzione di gioco (la cattura viene comunque riportata a 1920x1080).
    resolution: tuple = (1920, 1080)

    # ── Riconoscimento schermate ─────────────────────────────────────────
    # Soglia di somiglianza (0.0-1.0) per riconoscere una schermata dai
    # template. Piu' ALTA = piu' severa (meno errori, ma rischia di non
    # riconoscere una schermata); piu' BASSA = riconosce piu' facilmente ma
    # puo' confondere schermate simili. 0.80 e' il buon compromesso.
    # - se una schermata NON viene riconosciuta: prova ad abbassare a 0.75
    # - se riconosce la schermata SBAGLIATA: alza a 0.83-0.85
    # Non e' una leva di velocita' diretta.
    match_threshold: float = 0.80

    # Intervallo colore lime (HSV) usato SOLO da una utility secondaria; il
    # rilevamento di Conferma e del timbro VENDUTO non lo usa piu'. Lasciare
    # invariato.
    lime_hsv_lower: tuple = (32, 110, 110)
    lime_hsv_upper: tuple = (52, 255, 255)

    # ── Timing degli input (LEVE DI VELOCITA') ───────────────────────────
    # [min, max] millisecondi di tenuta di ogni tasto, scelti a caso
    # nell'intervallo (per non sembrare meccanici).
    # PIU' BASSO = piu' veloce. Troppo basso e il gioco puo' "perdere"
    # pressioni: per velocizzare prova [10, 20]; se saltano tasti, rialza.
    key_hold_ms: tuple = (20, 45)

    # [min, max] millisecondi di pausa DOPO ogni tasto, prima del successivo.
    # PIU' BASSO = navigazione piu' rapida. Per velocizzare prova [10, 20];
    # se il gioco perde input, rialza.
    between_keys_ms: tuple = (20, 55)

    # [min, max] millisecondi tra un controllo dello schermo e l'altro mentre
    # il bot ASPETTA che una schermata cambi. E' la leva di velocita' PIU'
    # importante: piu' BASSO = reagisce prima all'apparire dei risultati e
    # all'esito del buyout (cruciale per lo sniping).
    # Per velocizzare: [15, 30]. Troppo basso = piu' uso di CPU.
    poll_interval_ms: tuple = (40, 90)

    # Ritardo extra (ms) prima di confermare il buyout. Tenere 0 per la
    # massima velocita'; aumentare SOLO se il gioco non registra in tempo la
    # selezione dell'acquisto.
    buyout_select_delay_ms: int = 0

    # ── Timeout (reti di sicurezza, in secondi) ──────────────────────────
    # Questi NON velocizzano il caso normale (il bot esce dall'attesa appena
    # vede la schermata giusta): servono solo a non restare bloccato per
    # sempre se qualcosa non arriva.
    # Secondi massimi di attesa dei risultati dopo una ricerca prima di
    # rinunciare e riprovare. Abbassarlo = rinuncia prima a ricerche
    # lente/vuote e ricomincia.
    timeout_results_s: float = 12.0

    # Secondi massimi di attesa dell'esito del buyout (riuscito/fallito) dopo
    # l'avvio dell'acquisto. Lasciare ampio.
    timeout_outcome_s: float = 25.0

    # Secondi massimi per completare il ritiro dell'auto dopo l'acquisto.
    timeout_claim_s: float = 20.0

    # Timeout generico per altre attese minori.
    timeout_generic_s: float = 10.0

    # Pausa tra un ciclo completo e il successivo. PIU' BASSO = ricerche
    # ripetute piu' frequenti, quindi piu' tentativi di sniping al minuto.
    # Per velocizzare: 0.02 o 0.0. A 0 massimizza i tentativi ma carica di
    # piu' CPU e gioco.
    loop_pace_s: float = 0.15

    # ── Stop automatico ──────────────────────────────────────────────────
    # Se True, il bot si ferma da solo al raggiungimento di max_cars OPPURE
    # di max_minutes. Non influisce sulla velocita'.
    auto_stop_enabled: bool = True

    # Numero di auto da comprare prima di fermarsi (se auto_stop_enabled).
    max_cars: int = 1

    # Minuti massimi di esecuzione prima dello stop automatico.
    max_minutes: float = 180.0

    # ── Comportamento ────────────────────────────────────────────────────
    # Se True, dopo ogni acquisto esegue anche il RITIRO dell'auto. Metterlo
    # a False fa risparmiare tempo dopo ogni acquisto (dovrai ritirare le
    # auto a mano dai messaggi), utile se vuoi accaparrarne il piu' possibile
    # in fretta.
    collect_after_buyout: bool = True

    # Beep di Windows a ogni acquisto riuscito.
    notify_sound: bool = True

    # Notifica "toast" di Windows a ogni acquisto riuscito.
    notify_toast: bool = True

    # ── Percorsi ─────────────────────────────────────────────────────────
    # File CSV con lo storico degli acquisti.
    log_path: str = "logs/purchases.csv"

    # Cartella che contiene i template (immagini) per il riconoscimento delle
    # schermate.
    template_dir: str = "templates"

    # ── Scorciatoie globali (formato pynput) ─────────────────────────────
    # Tasto per avviare/fermare il bot. Es. "<f8>".
    hotkey_start_stop: str = "<f8>"

    # Tasto di emergenza per fermare subito il bot. Es. "<f9>".
    hotkey_panic: str = "<f9>"


_TUPLE_FIELDS = {
    name for name, f in Config.__dataclass_fields__.items()
    if isinstance(f.default, tuple)
}


def load_config(path=DEFAULT_CONFIG_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        cfg = Config()
        save_config(cfg, path)
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in _TUPLE_FIELDS:
        if key in data and isinstance(data[key], list):
            data[key] = tuple(data[key])
    known = set(Config.__dataclass_fields__)
    cfg = Config(**{k: v for k, v in data.items() if k in known})
    for key, value in data.items():
        if key not in known:
            setattr(cfg, key, value)
    if not known.issubset(data.keys()):
        save_config(cfg, path)
    return cfg


def save_config(cfg: Config, path=DEFAULT_CONFIG_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    declared = set(Config.__dataclass_fields__)
    for key, value in cfg.__dict__.items():
        if key not in declared:
            data[key] = value
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
