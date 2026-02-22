"""Moteur de preview unifié pour les widgets Niamoto.

Ce module centralise la logique de rendu des previews widgets
(résolution, chargement de données, transformation, rendu HTML)
en un seul pipeline utilisé par tous les endpoints.
"""

from niamoto.gui.api.services.preview_engine.models import (
    PreviewMode,
    PreviewRequest,
    PreviewResult,
)
from niamoto.gui.api.services.preview_engine.engine import PreviewEngine

__all__ = ["PreviewEngine", "PreviewMode", "PreviewRequest", "PreviewResult"]
