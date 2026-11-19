"""
frontend/component.py - Composant navigateur du projecteur (SVG + JS, style rétro ProjFlow).

Le navigateur anime seul le cycle (60 i/s) à partir d'un instantané ; Python ne renvoie un
nouvel instantané qu'aux événements (mutation, nouveau lot, pause, vitesse, seuil). Tant que
l'instantané ne change pas, le HTML envoyé est identique et l'iframe n'est pas rechargée.
"""

from __future__ import annotations

import json
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "projector.html")
PLACEHOLDER = "/*__DATA__*/null"


def render_html(snapshot: dict) -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    data = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, data)
