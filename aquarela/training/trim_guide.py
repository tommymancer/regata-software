"""Trim guide — recommended sail/rigging settings by wind and point of sail.

Encodes tuning knowledge for the Nitro 80 'Aquarela' as a lookup table.
Returns step-by-step recommendations for current conditions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class TrimStep:
    """One step in the guided trim procedure."""
    order: int
    control: str            # key matching TrimSnapshot fields
    label: str              # display name (Italian)
    setting: str            # "light", "medium", "heavy"
    instruction: str        # brief Italian explanation of what to do
    why: str                # brief Italian explanation of why
    test: str               # how to verify the setting is correct


# Wind ranges
LIGHT = (0, 8)
MEDIUM = (8, 14)
HEAVY = (14, 25)

WIND_RANGES = [
    ("light", LIGHT, "Aria leggera"),
    ("medium", MEDIUM, "Vento medio"),
    ("heavy", HEAVY, "Vento forte"),
]


def _wind_range(tws: float) -> str:
    if tws < 8:
        return "light"
    if tws < 14:
        return "medium"
    return "heavy"


def _point_of_sail(twa: float) -> str:
    abs_twa = abs(twa)
    if abs_twa < 70:
        return "upwind"
    if abs_twa < 110:
        return "reach"
    return "downwind"


# ── Trim tables ──────────────────────────────────────────────────────
# (wind_range, point_of_sail) → list of (control, setting, instruction, why)
#
# Order matters: we go from rig base → sails → fine-tune.
# This is the standard Nitro 80 tuning sequence.

_UPWIND_LIGHT: List[Tuple[str, str, str, str, str, str]] = [
    ("forestay", "Strallo", "light",
     "Lasca lo strallo per avere piu grasso nella vela",
     "In aria leggera serve potenza: lo strallo lasco crea piu pancia nel fiocco",
     "Guarda la curva dello strallo sottovento: deve avere un leggero insaccamento. Controlla il profilo del fiocco — deve essere grasso e pieno"),
    ("jib_halyard", "Drizza Fiocco", "light",
     "Drizza appena in tensione, piccole pieghe sul bordo d'entrata",
     "Le pieghe sul luff indicano il giusto grasso per aria leggera",
     "Controlla il bordo d'entrata del fiocco: devono esserci piccole pieghe orizzontali lungo il luff. Se e liscio, la drizza e troppo cazzata"),
    ("jib_lead", "Carrello Fiocco", "heavy",
     "Carrello a poppa per svergolare il fiocco",
     "Lo svergolamento in alto scarica la balumina e aiuta in aria leggera",
     "TEST CLASSICO: Orza lentamente e guarda dove sfila prima il fiocco. Se sfila prima in alto = OK (carrello a poppa). Se sfila prima in basso = carrello troppo a poppa, portalo avanti"),
    ("cunningham", "Cunningham", "light",
     "Cunningham completamente lasco",
     "Nessuna tensione: il grasso resta avanti nella randa",
     "Guarda il profilo della randa di taglio: il punto di grasso massimo deve essere al 40-50% dal luff. Se e troppo indietro, il cunningham e troppo lasco (ma in leggera va bene cosi)"),
    ("outhaul", "Borosa", "light",
     "Borosa lasca — pancia piena sulla base",
     "In poco vento serve forma per generare portanza",
     "Misura la distanza tra boma e punto piu profondo della base randa: deve essere circa un palmo (15-20 cm). Se e piatto, lasca ancora"),
    ("vang", "Vang", "light",
     "Vang lasco, solo appoggio",
     "La balumina resta aperta, scaricando la randa in alto",
     "Lasca la scotta di 15 cm e guarda la stecca in alto: deve aprirsi liberamente sottovento. Se resta chiusa, il vang e troppo cazzato"),
    ("traveller", "Carrello Randa", "heavy",
     "Carrello sopravvento, randa a centro barca o oltre",
     "Porta la randa in centro senza tirare la scotta, mantieni la forma",
     "Controlla il filetto in alto sulla balumina della randa: deve volare libero quasi sempre (80-100%). Se stalla, il carrello e troppo alto"),
]

_UPWIND_MEDIUM: List[Tuple[str, str, str, str, str, str]] = [
    ("forestay", "Strallo", "medium",
     "Strallo in tensione media",
     "Riduce il grasso del fiocco per la bolina ottimale",
     "Guarda lo strallo di lato: deve essere quasi dritto con minimo insaccamento. Il fiocco deve avere un profilo moderato, non troppo grasso"),
    ("jib_halyard", "Drizza Fiocco", "medium",
     "Drizza in tensione — niente pieghe sul bordo d'entrata",
     "Luff teso per mantenere il flusso laminare",
     "Il luff del fiocco deve essere completamente liscio, senza pieghe. Il punto di grasso massimo deve essere al 35-40% dal bordo d'entrata"),
    ("jib_lead", "Carrello Fiocco", "medium",
     "Carrello in posizione media",
     "Bilanciamento tra potenza e puntata",
     "TEST CLASSICO: Orza lentamente — il fiocco deve sfilare uniformemente da cima a fondo, tutti i filetti si alzano insieme. Se sfila prima in alto, porta avanti; se prima in basso, porta a poppa"),
    ("cunningham", "Cunningham", "medium",
     "Leggera tensione sul cunningham",
     "Sposta il grasso avanti per mantenere la randa efficiente",
     "Il grasso della randa deve essere al 40-50% dal luff. Non devono esserci pieghe diagonali dal punto di mura — se ci sono, e troppo cazzato"),
    ("outhaul", "Borosa", "medium",
     "Borosa a meta — forma moderata",
     "Bilancia tra grasso per potenza e piattezza per puntata",
     "La pancia sulla base randa deve essere circa mezzo pugno dal boma. Troppo grasso = barca sbandata e lenta; troppo piatto = niente potenza"),
    ("vang", "Vang", "medium",
     "Vang in tensione moderata",
     "Controlla lo svergolamento della balumina",
     "Lasca la scotta 15 cm: la balumina deve aprirsi progressivamente dal basso verso l'alto. Il filetto in alto deve volare 50-80% del tempo"),
    ("traveller", "Carrello Randa", "medium",
     "Carrello leggermente sotto centro",
     "Inizia a scaricare senza perdere puntata",
     "Controlla il timone: se hai troppa barra, scendi col carrello. Il filetto in alto della randa deve volare 50-80% del tempo. Boma vicino alla mezzeria"),
]

_UPWIND_HEAVY: List[Tuple[str, str, str, str, str, str]] = [
    ("forestay", "Strallo", "heavy",
     "Strallo al massimo della tensione",
     "Appiattisce il fiocco per depotenza in vento forte",
     "Lo strallo deve essere dritto come una barra. Il fiocco deve essere piatto con entrata fine. Se c'e ancora pancia, serve piu tensione"),
    ("jib_halyard", "Drizza Fiocco", "heavy",
     "Drizza a segno, massima tensione",
     "Fiocco piatto, riduce la resistenza",
     "Luff perfettamente liscio, nessuna piega. Il profilo deve essere piatto con il grasso molto avanti. Se il fiocco e ancora grasso, cazza di piu"),
    ("jib_lead", "Carrello Fiocco", "light",
     "Carrello avanti per chiudere la balumina",
     "Meno svergolamento = piu controllo in raffica",
     "TEST CLASSICO: Orza lentamente — in vento forte il fiocco puo sfilare leggermente prima in alto (OK per depotenza). Se sfila tutto in basso, carrello troppo avanti"),
    ("cunningham", "Cunningham", "heavy",
     "Cunningham a segno — apri la balumina della randa",
     "Scarica la randa in alto, riduce il momento sbandante",
     "La balumina della randa deve essere aperta in alto — guarda la stecca superiore, deve puntare leggermente sottovento. Il grasso deve essere al 35-40% dal luff"),
    ("outhaul", "Borosa", "heavy",
     "Borosa a segno — randa piatta",
     "Massima depotenza sulla base della randa",
     "La base della randa deve essere quasi piatta contro il boma, nessun pancia visibile. Se la barca sbanda ancora troppo, verifica che sia veramente a segno"),
    ("vang", "Vang", "heavy",
     "Vang a segno",
     "Blocca la stecca superiore, controlla la balumina",
     "Lasca la scotta: la stecca superiore deve restare controllata. Se si apre troppo, serve piu vang. Il filetto in alto deve volare 40-60% del tempo"),
    ("traveller", "Carrello Randa", "light",
     "Carrello tutto sottovento",
     "Depotenza: apri la randa per ridurre la sbandamento",
     "La barca deve essere piatta o quasi. Se hai ancora troppa barra sottovento, il carrello non e abbastanza giu. Il boma deve essere ben a sottovento della mezzeria"),
]

# Reach — less specific, main focus on vang and traveller
_REACH: List[Tuple[str, str, str, str, str, str]] = [
    ("forestay", "Strallo", "medium",
     "Strallo in tensione media",
     "Bilancia il grasso del fiocco per il lasco",
     "Il fiocco deve avere forma moderata. Controlla che non sia troppo grasso (scarroccia) ne troppo piatto (stalla)"),
    ("jib_halyard", "Drizza Fiocco", "medium",
     "Drizza in tensione",
     "Mantieni il profilo del fiocco",
     "Luff liscio senza pieghe. Il fiocco deve lavorare con flusso attaccato — i filetti devono volare su entrambi i lati"),
    ("jib_lead", "Carrello Fiocco", "heavy",
     "Carrello a poppa",
     "Apri lo svergolamento per il traverso",
     "Al traverso lo svergolamento deve essere aperto. Controlla che la parte alta del fiocco non stalli — il filetto sopravvento in alto deve volare"),
    ("cunningham", "Cunningham", "light",
     "Cunningham lasco",
     "Lascia il grasso nella randa per portanza laterale",
     "La randa deve avere forma piena. Pieghe lungo il luff sono accettabili al traverso — indicano grasso che serve per potenza"),
    ("outhaul", "Borosa", "medium",
     "Borosa a meta",
     "Forma moderata sulla base",
     "Pancia moderata sulla base. Regola guardando la PERF%: prova a lascare/cazzare leggermente e osserva se la velocita migliora"),
    ("vang", "Vang", "heavy",
     "Vang in tensione — controlla lo svergolamento",
     "Al traverso il vang e il controllo principale della balumina",
     "IMPORTANTE: Al traverso il vang sostituisce la scotta per il controllo della balumina. La stecca superiore deve essere parallela al boma. Se punta sopravvento, troppo vang"),
    ("traveller", "Carrello Randa", "light",
     "Carrello sottovento, scotta a segno",
     "Lascia la randa lavorare con la scotta, non col carrello",
     "Il boma deve lavorare libero a sottovento. Regola con la scotta, non col carrello. La barra dovrebbe essere leggera e neutra"),
]

# Downwind white sails
_DOWNWIND_WHITE: List[Tuple[str, str, str, str, str, str]] = [
    ("forestay", "Strallo", "light",
     "Strallo lasco",
     "Massimo grasso nel fiocco per la poppa",
     "Lo strallo deve avere insaccamento visibile. Il fiocco deve essere pieno e grasso per catturare il vento in poppa"),
    ("jib_halyard", "Drizza Fiocco", "light",
     "Drizza appena in tensione",
     "Forma piena per il lasco stretto",
     "Piccole pieghe sul luff sono OK in poppa. Il fiocco deve essere pieno e aperto. Se e piatto, lasca la drizza"),
    ("jib_lead", "Carrello Fiocco", "heavy",
     "Carrello tutto a poppa",
     "Massimo svergolamento per andature portanti",
     "Il fiocco deve essere completamente svergolato in alto. La balumina deve essere aperta. Se il fiocco richiude in alto, carrello ancora piu a poppa"),
    ("cunningham", "Cunningham", "light",
     "Cunningham lasco",
     "Forma piena nella randa",
     "La randa deve essere grassa con pancia piena. Pieghe lungo il luff sono normali e desiderabili in poppa"),
    ("outhaul", "Borosa", "light",
     "Borosa lascissima — massimo grasso",
     "Tutta la potenza possibile in poppa",
     "Massima pancia sulla base — piu di un palmo dal boma. Tutta la superficie proiettata possibile per catturare il vento"),
    ("vang", "Vang", "heavy",
     "Vang a segno — e il tuo timone di randa",
     "Controlla lo svergolamento quando la scotta e lasca",
     "CRITICO: Con la scotta lasca, il vang e l'unico controllo della balumina. La stecca superiore deve essere parallela al boma. Se si apre, cazza il vang"),
    ("traveller", "Carrello Randa", "light",
     "Carrello tutto sottovento, scotta lasca",
     "Apri la randa al massimo",
     "Il boma deve essere completamente fuori. Regola l'angolo della randa solo col vang e la scotta. La barca deve essere stabile senza rolling"),
]

# Downwind with gennaker — fewer controls (no jib)
_DOWNWIND_GENNAKER: List[Tuple[str, str, str, str, str, str]] = [
    ("cunningham", "Cunningham", "light",
     "Cunningham lasco",
     "Forma piena nella randa",
     "Randa grassa. Col gennaker la randa e secondaria — deve solo non frenare. Pieghe sul luff vanno bene"),
    ("outhaul", "Borosa", "light",
     "Borosa lascissima",
     "Tutta la potenza in poppa",
     "Massima pancia sulla base. La randa deve catturare tutto il vento possibile dietro il gennaker"),
    ("vang", "Vang", "heavy",
     "Vang a segno",
     "Controlla la balumina della randa con il gennaker alzato",
     "La stecca superiore deve essere parallela al boma. Se la randa pompa o oscilla, serve piu vang. Se la barca tende a strapoggiare, lasca leggermente"),
    ("traveller", "Carrello Randa", "light",
     "Carrello tutto sottovento",
     "Apri la randa, il gennaker fa il lavoro",
     "Boma completamente fuori. La randa non deve interferire col flusso del gennaker. Se il gennaker collassa, potrebbe servire orzare leggermente, non toccare il carrello"),
]


def _get_table(
    wind_range: str, pos: str, sail_type: str
) -> List[Tuple[str, str, str, str, str, str]]:
    """Pick the right trim table."""
    if pos == "upwind":
        if wind_range == "light":
            return _UPWIND_LIGHT
        elif wind_range == "medium":
            return _UPWIND_MEDIUM
        else:
            return _UPWIND_HEAVY
    elif pos == "reach":
        # Adjust per wind — use medium-heavy table for heavy wind reach
        return _REACH
    else:  # downwind
        if "gennaker" in sail_type:
            return _DOWNWIND_GENNAKER
        return _DOWNWIND_WHITE


def _adjust_for_sea(steps: List[TrimStep], sea_state: str) -> List[TrimStep]:
    """Tweak recommendations for sea state."""
    if sea_state == "rough":
        for s in steps:
            # In rough water: more power, less pointing
            if s.control == "jib_lead" and s.setting == "light":
                s.setting = "medium"
                s.instruction += " (piu a poppa per onda)"
            if s.control == "outhaul" and s.setting == "heavy":
                s.setting = "medium"
                s.instruction += " (lasca leggermente per onda)"
            if s.control == "traveller" and s.setting == "heavy":
                s.setting = "medium"
                s.instruction += " (scendi per onda)"
    elif sea_state == "flat":
        for s in steps:
            # Flat water: max pointing
            if s.control == "traveller" and s.setting == "medium":
                s.setting = "heavy"
                s.instruction += " (alza per acqua piatta)"
    return steps


def get_trim_guide(
    tws: float,
    twa: float,
    sail_type: str = "racing_white",
    sea_state: str = "",
) -> dict:
    """Return the guided trim procedure for current conditions.

    Returns a dict with:
      - wind_range: "light" | "medium" | "heavy"
      - point_of_sail: "upwind" | "reach" | "downwind"
      - steps: list of TrimStep dicts
    """
    wr = _wind_range(tws)
    pos = _point_of_sail(twa)
    table = _get_table(wr, pos, sail_type)

    steps = []
    for i, (ctrl, label, setting, instruction, why, test) in enumerate(table):
        steps.append(TrimStep(
            order=i + 1,
            control=ctrl,
            label=label,
            setting=setting,
            instruction=instruction,
            why=why,
            test=test,
        ))

    if sea_state:
        steps = _adjust_for_sea(steps, sea_state)

    # Find wind range label
    wr_label = next((lbl for key, _, lbl in WIND_RANGES if key == wr), wr)
    pos_labels = {"upwind": "Bolina", "reach": "Traverso", "downwind": "Poppa"}

    return {
        "wind_range": wr,
        "wind_range_label": wr_label,
        "tws_kt": round(tws, 1),
        "point_of_sail": pos,
        "point_of_sail_label": pos_labels.get(pos, pos),
        "sail_type": sail_type,
        "sea_state": sea_state,
        "total_steps": len(steps),
        "steps": [
            {
                "order": s.order,
                "control": s.control,
                "label": s.label,
                "setting": s.setting,
                "instruction": s.instruction,
                "why": s.why,
                "test": s.test,
            }
            for s in steps
        ],
    }
