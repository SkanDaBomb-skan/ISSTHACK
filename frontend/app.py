"""
frontend/app.py - Établi virtuel & simulateur du projecteur zénithal (Membre 2).

Lancer depuis la racine du dépôt :
    streamlit run frontend/app.py
"""

from __future__ import annotations

import os
import sys
import time

import streamlit as st
import streamlit.components.v1 as components

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from frontend.component import render_html  # noqa: E402
from frontend.adapter import SOURCES  # noqa: E402
from frontend.session import ProjectorSession  # noqa: E402

st.set_page_config(page_title="ProjFlow-AI · Projecteur zénithal", page_icon="💡", layout="wide")

# Retro editorial skin of the ProjFlow dashboard, applied to the Streamlit chrome.
st.markdown("""
<style>
@import url("https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;600;700;800&display=swap");
.stApp { background-color: #188f83;
  background-image: linear-gradient(#173b3b55 1px, transparent 1px), linear-gradient(90deg, #173b3b55 1px, transparent 1px);
  background-size: 38px 38px; font-family: "Inter", sans-serif; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 2.6rem 1.2rem 1rem; max-width: none; }
[data-testid="stSidebar"] { background: #f4f0df; border-right: 2px solid #28252c; }
[data-testid="stSidebar"] * { color: #28252c; }
[data-testid="stSidebar"] h3 { font-family: "DM Serif Display", serif; font-weight: 400; font-size: 1.5rem; }
[data-testid="stSidebar"] .stButton button { border: 2px solid #28252c; border-radius: 999px; background: #f0df54;
  color: #28252c; font-weight: 700; box-shadow: 3px 3px 0 #28252c; }
[data-testid="stSidebar"] .stButton button:hover { filter: brightness(1.05); transform: translateY(-1px); }
[data-testid="stSidebar"] .stButton button[kind="primary"] { background: #2765d5; box-shadow: 0 5px 0 #ed59b8, 0 8px 0 #28252c; }
[data-testid="stSidebar"] .stButton button[kind="primary"] * { color: #fff8ea; }
[data-testid="stSidebar"] code { background: #fbf8ec; border: 1.5px solid #28252c; color: #28252c; }
[data-testid="stSidebar"] [data-testid="stCode"] pre { background: #fbf8ec; border: 2px solid #28252c; border-radius: 10px; }
iframe { border: 0; }
</style>
""", unsafe_allow_html=True)


SOURCE_LABELS = {"m1": "Moteur IA Membre 1 (live)", "m3": "Lots scénarisés Membre 3 (rejeu)"}
MODE_LABELS = {False: "Protocole fixe standard (fatigue élevée)", True: "ProjFlow-AI · nudge subconscient (protégé)"}


@st.cache_resource(show_spinner="Chargement du moteur du Membre 1…")
def load_source(key: str):
    """Moteur chargé une seule fois par serveur : les rechargements de page et changements de source sont instantanés."""
    src = SOURCES[key]()
    src.shift_comparison()  # pré-calcul de la comparaison avant/après du shift
    return src


def safe(action, label: str) -> None:
    """Exécute une action de l'IHM sans jamais casser la démo : en cas d'erreur, message clair et état conservé."""
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - on veut tout attraper pendant une démo en direct
        st.toast(f"⚠️ {label} impossible : {exc}", icon="⚠️")


ss = st.session_state
ss.setdefault("source", "m1")
ss.setdefault("playing", True)
ss.setdefault("speed", 5)
ss.setdefault("last_tick", time.monotonic())

with st.sidebar:
    st.markdown("### Projecteur zénithal")
    ai = st.radio("Mode (avant / après)", [False, True], index=1, format_func=MODE_LABELS.get,
                  help="Bascule immédiate sur les étapes restantes du lot en cours.")
    source = st.radio("Source des données", list(SOURCE_LABELS), format_func=SOURCE_LABELS.get,
                      index=list(SOURCE_LABELS).index(ss.source))
    threshold = st.slider("Seuil de déclenchement auto (%)", 50, 120, 75 if source == "m1" else 70, 5,
                          help="L'IA intervient si une articulation doit dépasser ce niveau dans les 30 s. "
                               "M1 : % du pic atteint par le protocole fixe. M3 : % de fatigue du lot.")
    ss.speed = st.select_slider("Vitesse de simulation", [1, 2, 5, 10, 20], value=ss.speed, format_func=lambda v: f"{v}×")

    try:
        if "sess" not in ss or ss.source != source:
            ss.source = source
            ss.sess = ProjectorSession(source, ai=ai, threshold_pct=threshold, src=load_source(source))
            ss.last_tick = time.monotonic()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Le moteur « {SOURCE_LABELS[source]} » n'a pas pu démarrer : {exc}")
        st.stop()
    sess: ProjectorSession = ss.sess
    sess.threshold_pct = float(threshold)
    if ai != sess.ai:
        safe(lambda: sess.set_ai(ai), "Changement de mode")

    if st.button("⏭ Simuler le lot suivant", type="primary", width="stretch",
                 help="Termine le lot en cours dans le jumeau de fatigue du Membre 1 et lance un nouvel ordre de fabrication."):
        safe(sess.next_batch, "Lot suivant")
    c1, c2 = st.columns(2)
    if c1.button("⏸ Pause" if ss.playing else "▶ Lecture", width="stretch"):
        ss.playing = not ss.playing
        ss.last_tick = time.monotonic()
    if c2.button("↺ Relancer", width="stretch"):
        safe(sess.reset, "Relance")


@st.fragment(run_every=0.5)
def live() -> None:
    """Fait avancer la simulation côté serveur (déclenchement auto) et ne renvoie un nouvel instantané
    au navigateur que si l'état visible a changé. Le reste du temps, le HTML est identique :
    l'iframe n'est pas rechargée et l'animation navigateur reste fluide."""
    sess: ProjectorSession = ss.sess
    now = time.monotonic()
    dt = min(now - ss.last_tick, 2.0)
    ss.last_tick = now
    try:
        if ss.playing:
            sess.tick(dt * ss.speed)
        key = (sess.source_key, sess.batch_no, tuple(sess.order), tuple(round(sess.angles[i], 1) for i in sess.order),
               len(sess.events), ss.playing, ss.speed, sess.ai, sess.threshold_pct, sess.mutated)
        if ss.get("snap_key") != key:
            ss.snap_html = render_html(sess.snapshot(ss.playing, ss.speed))
            ss.snap_key = key
    except Exception as exc:  # noqa: BLE001 - keep showing the last good frame
        st.warning(f"Simulation interrompue : {exc}. Dernier état affiché ; cliquez sur « Relancer ».")
        if "snap_html" not in ss:
            return
    components.html(ss.snap_html, height=1450, scrolling=False)


live()
