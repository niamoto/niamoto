# Guide de démarrage - Interface GUI Niamoto

Ce guide vous accompagne pas à pas dans l'utilisation de l'interface graphique Niamoto pour créer votre premier projet de données écologiques.

## Prérequis

### Installation de Niamoto

1. **Installer Python 3.10 ou supérieur**
   ```bash
   python --version  # Devrait afficher Python 3.10+
   ```

2. **Installer Niamoto avec les dépendances GUI**
   ```bash
   pip install niamoto[gui]

   # Ou depuis les sources
   git clone https://github.com/niamoto/niamoto.git
   cd niamoto
   pip install -e ".[gui]"
   ```

3. **Vérifier l'installation**
   ```bash
   niamoto --version
   niamoto gui --help
   ```

## Créer votre premier projet

### Méthode 1 : Nouveau projet avec l'interface

1. **Créer un répertoire pour votre projet**
   ```bash
   mkdir mon-projet-flore
   cd mon-projet-flore
   ```

2. **Initialiser avec l'interface GUI**
   ```bash
   niamoto init
   ```

   L'interface s'ouvre automatiquement dans votre navigateur. Si ce n'est pas le cas, allez à http://localhost:8080

3. **Suivre l'assistant de configuration**
   - L'interface vous guide à travers les étapes
   - Commencez par configurer vos sources de données
   - Ajoutez les transformations souhaitées
   - Définissez les paramètres d'export

### Méthode 2 : Projet existant

Si vous avez déjà un projet Niamoto :

```bash
cd mon-projet-existant
niamoto gui
```

L'interface chargera automatiquement vos configurations existantes.

## Interface principale

### 1. Section Import

Cette section définit vos sources de données :

- **Taxonomie CSV** : Le fichier contenant votre référentiel taxonomique
  - Format attendu : CSV avec colonnes family, genus, species
  - Exemple : `imports/taxonomy.csv`

- **Occurrences CSV** : Les observations de terrain
  - Format attendu : CSV avec colonnes id, taxon, geo_pt (coordonnées)
  - Exemple : `imports/occurrences.csv`

- **Données de parcelles** (optionnel) : Pour les inventaires forestiers
  - Cochez la case pour activer
  - Format attendu : CSV avec colonnes id_plot, plot, geo_pt

### 2. Section Transform

Activez les analyses que vous souhaitez effectuer :

- **Top Species Analysis** : Identifie les 10 espèces les plus fréquentes
- **Distribution Maps** : Génère des cartes de distribution géographique

Plus d'options seront disponibles dans les versions futures.

### 3. Section Export

Configure la génération de votre site web :

- **Titre du site** : Le nom de votre projet (ex: "Flore de Nouvelle-Calédonie")
- **Couleur principale** : Personnalisez l'apparence (défaut: #228b22)
- **Generate Static Website** : Cochez pour créer un site web statique

### 4. Génération de la configuration

1. Cliquez sur **"🚀 Generate YAML Configuration"**
2. L'interface valide votre configuration
3. Les fichiers YAML sont générés et affichés
4. Copiez les configurations dans vos fichiers ou utilisez-les directement

## Workflow complet

### Étape 1 : Préparer vos données

Organisez vos fichiers dans la structure suivante :
```
mon-projet/
├── imports/
│   ├── taxonomy.csv
│   ├── occurrences.csv
│   └── plots.csv (optionnel)
└── config/
    └── (les fichiers YAML seront ici)
```

### Étape 2 : Configurer via l'interface

1. Lancez `niamoto gui`
2. Remplissez les chemins vers vos fichiers
3. Sélectionnez les analyses souhaitées
4. Personnalisez l'export

### Étape 3 : Exécuter le pipeline

Une fois la configuration générée :

```bash
# Importer les données
niamoto import

# Exécuter les transformations
niamoto transform

# Générer le site web
niamoto export
```

### Étape 4 : Visualiser le résultat

```bash
# Ouvrir le site généré
cd exports/web
python -m http.server 8000
```

Visitez http://localhost:8000 pour voir votre site.

## Options de la commande GUI

```bash
# Changer le port (défaut: 8080)
niamoto gui --port 3000

# Ne pas ouvrir le navigateur automatiquement
niamoto gui --no-browser

# Mode développement avec rechargement automatique
niamoto gui --reload

# Spécifier l'hôte (défaut: 127.0.0.1)
niamoto gui --host 0.0.0.0
```

## Résolution des problèmes

### "GUI dependencies not installed"

Les dépendances GUI sont maintenant dans les dépendances principales. Si vous rencontrez ce problème :

```bash
# Réinstaller avec les dépendances GUI
pip install --upgrade "niamoto[gui]"

# Ou installer manuellement
pip install fastapi uvicorn[standard]
```

### Port déjà utilisé

Si le port 8080 est occupé :
```bash
niamoto gui --port 8081
```

### L'interface ne charge pas les configurations

Assurez-vous d'être dans le bon répertoire :
- La commande cherche un dossier `config/` dans le répertoire courant
- Ou dans `test-instance/niamoto-og/config/` pour les tests

### Erreurs de validation

L'interface affiche des messages d'erreur détaillés. Vérifiez :
- Que tous les chemins de fichiers sont corrects
- Qu'au moins une source de données est définie
- Qu'au moins un export est configuré

## Prochaines étapes

- Consultez le [parcours utilisateur détaillé](user-workflow.md) pour des cas d'usage avancés
- Explorez la [référence API](../10-roadmaps/gui/api-reference.md) pour intégrer l'interface dans vos workflows
- Lisez la [documentation technique](../10-roadmaps/gui/development/architecture.md) pour comprendre le fonctionnement interne

## Support

En cas de problème :
1. Consultez les logs dans le terminal où vous avez lancé `niamoto gui`
2. Vérifiez la console du navigateur (F12) pour les erreurs JavaScript
3. Ouvrez une issue sur [GitHub](https://github.com/niamoto/niamoto/issues)
