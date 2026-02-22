"""Modèles du moteur de preview.

Contrat partagé entre le router et le moteur de rendu.
SYNC: les types TypeScript correspondants sont dans
src/niamoto/gui/ui/src/lib/preview/types.ts
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

PreviewMode = Literal["thumbnail", "full"]


@dataclass(frozen=True)
class PreviewRequest:
    """Requête de preview entrante (construite par le router).

    Deux modes d'utilisation :
    - Par template_id : résolution via transform.yml/export.yml
    - Par inline : configuration directe transformer+widget
    """

    template_id: Optional[str] = None
    group_by: Optional[str] = None
    source: Optional[str] = None
    entity_id: Optional[str] = None
    mode: PreviewMode = "full"
    inline: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class PreviewResult:
    """Résultat du rendu de preview.

    Le HTML est un document complet (<!DOCTYPE html>...) prêt
    pour injection dans un iframe via srcDoc.
    """

    html: str
    etag: str
    preview_key: str
    warnings: tuple[str, ...] = ()
