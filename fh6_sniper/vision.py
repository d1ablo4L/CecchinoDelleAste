"""Screen identification: template matching e rilevamento universale SDR/HDR."""
from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
import cv2
import numpy as np


class Screen(Enum):
    UNKNOWN = auto()
    SEARCH_CONFIG = auto()
    RESULTS_HAS_CARS = auto()
    RESULTS_EMPTY = auto()
    AUCTION_OPTIONS = auto()
    PLAYER_OPTIONS = auto()
    BUY_OUT = auto()
    BUYOUT_PROGRESS = auto()
    BUYOUT_SUCCESS = auto()
    BUYOUT_FAILED = auto()
    CLAIM_CAR = auto()
    AH_LANDING = auto()


TEMPLATE_SCREENS: dict[str, Screen] = {
    "search.png": Screen.SEARCH_CONFIG,
    "auction_details.png": Screen.RESULTS_HAS_CARS,
    "no_auctions.png": Screen.RESULTS_EMPTY,
    "auction_options.png": Screen.AUCTION_OPTIONS,
    "player_options.png": Screen.PLAYER_OPTIONS,
    "buy_out.png": Screen.BUY_OUT,
    "buy_out_bgoff.png": Screen.BUY_OUT,
    "buy_out_progress.png": Screen.BUYOUT_PROGRESS,
    "buy_out_progress_bgoff.png": Screen.BUYOUT_PROGRESS,
    "buyout_successful.png": Screen.BUYOUT_SUCCESS,
    "buyout_failed.png": Screen.BUYOUT_FAILED,
    "claim_car.png": Screen.CLAIM_CAR,
    "ah_landing.png": Screen.AH_LANDING,
}


# ── Utility HSV (mantenuta per compatibilità) ─────────────────────────────────
def lime_mask(bgr: np.ndarray, lower, upper) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))


def largest_lime_bbox(bgr, lower, upper):
    """Bounding box della più grande regione lime a forma di banner, o None."""
    mask = lime_mask(bgr, lower, upper)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 2000:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if h <= 0 or w / h < 4.0:
            continue
        if area > best_area:
            best_area = area
            best = (x, y, w, h)
    return best


# ── Template matching ─────────────────────────────────────────────────────────
def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def match_template(scene: np.ndarray, template: np.ndarray) -> float:
    """Miglior punteggio NCC del template nella scena. 0.0 se il template è troppo grande."""
    s, t = _gray(scene), _gray(template)
    if t.shape[0] > s.shape[0] or t.shape[1] > s.shape[1]:
        return 0.0
    result = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


_DOWNSCALED_TEMPLATES: dict[int, np.ndarray] = {}


def _small(tmpl: np.ndarray) -> np.ndarray:
    key = id(tmpl)
    cached = _DOWNSCALED_TEMPLATES.get(key)
    if cached is None:
        cached = _downscale(tmpl)
        _DOWNSCALED_TEMPLATES[key] = cached
    return cached


def load_templates(template_dir) -> dict:
    """Carica ogni template di rilevamento in scala di grigi.
    Lancia FileNotFoundError se un template obbligatorio manca.

    Il tool funziona ESCLUSIVAMENTE con lo sfondo in movimento ("moving
    background") OFF nel gioco: dove esiste una variante _bgoff si usa sempre
    quella, e i template "background ON" corrispondenti vengono ignorati. Non
    c'e' piu' alcun flag da controllare.

    Il matching avviene sempre su frame normalizzati a 1920×1080, quindi
    i template a 1080p funzionano per qualsiasi risoluzione di gioco.
    """
    out = {}
    for name in TEMPLATE_SCREENS:
        # Esiste una variante _bgoff per questo template? Allora salta questo
        # (versione background ON) e carica solo la _bgoff.
        if _has_bgoff_variant(name):
            continue
        path = Path(template_dir) / name
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"template mancante: {path}")
        gray = _gray(img)
        out[name] = gray
        _DOWNSCALED_TEMPLATES[id(gray)] = _downscale(gray)
    return out


def _has_bgoff_variant(name: str) -> bool:
    if name.endswith("_bgoff.png"):
        return False
    sibling = name[:-len(".png")] + "_bgoff.png"
    return sibling in TEMPLATE_SCREENS


