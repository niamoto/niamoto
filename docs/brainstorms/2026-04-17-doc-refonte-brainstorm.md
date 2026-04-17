---
date: 2026-04-17
topic: documentation-refonte-desktop-first
---

# Refonte documentation Niamoto — Desktop-first

## What We're Building

Refonte complète de la surface documentaire publique Niamoto, alignée sur le
pivot desktop-first (app Tauri v0.15+ devenue l'UX principale). Le sprint 1
couvre la totalité de la surface publique :

- `README.md` (GitHub, PyPI) — restructuré en format « studio » court et visuel.
- Arborescence `docs/` réorganisée par cycle de vie utilisateur.
- Métadonnées GitHub du repo : description, topics, website URL, social preview.
- Assets visuels : screenshots app desktop + GIF workflow + image social preview.

Le produit raconte désormais : « studio desktop qui transforme des données
écologiques en portails biodiversité », avec CLI reléguée au rang d'outil
avancé pour automation et CI. Trois parcours de lecture par persona
(chercheur / institution / développeur). Pattern structurel repris de
`docs/03-ml-detection/` (« Start here / If you want to / Structure »).

## Why This Approach

**Constat.** Le README parle uniquement de CLI (`pip install niamoto`) et
n'évoque nulle part l'app desktop. `docs/README.md` est estampillé
« v2.0.0 — décembre 2024 ». Les sections `02-data-pipeline`, `04-plugin-development`,
`05-api-reference` n'ont pas été touchées depuis 4 à 6 mois et restent CLI-only.
Seules `06-gui`, `10-roadmaps/gui-finalization` et une partie de `01-getting-started`
mentionnent déjà le desktop. `03-ml-detection` est propre et peut servir de
gabarit.

**Approches comparées pour le README.**

- **Studio (choisi)** : ~200 lignes, hero + screenshot app desktop, table des 3
  parcours persona, install binaire + CLI, GIF workflow, liens docs. Suffit pour
  évaluer depuis GitHub en 30 secondes sans surcharger.
- *Landing marketing long (~600 lignes)* — rejeté : surdimensionné pour un
  README GitHub, redondant avec la doc.
- *Docs-first minimaliste (Zed/Astro-style, ~60 lignes)* — rejeté : pas assez
  de signal pour se faire une opinion depuis la page d'accueil.

**Approches comparées pour `docs/`.**

- **Par cycle de vie (choisi)** : structure neutre par étape (démarrer →
  utiliser → étendre → comprendre). Les 3 personas trouvent leur chemin via le
  README. Scale bien.
- *Par persona (for-researchers / for-devs / for-institutions)* — rejeté :
  redondance install/config, plus dur à maintenir.
- *In-place (garder 01-12)* — rejeté : on hériterait d'une taxonomie CLI-first
  et on n'aurait pas le signal fort de remise à plat.

**Approches comparées pour la migration.**

- **Reboot big-bang + `_archive/` (choisi)** : nouvelle arbo créée d'un coup,
  ancien déplacé par `git mv` dans `docs/_archive/` (pénalité nulle, git garde
  l'historique). Pas de limbo, lecteur ne voit jamais de mélange.
- *V2 en parallèle puis bascule* — rejeté : double maintenance, risque
  d'inachevé.
- *Progressif in-place* — rejeté : contenu hétérogène visible longtemps.
- *Archive brutale + minimal viable* — rejeté : vide trop long.

## Key Decisions

### Positionnement et audience

- **Desktop-first explicite** : l'app Tauri est le produit, la CLI est un outil
  avancé (CI, automation, power-users).
- **Audience README mixte** avec 3 parcours distincts (chercheur / institution
  / développeur). Hero universel, redirection par persona.
- **Pages persona = index composites** : ce sont des pages d'entrée qui agrègent
  des liens vers les sections cycle-de-vie (pas de guides autonomes dédiés,
  donc pas de duplication de contenu).

### Structure du README

- Hero + tagline + **screenshot split-view (app desktop à gauche + portail
  généré à droite)** : raconte départ → arrivée en une image.
- Table des 3 parcours persona.
- Installation (desktop releases + `pip install niamoto`).
- Aperçu GIF ~60s du workflow import → preview → export.
- Ressources (docs, issues, discussions, changelog).
- Démo link `niamoto.github.io/niamoto-static-site` : **à vérifier avant le
  sprint**, garder si représentatif, sinon retirer.
- ~200 lignes max.

### Topologie `docs/`

```
docs/
├─ 01-getting-started/        install desktop · premier projet · concepts
├─ 02-user-guide/             desktop : import · preview · transform · export
├─ 03-cli-automation/         CLI, automation, pipelines CI/CD (nom explicite)
├─ 04-plugin-development/     transformers, widgets, loaders, exporters
├─ 05-ml-detection/           conservé intact (déjà propre)
├─ 06-reference/
│  └─ api/                    autogen Sphinx (27 .rst déplacés + conf.py ajusté)
├─ 07-architecture/           ADR, system overview, decisions
├─ 08-roadmaps/               plans datés, target-architecture
├─ 99-troubleshooting/
├─ _archive/                  ancien contenu CLI-only, déplacé par git mv
├─ plans/                     archive vivante datée (inchangé, exclude_pattern Sphinx)
├─ brainstorms/               archive vivante datée (inchangé, exclude_pattern Sphinx)
└─ ideation/                  (inchangé, exclude_pattern Sphinx)
```

- Noms explicites `03-cli-automation` et `04-plugin-development` pour que le
  lecteur sache sans chercher dans le README.
- `06-reference/api/` reçoit l'autogen Sphinx — `conf.py` et la config
  `sphinx-apidoc` sont modifiés pour générer dans ce chemin au lieu de la
  racine de `docs/`.
- `plans/`, `brainstorms/`, `ideation/` restent en place (archive vivante
  utile à l'équipe) mais sont ajoutés à `exclude_patterns` dans `conf.py` pour
  ne pas polluer le toctree public.

### Migration

- **Reboot big-bang au sprint 1.** Nouvelle arbo créée d'un coup, ancien
  contenu CLI-only des dossiers `02-data-pipeline`, `05-api-reference`,
  `06-gui`, `08-configuration`, `11-development`, `12-troubleshooting` déplacé
  par `git mv` vers `docs/_archive/` (git garde l'historique).
- Chaque nouveau dossier contient au minimum un `README.md` d'index (pattern
  03-ml-detection) avec mention honnête « contenu en cours de migration »
  pour les parties vides.
- **Pattern structurel** appliqué à chaque section `docs/0X-*/README.md` :
  « Start here » (3 liens essentiels), « If you want to… » (par cas d'usage),
  « Structure » (active / research / archive si pertinent).

### Sprint 1 complet

- README + arbo `docs/` reboot + métadonnées GitHub + assets. Toute la surface
  publique cohérente d'un coup.
- **`docs/index.rst`** réécrit (toctree nouvelle arbo, exclude_patterns).
- **`docs/README.md`** réécrit (tampon « décembre 2024 » remplacé).
- **`docs/conf.py`** mis à jour : thème Shibuya, sphinx-apidoc sur
  `06-reference/api/`, `exclude_patterns` pour `plans/brainstorms/ideation`.
- **Métadonnées GitHub** (repo settings) : description, topics, website URL,
  social preview image.

### Anti-slop

- **Review manuelle poussée partout.** Chaque fichier relu ligne à ligne
  après application des skills `/anti-slop` et `/stop-slop`. Qualité maximale
  assumée même si le tempo est plus lent.
- **`docs/STYLE_GUIDE.md`** créé au sprint 1 : voix Niamoto (phrases courtes,
  verbes d'action), vocabulaire banni (« seamlessly », « leveraging »,
  « delve into », « comprehensive », « elegantly », « robust », « powerful »),
  conservation des accents français dans les comms FR (README reste en
  anglais mais le style guide rappelle la règle pour devlog et comms internes).

### Branding visuel

- **Logo actuel conservé** (`assets/niamoto_logo.png`). Pas de refonte
  branding dans ce sprint.
- **Social preview image 1280×640** produite dans le sprint (logo + tagline
  + screenshot split-view).
- **Thème Sphinx upgradé vers Shibuya** (plus produit, moins docs-classique).

### Langue

- Docs en anglais (convention actuelle conservée).
- Accents français exigés dans comms internes et devlog (rappel dans le
  style guide).

### Assets à capturer

- 1 screenshot hero **split-view** : app desktop à gauche (écran import
  avec auto-detection ML ou preview d'un widget), portail généré à droite.
- 1 GIF ~30-60s du workflow import → preview → export, format optimisé pour
  README (≤ 5 MB, boucle propre).
- 1 social preview image 1280×640 pour GitHub.
- 2-3 screenshots supplémentaires pour `01-getting-started` et
  `02-user-guide`.

## Open Questions

Toutes les questions structurelles sont résolues. Les précisions restantes
sont du HOW et appartiennent au plan :

- Contenu exact du `STYLE_GUIDE.md` anti-slop (liste complète des mots bannis,
  exemples avant/après).
- Tagline exacte du hero (plusieurs formulations à tester).
- État précis de l'app à capturer pour le split-view (import CSV ? preview
  widget ? carte interactive ?).
- Durée exacte et scénario du GIF workflow.
- Vérification du demo link `niamoto-static-site` : à faire avant le sprint.
- Texte exact des métadonnées GitHub (description ≤ 350 caractères, topics
  choisis parmi la taxonomie GitHub).

## Next Steps

→ Lancer `/workflows:plan` pour produire le plan d'exécution détaillé du
sprint 1.

Attendu dans le plan :

- Séquencement : assets → README → squelette `docs/` → métadonnées GitHub → passe anti-slop finale
- Liste exacte des fichiers à créer, déplacer (`git mv`), supprimer
- Détail des screenshots/GIF à capturer (états précis de l'app desktop, durée, format)
- Gabarit exact des `README.md` d'index par section
- Contenu du `STYLE_GUIDE.md` anti-slop
- Mise à jour `docs/index.rst`, `docs/conf.py`, `docs/README.md`
- Texte exact des métadonnées GitHub (description, topics, website)
- Checklist de vérification avant merge (anti-slop, liens, accents, cohérence)
