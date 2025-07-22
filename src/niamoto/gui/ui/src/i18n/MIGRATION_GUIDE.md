# Guide de migration i18n

Ce guide explique comment migrer les composants existants pour utiliser le système de traduction.

## 1. Importer le hook de traduction

```tsx
import { useTranslation } from 'react-i18next';
```

## 2. Initialiser le hook dans le composant

```tsx
// Pour un seul namespace
const { t } = useTranslation('import');

// Pour plusieurs namespaces
const { t } = useTranslation(['import', 'common']);
```

## 3. Remplacer les textes hardcodés

### Texte simple
```tsx
// Avant
<h1>Import de données</h1>

// Après
<h1>{t('title')}</h1>
```

### Avec namespace spécifique
```tsx
// Avant
<button>Suivant</button>

// Après
<button>{t('common:actions.next')}</button>
```

### Avec interpolation
```tsx
// Avant
<p>Fichier sélectionné: {fileName}</p>

// Après
<p>{t('source.fileSelected', { fileName })}</p>
```

### Avec pluralisation
```tsx
// Dans le fichier de traduction
{
  "items_one": "{{count}} élément",
  "items_other": "{{count}} éléments"
}

// Dans le composant
<p>{t('items', { count: itemCount })}</p>
```

## 4. Conventions de nommage des clés

- Utiliser la notation par points pour la hiérarchie : `section.subsection.key`
- Grouper par fonctionnalité : `actions.save`, `status.loading`, etc.
- Éviter les clés trop longues ou trop courtes
- Être cohérent dans le nommage

## 5. Organisation des fichiers de traduction

```
src/i18n/locales/
├── fr/
│   ├── common.json    # Termes généraux, actions, validations
│   ├── import.json    # Page d'import
│   ├── transform.json # Page de transformation
│   └── ...
└── en/
    └── ... (même structure)
```

## 6. Tester les traductions

1. Changer de langue via le sélecteur
2. Vérifier que tous les textes changent
3. Vérifier l'interpolation des variables
4. Tester les cas limites (textes longs, caractères spéciaux)

## 7. Checklist de migration

- [ ] Importer useTranslation
- [ ] Initialiser le hook avec le(s) bon(s) namespace(s)
- [ ] Remplacer tous les textes hardcodés
- [ ] Ajouter les traductions dans les fichiers JSON (FR et EN)
- [ ] Tester le changement de langue
- [ ] Vérifier que les types TypeScript sont corrects
