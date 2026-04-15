# Brainstorm — Contrôle de conformité vidéo de démo Niamoto

**Date** : 2026-04-13
**Sujet** : Fidélité entre captures `docs/plans/caps/` et composition Remotion `media/demo-video/`
**Référentiels existants** : [video-fidelity-mapping.md](../plans/caps/video-fidelity-mapping.md), [2026-04-13-demo-video-motion-graphics-brainstorm.md](2026-04-13-demo-video-motion-graphics-brainstorm.md)

## 1. Question-source

> « Contrôle de conformité entre l'appli réelle telle qu'on la voit dans les screenshots et la vidéo, pour corriger les écrans si nécessaire. Est-ce une bonne idée de coller juste aux écrans de l'appli ? »

## 2. Réponse à la question méta

**Coller pixel-perfect aux écrans réels n'est pas une bonne idée.** Raisons :

- À 1920×1080, avec 8–15 s par acte, un écran dense (ex : catalog widgets, site builder 3 colonnes) devient illisible — le spectateur ne lit ni ne reconnaît.
- Coût de maintenance énorme : chaque évolution UI casse la vidéo.
- Risque d'uncanny valley dès que typo ou spacing dérivent de 1 px.
- Du bruit inutile (URLs de dév, noms de fichiers internes, IDs) parasite le message.

**À l'inverse**, il faut absolument coller à : palette `frond`, structure globale (sidebar + topbar + traffic lights macOS), logo et typographie officiels, libellés des CTA majeurs (ex. « Créer un nouveau projet »).

**Règle d'or** : le spectateur doit reconnaître l'app 10 s après la vidéo, pas reconnaître chaque modale exacte.

## 3. Ce qu'on construit

Une vidéo **hybride semi-fidèle** :

| Niveau | Règle | Exemple |
| --- | --- | --- |
| Shell app | Pixel-proche des captures | `AppWindow`, `Sidebar`, `TopBar`, traffic lights, window radius |
| Écran principal | Structure + palette exactes, densité réduite à 20-40 % | Act 4 : 3 widgets visibles au lieu de 12 dans le catalog |
| Micro-interactions | Invention guidée par les captures | Typing animation, cursor flow, spring on click |
| Site publié | **100 % capture PNG réelle** dans un cadre | partie « aperçu site » de cap 25 + capture complémentaire à générer, insérées dans un `SitePreviewFrame` (Act 6 uniquement) |

## 4. Décisions prises

- **Philosophie** : hybride semi-fidèle (shell exact, scènes focus simplifiées).
- **Usage cible** : landing Niamoto-Arsis, 60–90 s, muet par défaut, texte à l'écran court.
- **Assets** : captures réelles uniquement pour les pages publiées / site live — pas pour les écrans de l'app.
- **Format** : 1920×1080, 30 fps, 90 s (conserver la durée actuelle).
- **Pas de voix off** cette itération.
- **Stratégie de mise en œuvre** : shell d'abord, puis primitives, puis actes (les plus faux en premier).

## 5. Audit synthétique acte par acte

| Acte | État post-refactor (commit `02c0bee9`) | Écart cible | Priorité |
| --- | --- | --- | --- |
| Intro | Logo animé sur gradient clair | Vérifier anti-aliasing du logo | basse |
| Act 1 Welcome | 2 cards Créer/Ouvrir + toggle autoload | Proche du vrai, vérifier wording + toggle | basse |
| Act 2 Project Wizard | Formulaire React générique | Coller cap 03→04→05 : champs Nom + Emplacement + bouton Créer | **haute** |
| Act 3 Import | Structure correcte, dense | Alléger listes fichiers (6 max), aligner sur cap 08 | moyenne |
| Act 4 Collections | Très éloigné du réel | Refondre : vue plots/taxons/shapes (cap 15) + modal Ajouter widget simplifiée (cap 17) | **haute** |
| Act 5 Site Builder | 3 colonnes présentes | Reconstituer l'interface de builder (cap 21/22/23 comme **référence visuelle**, pas comme asset injecté) | moyenne |
| Act 6 Publish | Écran de déploiement générique | Refondre : panneau preview avec **aperçu site live extrait de cap 25** + modal providers (cap 26) + succès (cap 29) | **haute** |
| Outro | CTA | Conserver | basse |