_RESULTS_PRIORITY = ("auction_details.png", "no_auctions.png")
_MATCH_SCALE = 0.5


def _downscale(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, None, fx=_MATCH_SCALE, fy=_MATCH_SCALE,
                      interpolation=cv2.INTER_AREA)


# Regioni di ricerca dei template. NON sono tutte centrate sullo schermo:
# alcuni elementi (es. "Dettagli asta", messaggio "nessuna asta") vivono nel
# PANNELLO DI DESTRA, centrati a ~x=1409, non a x=960. Cambiare lingua cambia
# solo la *larghezza* del testo, non la posizione: quindi ogni regione conserva
# il proprio centro (verificato su screenshot reale del gioco in italiano) e
# l'unica modifica rispetto all'originale e' l'allargamento di no_auctions, il
# cui template italiano (650 px, due righe) non entrava nella regione vecchia.
# Verifiche su frame reale: auction_details -> match 0.86 (picco x969,y154);
# ah_landing -> 0.95 (picco x72,y99).
TEMPLATE_REGIONS = {
    "search.png":                (472, 223, 1448, 471),
    "auction_details.png":       (889,  64, 1920, 294),   # banner pannello destro
    "no_auctions.png":           (700, 410, 1780, 720),   # allargata: copre pannello e centro
    "auction_options.png":       (546, 276, 1374, 526),
    "player_options.png":        (580, 230, 1340, 486),
    "buy_out.png":               (520, 470, 1400, 620),
    "buy_out_bgoff.png":         (520, 470, 1400, 620),
    "buy_out_progress.png":      (520, 470, 1400, 620),
    "buy_out_progress_bgoff.png":(520, 470, 1400, 620),
    "buyout_successful.png":     (539, 334, 1374, 612),
    "buyout_failed.png":         (546, 378, 1374, 631),
    "claim_car.png":             (538, 359, 1374, 615),
    "ah_landing.png":            (16,   89,  387, 291),
}

_FULL_RES_TEMPLATES = {
    "buy_out.png", "buy_out_bgoff.png",
    "buy_out_progress.png", "buy_out_progress_bgoff.png",
}


def screen_scores(scene_bgr, templates: dict, targets=None) -> dict:
    """Punteggio di matching per template, crop-regione.
    Il matching in scala di grigi è già indipendente da SDR/HDR e risoluzione.
    """
    if targets is not None:
        wanted = set(_RESULTS_PRIORITY)
        wanted |= {n for n, scr in TEMPLATE_SCREENS.items() if scr in targets}
        templates = {n: t for n, t in templates.items() if n in wanted}
    gray = _gray(scene_bgr)
    h, w = gray.shape[:2]
    scores = {}
    for name, tmpl in templates.items():
        region = TEMPLATE_REGIONS.get(name)
        if region:
            x1, y1, x2, y2 = region
            crop = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            crop = gray
        if name in _FULL_RES_TEMPLATES:
            scores[name] = match_template(crop, tmpl)
        else:
            scores[name] = match_template(_downscale(crop), _small(tmpl))
    return scores


def identify_screen(scene_bgr, templates: dict, threshold: float,
                    targets=None) -> Screen:
    scores = screen_scores(scene_bgr, templates, targets=targets)
    for name in _RESULTS_PRIORITY:
        if scores.get(name, 0.0) >= threshold:
            return TEMPLATE_SCREENS[name]
    best_screen, best_score = Screen.UNKNOWN, threshold
    for name, score in scores.items():
        if score >= best_score:
            best_screen, best_score = TEMPLATE_SCREENS[name], score
    return best_screen


# ── Rilevamento pulsante Conferma ─────────────────────────────────────────────
CONFIRM_ROW = (548, 714, 1372, 772)

# Soglie basate sul canale V (luminosità) invece di un hue specifico.
# Il pulsante evidenziato — lime in SDR, o qualsiasi colore brillante in HDR —
# ha sempre luminosità V significativamente maggiore dello sfondo UI scuro.
# Funziona per SDR, HDR, qualsiasi temperatura colore e gamma display.
_CONFIRM_V_THRESH  = 130   # soglia canale V: pixel "acceso"
_CONFIRM_V_COUNT   = 500   # numero minimo di pixel accesi per considerarlo evidenziato


