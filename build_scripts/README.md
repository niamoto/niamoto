# Niamoto Desktop - Build Scripts

Scripts pour créer une application desktop Tauri à partir de l'application web Niamoto existante.

## 🎯 Approche Simple

**Wrapper Tauri autour de FastAPI + React existants = Application desktop**

Aucune modification du code Python ou React n'est nécessaire.

## 📁 Fichiers

```
build_scripts/
├── README.md                 # Ce fichier
├── init_tauri.sh            # Initialise la structure Tauri
├── build_desktop.sh         # Build l'application complète
├── niamoto.spec             # Configuration PyInstaller
└── templates/
    ├── main.rs              # Backend Rust Tauri
    └── tauri.conf.json      # Configuration Tauri
```

## 🚀 Démarrage Rapide

### Étape 1 : Initialiser Tauri

```bash
./build_scripts/init_tauri.sh
```

Cela crée la structure `src-tauri/` avec tous les fichiers nécessaires.

### Étape 2 : Ajouter des Icônes

Placez vos icônes dans `src-tauri/icons/` :
- `icon.icns` (macOS)
- `icon.ico` (Windows)
- `32x32.png`, `128x128.png`, `128x128@2x.png` (Linux)

**Astuce** : Vous pouvez utiliser un outil comme [Icon Kitchen](https://icon.kitchen) pour générer toutes les tailles à partir d'une seule image PNG 1024x1024.

### Étape 3 : Build l'Application

```bash
./build_scripts/build_desktop.sh
```

Cette commande :
1. Bundle Python avec PyInstaller (~350-400 MB)
2. Build React frontend
3. Compile l'application Tauri
4. Génère les installateurs dans `src-tauri/target/release/bundle/`

## 🧪 Développement

Pour développer et tester :

**Terminal 1** - FastAPI :
```bash
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc
```

**Terminal 2** - Tauri :
```bash
cd src-tauri
cargo tauri dev
```

Le mode dev recharge automatiquement sur modification du code.

## 📦 Installateurs Générés

Selon votre OS :

- **macOS** : `.dmg` et `.app` dans `bundle/dmg/` et `bundle/macos/`
- **Linux** : `.deb` et `.AppImage` dans `bundle/deb/` et `bundle/appimage/`
- **Windows** : `.msi` et `.exe` dans `bundle/msi/` et `bundle/nsis/`

## ⚙️ Prérequis

### Système

- **Python 3.12+** avec toutes les dépendances Niamoto
- **Node.js 18+** et pnpm
- **Rust** (installer avec https://rustup.rs/)
- **PyInstaller** : `pip install pyinstaller==6.19.0`

### Dépendances Supplémentaires

**macOS** :
```bash
xcode-select --install
```

Vérification locale de signature / notarisation :
```bash
scripts/dev/verify_macos_distribution.sh --ad-hoc --skip-spctl
scripts/dev/verify_macos_distribution.sh
scripts/dev/verify_macos_distribution.sh --notarize
```

**Linux (Ubuntu/Debian)** :
```bash
sudo apt update
sudo apt install libwebkit2gtk-4.0-dev \
    build-essential \
    curl \
    wget \
    file \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
```

**Windows** :
- Visual Studio Build Tools ou Visual Studio Community
- WebView2 (généralement déjà installé sur Windows 10/11)

## 🔧 Personnalisation

### Modifier le Port par Défaut

Éditez `templates/main.rs`, fonction `launch_fastapi_server()` :
```rust
.args(&["gui", "--port", "8765", ...])
```

### Changer la Taille de Fenêtre

Éditez `templates/tauri.conf.json`, section `windows` :
```json
"width": 1600,
"height": 1000,
```

### Timeout de Démarrage

Dans `templates/main.rs`, modifiez `max_attempts` :
```rust
let max_attempts = 60; // 30 secondes actuellement
```

## 🐛 Dépannage

### PyInstaller ne trouve pas les modules

Ajoutez-les dans `niamoto.spec`, section `hiddenimports` :
```python
hiddenimports = [
    'niamoto',
    'votre_module_manquant',
]
```

### Le serveur ne démarre pas

Vérifiez que :
1. Le bundle Python existe : `ls src-tauri/bin/niamoto`
2. Il est exécutable : `chmod +x src-tauri/bin/niamoto`
3. Testez-le manuellement : `./src-tauri/bin/niamoto gui --port 8765`

### Erreur de build Tauri

```bash
# Nettoyer et rebuilder
cd src-tauri
cargo clean
cargo tauri build
```

### La notarisation macOS échoue en CI

Reproduisez d'abord le problème sur votre machine avec le même bundle :

```bash
scripts/dev/verify_macos_distribution.sh --ad-hoc --skip-spctl
scripts/dev/verify_macos_distribution.sh
```

Le script :
1. répare le layout du `Python.framework` si Tauri a aplati les symlinks
2. signe le sidecar et le bundle `.app`
3. vérifie `codesign` et `spctl`
4. peut soumettre à Apple avec `--notarize`

Utilisez `--ad-hoc --skip-spctl` pour valider rapidement la structure locale sans dépendre du certificat Apple ni de Gatekeeper.

### L'application ne charge pas l'UI

Vérifiez que :
1. React est buildé : `ls gui/ui/dist/index.html`
2. Le health endpoint répond : `curl http://localhost:8765/api/health`

## 📊 Taille du Bundle

Attendu : **~370-420 MB**

Composition :
- Python + dépendances : ~350-400 MB
- Tauri runtime : ~10 MB
- React build : ~5 MB

**Note** : C'est plus gros qu'une optimisation complète, mais :
- ✅ Rapide à implémenter
- ✅ Pas de refonte de code
- ✅ Toutes les fonctionnalités préservées

## 📚 Documentation Complète

Voir `docs/TAURI_SIMPLE.md` pour la documentation détaillée.

## ❓ Questions Fréquentes

**Q : L'app web continue de fonctionner ?**
R : Oui ! Aucun changement. Tauri est une option supplémentaire.

**Q : Dois-je maintenir deux codebases ?**
R : Non. Même code pour web et desktop.

**Q : Puis-je auto-update l'application ?**
R : Oui, Tauri le supporte. Voir la doc Tauri sur les updaters.

**Q : Comment signer l'application pour macOS/Windows ?**
R : Configurez `signingIdentity` (macOS) ou `certificateThumbprint` (Windows) dans `tauri.conf.json`.

## 🚀 Optimisations Futures (Optionnelles)

Si la taille du bundle devient problématique :
- Migrer vers Polars (économie ~30 MB)
- Utiliser DuckDB Spatial au lieu de GeoPandas (économie ~150 MB)
- Lazy loading de certains modules

Mais pour commencer : **Keep It Simple** ✨