## 6. Ordre de mise en œuvre

### Phase 1 — Shell consolidé (fondations)

1. `AppWindow` : radius 20 px, shadow macOS, traffic lights alignés.
2. `Sidebar` : hiérarchie avec sous-items (ex. Collections → plots, taxons, shapes).
3. `TopBar` : project selector « nouvelle-calé… », search compact, notif bell.
4. `NiamotoLogo` : vérifier anti-aliasing (problème de pixelisation signalé sur splash).

### Phase 2 — Primitives UI manquantes

5. `AppModal` : overlay dim + modal centrée (titre, close X).
6. `WidgetCard` : icône + titre + source pill + thumbnail.
7. `SitePreviewFrame` : frame « iframe-like » qui affiche un PNG du **site publié** (utilisé uniquement dans Act 6 pour l'aperçu de génération + l'état succès, pas dans Act 5).
8. `ProviderPickerTile` : tuile logo + label en grille 2×3.

### Phase 3 — Actes prioritaires (les plus faux)

9. **Act 2 Project Wizard** : refaire suivant cap 03/04/05 (form centré, saisie animée du nom, bouton Créer vert).
10. **Act 4 Collections** : vue catalog 3 colonnes (cap 15) → modal Ajouter widget simplifiée (cap 17, 3 cartes visibles) → boutons Blocs / Liste / Export.
11. **Act 6 Publish** : cadre preview avec cap 25 en asset + modal providers avec 6 tuiles (cap 26) + build log allégé + état succès (cap 29).

### Phase 4 — Polish des actes structurellement OK

12. **Act 3 Import** : réduire listes à 6 fichiers, garder structure sources → analyse → config.
13. **Act 5 Site Builder** : reconstituer le layout 3 colonnes (sidebar projet + arbre pages + formulaire d'édition), en prenant cap 21/22/23 comme référence visuelle.

## 7. Règles de simplification

- **Densité** : 3 éléments visibles max, reste tronqué (`+15 autres` ou hors-viewport).
- **Textes** : une ligne par libellé, pas de paragraphes.
- **Chiffres** : 1 KPI fort par scène (ex. « 205 654 occurrences importées »).
- **URLs** : fictives réalistes (`monprojet.github.io/niamoto`), jamais de vrai domaine de prod.
- **Logs** : 4 lignes verbalisées (« Génération du site… », « Upload GitHub Pages… », « Déploiement OK »), pas de stdout brut.
- **Données sensibles** : aucun email, ID système ou path local visible.

## 8. Assets à importer

**Règle** : seules les captures qui montrent le **site publié** sont embarquées dans la vidéo comme PNG. Les captures d'écrans app restent uniquement des références visuelles pour le code React.

**À générer par Julien** (déploiement Niamoto réel ou local, captures navigateur 1600×900 min) :

- `site-home.png` — accueil du site publié (header vert + hero forêt)
- `site-taxon.png` — page taxon avec widgets (carte, charts)
- `site-collection.png` — liste collection (grille de cards)

Destination : `media/demo-video/public/site-previews/`.

Usage :
- Act 6 aperçu (cap 25 référence) → injection `site-home.png` dans `SitePreviewFrame`.
- Act 6 succès → injection `site-home.png` en « live ».
- Outro → rotation `site-home` → `site-taxon` → `site-collection`.

Captures d'interface app (référence visuelle uniquement, **pas embarquées**) : 01, 02, 03, 04, 05, 06, 08, 10, 11, 13, 15, 16, 17, 19, 21, 22, 25, 26, 27, 28, 29.

## 9. Questions ouvertes

- `TransitionLabel` entre actes : conserver tel quel ou basculer vers sous-titre discret continu ? → à trancher après premier rendu.
- SFX légers (click, whoosh, notification) ? → a priori non, mais à reconsidérer si la vidéo paraît « trop silencieuse ».
- Variantes d'export (60 s réseaux, 9:16 vertical) : hors périmètre de cette itération.

## 10. Next

Lancer `/compound-engineering:workflows:plan` sur ce document pour générer le plan d'implémentation (storyboards, primitives, timings) couvrant les quatre phases.

**Pré-requis avant planning** : récupérer les 3 captures `site-home.png`, `site-taxon.png`, `site-collection.png` (§8) — sinon Act 6 et l'outro ne pourront pas être finalisés.