def is_confirm_highlighted(scene_bgr, region=CONFIRM_ROW) -> bool:
    """True se il pulsante Conferma è evidenziato.

    Usa il canale V (luminosità) dell'HSV: il pulsante evidenziato è sempre
    molto più luminoso dello sfondo UI scuro, indipendentemente dal color
    space (SDR/HDR), dalla risoluzione o dalla calibrazione del display.
    Non richiede template aggiuntivi.
    """
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    v = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]
    _, bright = cv2.threshold(v, _CONFIRM_V_THRESH, 255, cv2.THRESH_BINARY)
    return int(cv2.countNonZero(bright)) > _CONFIRM_V_COUNT


# ── Rilevamento timbro SOLD ───────────────────────────────────────────────────
SOLD_STAMP_REGION = (90, 185, 300, 295)

# Il timbro "VENDUTO!" e' una fascia LIME piena sopra la miniatura dell'auto.
# NON basta cercare "colore vivace": la foto dell'auto (qualunque colore) e'
# gia' vivace e generava falsi positivi (un'auto arancione disponibile dava
# ~4600 pixel "vivaci" -> marcata venduta per errore). La discriminante e'
# l'HUE LIME specifico del timbro: si filtra solo quella tinta.
#
# Misure su frame reali (1920x1080):
#   - 4 auto arancioni DISPONIBILI -> 0 pixel lime in tutti gli slot
#   - 1 auto VENDUTA               -> ~3000 pixel lime nello slot venduto
# La selezione (bordo lime della card) e i badge timer ("1 minuto", lime) non
# cadono dentro le regioni del timbro, quindi non interferiscono.
#
# Banda hue ampia (24-50) per tollerare lo spostamento di tinta in HDR; S e V
# alti perche' il timbro e' un lime pieno e brillante, non un verde spento.
_SOLD_H_LO         = 24    # hue minimo lime
_SOLD_H_HI         = 50    # hue massimo lime
_SOLD_S_THRESH     = 100   # saturazione minima: lime pieno, non colori smorti
_SOLD_V_THRESH     = 100   # luminosità minima: timbro brillante
_SOLD_PIXEL_COUNT  = 700   # pixel lime necessari per "VENDUTO" (margine ampio)

SOLD_STAMP_REGIONS = (
    SOLD_STAMP_REGION,
    (90, 387, 300, 497),
    (90, 589, 300, 699),
    (90, 791, 300, 901),
)


def _lime_mask(hsv: np.ndarray) -> np.ndarray:
    """Maschera dei pixel lime del timbro VENDUTO."""
    return cv2.inRange(
        hsv,
        np.array([_SOLD_H_LO, _SOLD_S_THRESH, _SOLD_V_THRESH], np.uint8),
        np.array([_SOLD_H_HI, 255, 255], np.uint8))


def is_card_sold(scene_bgr, region=SOLD_STAMP_REGION) -> bool:
    """True se la card mostra il timbro VENDUTO (fascia lime sulla miniatura).

    Filtra l'hue lime specifico del timbro: la foto dell'auto (qualunque
    colore) non lo attiva. Funziona in SDR e HDR (banda hue ampia).
    """
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return int(cv2.countNonZero(_lime_mask(hsv))) > _SOLD_PIXEL_COUNT


def sold_slots(scene_bgr) -> tuple:
    """Flag VENDUTO per ognuno dei quattro slot risultato (timbro lime)."""
    hsv = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2HSV)
    mask = _lime_mask(hsv)
    return tuple(int(cv2.countNonZero(mask[y1:y2, x1:x2])) > _SOLD_PIXEL_COUNT
                 for (x1, y1, x2, y2) in SOLD_STAMP_REGIONS)


def first_buyable_slot(scene_bgr) -> int:
    """Primo slot non venduto (indice 1-4), o 0 se tutti e quattro sono venduti."""
    for i, sold in enumerate(sold_slots(scene_bgr), start=1):
        if not sold:
            return i
    return 0
