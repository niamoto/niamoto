# Next Session Handoff

## État actuel

- worktree avec modifications locales (runner patché, pas encore commité)
- seul fichier hors git :
  - `ml-detection-dashboard.html`
- aucun runner `autoresearch` actif
- aucun `codex exec` actif

## Ce qui a été fait dans cette session

### Runner patché (2026-03-19)

Fichier modifié : `scripts/ml/run_fusion_surrogate_autoresearch.py`

Changements appliqués :

1. **`--defer-stack-validation` (défaut : `true`)**
   - quand un candidat passe `surrogate-mid`, il est logué dans
     `.autoresearch/fusion-surrogate-promotions.jsonl` avec son diff complet
   - statut : `queue_stack_validation`
   - la boucle **continue** sans lancer `product-score-fast-fast`
   - les baselines fast/mid sont mises à jour

2. **Filtrage des fichiers autorisés (`reject_scope`)**
   - si Codex touche un fichier hors `DEFAULT_ALLOWED_PATHS`, l'itération est
     rejetée immédiatement et les fichiers restaurés
   - corrige le problème de l'iter 11 qui avait touché le log d'expérimentations

3. **Suppression de `--baseline-stack`**
   - plus nécessaire puisque la stack est déférée par défaut
   - `--no-defer-stack-validation` permet de revenir au comportement original

## Baselines actuelles

Cache surrogate :

- `data/cache/ml/fusion_surrogate/gold_set_splits3`

Baselines fusion surrogate :

- `surrogate-fast = 55.6326`
- `surrogate-mid = 59.2746`

Baselines stack déjà mesurées auparavant :

- `ProductScoreFastFast = 69.8965`
- `ProductScoreFast = 79.0115`
- `ProductScore = 79.2454`
- `NiamotoOfflineScore = 78.6199`

## Logs importants

Runs autonomes passés :

- `.autoresearch/fusion-surrogate-20260318T205732Z.jsonl`
- `.autoresearch/fusion-surrogate-20260318T214705Z.jsonl`

Queue de promotions (nouvelle) :

- `.autoresearch/fusion-surrogate-promotions.jsonl` (sera créée au premier
  candidat qui passe `surrogate-mid`)

Journal humain :

- `docs/03-ml-detection/experiments/2026-03-17-ml-detection-iteration-log.md`

## Workflow actuel

### Boucle chaude (runner autonome)

```bash
uv run python -m scripts.ml.run_fusion_surrogate_autoresearch --iterations 50
```

Comportement :

1. évalue `surrogate-fast` → rejette si ≤ baseline
2. évalue `surrogate-mid` → rejette si ≤ baseline
3. si succès : commit + queue dans `promotions.jsonl` → **continue la boucle**

### Boucle froide (validation manuelle)

Lire la queue :

```bash
cat .autoresearch/fusion-surrogate-promotions.jsonl | python -m json.tool
```

Pour chaque candidat prometteur, lancer manuellement :

```bash
OMP_NUM_THREADS=1 .venv/bin/python -m scripts.ml.evaluate --model all --metric product-score-fast-fast --splits 2 --verbose-progress
```

Puis si ça passe, monter progressivement :

1. `product-score-fast-fast`
2. `product-score-mid`
3. `product-score`
4. `niamoto-score`

## Prochaines actions recommandées

### Immédiat

- commiter le runner patché
- lancer un run de 50 itérations pour vérifier que le nouveau flow fonctionne

### Si des candidats passent surrogate-mid

- inspecter la queue de promotions
- choisir le meilleur et lancer la validation stack manuellement

### Si aucun candidat ne passe après 50 itérations

- analyser les patterns d'échec dans le log
- envisager d'élargir le périmètre des fichiers autorisés
  (par ex. `fusion_features.py`)
- ou enrichir le prompt avec des hypothèses plus ciblées

## Commandes utiles

### Vérifier qu'aucun run n'est actif

```bash
ps -Ao pid,ppid,etime,%cpu,command | rg 'run_fusion_surrogate_autoresearch|codex exec|product-score-fast-fast'
```

### Relire les promotions

```bash
cat .autoresearch/fusion-surrogate-promotions.jsonl 2>/dev/null || echo "Aucune promotion encore"
```

### Appliquer un diff de promotion manuellement

```bash
# Extraire le diff du candidat N depuis le JSONL, puis :
git apply < candidate_N.patch
```
