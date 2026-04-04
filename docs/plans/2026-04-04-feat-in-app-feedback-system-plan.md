---
title: "In-App Feedback System"
type: feat
date: 2026-04-04
---

# In-App Feedback System

## Overview

Système de feedback intégré à Niamoto Desktop permettant aux chercheurs et botanistes de signaler des bugs, suggérer des améliorations, ou poser des questions — directement depuis l'application, sans compte GitHub. Les feedbacks sont envoyés comme GitHub Issues via un proxy Cloudflare Worker.

**Brainstorm de référence** : `docs/brainstorms/2026-04-03-feedback-system-brainstorm.md`

## Problem Statement

Les utilisateurs de Niamoto Desktop (botanistes, écologues) n'ont aucun moyen intégré de remonter des problèmes ou suggestions. Ils doivent contacter l'équipe par email ou message, sans contexte technique (version, OS, erreurs console, page courante). Le diagnostic est lent et incomplet.

**Objectifs** :
- Un feedback = 1 clic + 1 titre → une GitHub Issue complète avec contexte automatique
- Friction minimale pour un public non-technique
- Le token GitHub ne sort jamais du Worker (sécurité)
- Coût d'infrastructure : zéro (CF Workers free tier + R2 free tier)

## Architecture

```
┌──────────────────┐     POST /feedback      ┌──────────────────┐      ┌─────────────┐
│  Niamoto Desktop │ ──────────────────────→  │  CF Worker       │ ───→ │ GitHub API  │
│  (React/Tauri)   │   X-Feedback-Key         │  (niamoto-proxy) │      │ Issues      │
└──────────────────┘                          └────────┬─────────┘      └─────────────┘
                                                       │
                                                       ↓
                                               ┌──────────────┐
                                               │  CF R2       │
                                               │  (images)    │
                                               └──────────────┘
```

Le POST va **directement** du navigateur/Tauri au Worker (pas de proxy via le backend FastAPI local). Cela garantit que le feedback fonctionne même si le backend local crashe — exactement le moment où l'utilisateur a le plus besoin de remonter un problème.

Conséquence directe : la disponibilité du feedback ne doit pas dépendre de `useNetworkStatus().isOffline` ni d'un check backend local. Pour cette feature, la source de vérité est la connectivité navigateur (`navigator.onLine`) et, en dernier ressort, le résultat réel du POST vers le Worker.

## Proposed Solution

### Composants

| Composant | Emplacement | Rôle |
|-----------|-------------|------|
| Feature module `feedback` | `src/features/feedback/` | Modal, hooks, types, service API |
| Console error buffer | `src/app/main.tsx` (init) | Capture les 10 dernières erreurs |
| Bouton sidebar | `NavigationSidebar.tsx` | Point d'entrée principal |
| Entrée Command Palette | `CommandPalette.tsx` | Fallback quand sidebar masquée |
| Namespace i18n `feedback` | `locales/{en,fr}/feedback.json` | Traductions |
| Cloudflare Worker | Repo séparé `workers/niamoto-feedback-proxy/` | Proxy sécurisé vers GitHub |
| Bucket R2 | `niamoto-feedback` | Stockage screenshots |

### Dépendance ajoutée

- `html2canvas` (~40KB gzippé) — capture DOM en image

## Technical Approach

### Phase 1 : Infrastructure Worker + R2 (fondation)

Le Worker est un déployable indépendant. Il doit être fonctionnel et testable avant le frontend.

#### 1.1 Cloudflare Worker

**Repo** : `workers/niamoto-feedback-proxy/` (repo séparé ou sous-dossier selon préférence)

```typescript
// workers/niamoto-feedback-proxy/src/index.ts

interface FeedbackPayload {
  type: 'bug' | 'suggestion' | 'question';
  title: string;
  description?: string;
  context: {
    app_version: string;
    os: string;
    current_page: string;
    runtime_mode: string;
    theme: string;
    language: string;
    window_size: string;
    timestamp: string;
    diagnostic?: Record<string, unknown>;
    recent_errors?: Array<{ message: string; stack?: string; timestamp: string }>;
  };
}
```

**Transport HTTP** :
- Requête `multipart/form-data`
- Part `payload` : JSON sérialisé du `FeedbackPayload`
- Part `screenshot` : fichier JPEG optionnel (`File`/`Blob`)

Ce choix évite le surcoût du base64 dans le JSON. Un screenshot JPEG de 5 MB reste transportable sans inflation d'environ 33%, contrairement à une chaîne base64 embarquée dans le payload.

**Sécurité Worker** :
- Clé statique `X-Feedback-Key` — rejet si absente/invalide
- Rate limit : 10 req/min par IP (Cloudflare natif)
- Taille max requête : 6MB ; taille max screenshot : 5MB ; content-type JPEG vérifié sur le fichier uploadé
- Sanitization Markdown : escape `@mentions`, `#refs`, backticks dans le texte utilisateur
- **CORS** : réflexion dynamique de l'en-tête `Origin` si l'origine est dans une allowlist explicite (`tauri://localhost`, `https://tauri.localhost`, `http://localhost:1420`, `http://localhost:1421`, `http://127.0.0.1:1420`, `http://127.0.0.1:1421`)

**Réponses API** :

| Status | Body | Cas |
|--------|------|-----|
| `201` | `{ success: true, issue_url, screenshot_uploaded }` | Issue créée |
| `400` | `{ error: "missing_title" }` | Payload invalide |
| `401` | `{ error: "unauthorized" }` | Clé API invalide |
| `429` | `{ error: "rate_limited", retry_after: 60 }` | Rate limit |
| `502` | `{ error: "github_error", detail }` | GitHub API erreur |
| `500` | `{ error: "internal_error" }` | Erreur Worker |

**Template Issue GitHub** :

```markdown
## {emoji} {Type Label}

### Description
{description sanitisée}

### Screenshot
![screenshot]({r2_url})  <!-- si screenshot_uploaded -->

### Contexte
| | |
|-|-|
| Version | {app_version} |
| OS | {os} |
| Page | {current_page} |
| Mode | {runtime_mode} |
| Thème | {theme} |
| Langue | {language} |
| Fenêtre | {window_size} |

### Erreurs console
```
{recent_errors formatées}  <!-- si présentes -->
```

---
*Envoyé depuis Niamoto Desktop v{app_version}*
```

**Labels auto** : `feedback`, `feedback:{type}`, `from:app`

#### 1.2 Bucket R2

- Bucket : `niamoto-feedback`
- Custom domain : `feedback-assets.niamoto.dev` (pour que GitHub affiche les images)
- Nommage fichiers : `{YYYY-MM-DD}-{nanoid(10)}.jpg` (ex: `2026-04-04-a7b3c9d2e1.jpg`)
- Pas de listing public, accès direct par URL uniquement

#### Acceptance Criteria Phase 1

- [x] `POST /feedback` avec payload valide → Issue GitHub créée avec labels corrects
- [x] Screenshot uploadé en `multipart/form-data` → stocké sur R2 → URL dans l'Issue
- [x] Requête sans `X-Feedback-Key` → 401
- [x] Requête avec payload invalide → 400
- [x] CORS headers corrects pour origines Tauri
- [x] Rate limit fonctionnel (10/min)
- [ ] Tests du Worker (miniflare ou vitest)

---

### Phase 2 : Frontend — Feature Module (core)

#### 2.1 Structure du module

```
src/features/feedback/
├── components/
│   ├── FeedbackModal.tsx          # Modal principal (Dialog shadcn)
│   ├── FeedbackTypeSelector.tsx   # Toggle buttons Bug/Suggestion/Question
│   ├── ScreenshotPreview.tsx      # Miniature + toggle envoi
│   └── ContextDetails.tsx         # Section collapsible données envoyées
├── context/
│   └── FeedbackProvider.tsx       # État partagé: ouverture, capture, draft, envoi
├── hooks/
│   ├── useFeedback.ts             # API publique du provider
│   ├── useScreenshot.ts           # html2canvas capture + compression
│   └── useContextData.ts          # Collecte contexte (version, OS, page, etc.)
├── lib/
│   ├── feedback-api.ts            # POST multipart vers le Worker
│   ├── redact.ts                  # Redaction chemins/usernames
│   └── error-buffer.ts            # Console error buffer (init + read)
├── types.ts                       # Types TypeScript
└── index.ts                       # Barrel exports
```

#### 2.2 Console Error Buffer (`error-buffer.ts`)

Initialisé dans `main.tsx` **avant** `createRoot()` pour capturer les erreurs de boot.

```typescript
// src/features/feedback/lib/error-buffer.ts

interface ErrorEntry {
  message: string;
  stack?: string;
  timestamp: string;
}

const BUFFER_SIZE = 10;
const buffer: ErrorEntry[] = [];

export function initErrorBuffer(): void {
  const originalError = console.error;
  console.error = (...args: unknown[]) => {
    pushEntry(args.map(String).join(' '));
    originalError.apply(console, args);
  };
  window.addEventListener('unhandledrejection', (event) => {
    pushEntry(event.reason?.message || String(event.reason), event.reason?.stack);
  });
}

function pushEntry(message: string, stack?: string): void {
  if (buffer.length >= BUFFER_SIZE) buffer.shift();
  buffer.push({ message, stack, timestamp: new Date().toISOString() });
}

export function getRecentErrors(): ErrorEntry[] {
  return [...buffer];
}
```

```typescript
// main.tsx — ajout avant createRoot
import { initErrorBuffer } from '@/features/feedback/lib/error-buffer';
initErrorBuffer();
// ... createRoot(...)
```

#### 2.3 Redaction (`redact.ts`)

```typescript
// src/features/feedback/lib/redact.ts

export function redact(text: string): string {
  return text
    // macOS: /Users/<username>/... → <user>/...
    .replace(/\/Users\/[^/]+\//g, '<user>/')
    // Windows: C:\Users\<username>\... → <user>\...
    .replace(/[A-Z]:\\Users\\[^\\]+\\/gi, '<user>\\')
    // Home dir tilde expansion artifacts
    .replace(/~\/[^/\s]+/g, '<home>');
}

export function redactObject<T>(obj: T): T {
  if (typeof obj === 'string') return redact(obj) as T;
  if (Array.isArray(obj)) return obj.map(redactObject) as T;
  if (obj && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [k, redactObject(v)])
    ) as T;
  }
  return obj;
}
```

#### 2.4 Screenshot Hook (`useScreenshot.ts`)

```typescript
// src/features/feedback/hooks/useScreenshot.ts

export function useScreenshot() {
  const [screenshot, setScreenshot] = useState<Blob | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState(false);

  const capture = useCallback(async () => {
    setIsCapturing(true);
    setError(false);
    try {
      const { default: html2canvas } = await import('html2canvas');
      const canvas = await html2canvas(document.body, { useCORS: true, scale: 1 });
      // scale: 1 force résolution 1x (évite les screenshots >5MB sur Retina)
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.7)
      );
      if (blob && blob.size > 5 * 1024 * 1024) {
        // Fallback: qualité réduite
        const fallback = await new Promise<Blob | null>((resolve) =>
          canvas.toBlob(resolve, 'image/jpeg', 0.4)
        );
        setScreenshot(fallback);
      } else {
        setScreenshot(blob);
      }
    } catch {
      setError(true);
      setScreenshot(null);
    } finally {
      setIsCapturing(false);
    }
  }, []);

  return { screenshot, isCapturing, error, capture, clear: () => setScreenshot(null) };
}
```

**Point clé** : `scale: 1` empêche les screenshots surdimensionnés sur écrans Retina. On perd la résolution 2x mais on reste sous 5MB — acceptable pour du feedback.

#### 2.5 Context Data Hook (`useContextData.ts`)

```typescript
// src/features/feedback/hooks/useContextData.ts

export function useContextData() {
  const { pathname } = useLocation();
  const { mode: runtimeMode } = useRuntimeMode();
  const { themeId } = useThemeStore();
  const { i18n } = useTranslation();

  const collect = useCallback(async (): Promise<FeedbackContext> => {
    const context: FeedbackContext = {
      app_version: __APP_VERSION__,
      os: navigator.userAgent,
      current_page: pathname,
      runtime_mode: runtimeMode,
      theme: themeId,
      language: i18n.language,
      window_size: `${window.innerWidth}×${window.innerHeight}`,
      timestamp: new Date().toISOString(),
    };

    // Diagnostic détaillé uniquement si le backend local répond.
    // Ce bloc ne doit jamais bloquer l'ouverture ni l'envoi du feedback.
    try {
      const response = await fetch('/api/health/diagnostic', {
        signal: AbortSignal.timeout(1500),
      });
      if (response.ok) {
        const diagnostic = await response.json();
        context.diagnostic = redactObject({
          database: diagnostic.database,
          config_files: diagnostic.config_files,
        });
      }
    } catch {
      // backend local indisponible: contexte minimal uniquement
    }

    return context;
  }, [pathname, runtimeMode, themeId, i18n.language]);

  return { collect };
}
```

#### 2.6 Feedback API (`feedback-api.ts`)

```typescript
// src/features/feedback/lib/feedback-api.ts

const WORKER_URL = import.meta.env.VITE_FEEDBACK_WORKER_URL;
const API_KEY = import.meta.env.VITE_FEEDBACK_API_KEY;

interface FeedbackSubmission {
  payload: FeedbackPayload;
  screenshot?: Blob | null;
}

export async function sendFeedback({ payload, screenshot }: FeedbackSubmission): Promise<FeedbackResponse> {
  const formData = new FormData();
  formData.append('payload', JSON.stringify(payload));
  if (screenshot) {
    formData.append('screenshot', screenshot, 'feedback.jpg');
  }

  const response = await fetch(`${WORKER_URL}/feedback`, {
    method: 'POST',
    headers: {
      'X-Feedback-Key': API_KEY,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'unknown' }));
    throw new FeedbackError(response.status, error);
  }

  return response.json();
}
```

**Note** : `fetch` direct vers le Worker (pas via le client axios du backend local). Variables d'environnement Vite pour URL et clé. Le screenshot circule comme fichier binaire optionnel, pas comme base64 dans le JSON.

#### 2.7 Modal principal (`FeedbackModal.tsx`)

Structure :
1. **Header** : titre + bouton close
2. **Type selector** : 3 toggle buttons (Bug 🐛 / Suggestion 💡 / Question ❓)
3. **Formulaire** : titre (requis, 200 car) + description (optionnel, 5000 car)
4. **Screenshot preview** : miniature + checkbox "Inclure la capture d'écran"
5. **Contexte** : section collapsible `<details>` montrant les données envoyées (redacted)
6. **Footer** : bouton Envoyer (avec spinner/cooldown)

**Comportement type ↔ screenshot** :
- Bug : screenshot préparé avant ouverture, checkbox cochée par défaut
- Suggestion/Question : screenshot non capturé, checkbox décochée
- Changer de type modifie le défaut de la checkbox mais ne supprime pas un screenshot déjà capturé
- L'utilisateur peut toujours cocher/décocher manuellement

**Confirmation avant fermeture** : si titre ou description non vide, afficher une `AlertDialog` "Abandonner le feedback ?" avant de fermer le modal.

**Focus management** : à l'ouverture, focus sur le champ titre. À la fermeture, focus retour sur le bouton déclencheur (géré nativement par Radix Dialog).

#### 2.8 Hook principal (`useFeedback.ts`)

Gère l'état global du feedback via un provider léger : ouverture modal, type courant, screenshot préparé, cooldown, envoi.

```typescript
// src/features/feedback/context/FeedbackProvider.tsx

const COOLDOWN_SECONDS = 30;

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [type, setType] = useState<'bug' | 'suggestion' | 'question'>('bug');
  const [isSending, setIsSending] = useState(false);
  const [cooldownEnd, setCooldownEnd] = useState<number | null>(null);
  const { screenshot, isCapturing, error: screenshotError, capture, clear } = useScreenshot();

  const cooldownRemaining = useCooldownTimer(cooldownEnd);

  const openWithType = useCallback(async (nextType: 'bug' | 'suggestion' | 'question' = 'bug') => {
    setType(nextType);
    if (nextType === 'bug') {
      await capture();
    } else {
      clear();
    }
    setIsOpen(true);
  }, [capture, clear]);

  const send = useCallback(async (data: FeedbackFormData) => {
    setIsSending(true);
    try {
      const result = await sendFeedback(/* payload assemblé */);
      toast.success(t('feedback.success'), {
        description: t('feedback.issue_created'),
        action: result.issue_url ? {
          label: t('feedback.view_issue'),
          onClick: () => window.open(result.issue_url, '_blank'),
        } : undefined,
      });
      setIsOpen(false);
      setCooldownEnd(Date.now() + COOLDOWN_SECONDS * 1000);
    } catch (error) {
      if (error instanceof FeedbackError) {
        if (error.status === 429) {
          toast.error(t('feedback.rate_limited'));
        } else {
          toast.error(t('feedback.send_error'));
        }
      }
      // Modal reste ouvert — pas de perte de données
    } finally {
      setIsSending(false);
    }
  }, []);

  const value = {
    isOpen,
    type,
    setType,
    openWithType,
    close: () => setIsOpen(false),
    send,
    isSending,
    cooldownRemaining,
    screenshot,
    screenshotError,
    isPreparingScreenshot: isCapturing,
  };

  return <FeedbackContext.Provider value={value}>{children}</FeedbackContext.Provider>;
}
```

**Modèle d'état** :
- Le provider est monté une seule fois dans `MainLayout`
- Sidebar et Command Palette consomment `openWithType()` et `isPreparingScreenshot`
- Le modal consomme le même contexte, ce qui évite les états divergents entre déclencheur, capture et formulaire

**Cooldown** : stocké en state React au niveau feature (pas zustand). Persiste entre ouvertures/fermetures du modal tant que `MainLayout` reste monté.

#### Acceptance Criteria Phase 2

- [x] `src/features/feedback/` créé avec la structure décrite
- [x] `html2canvas` ajouté aux dépendances (`pnpm add html2canvas`)
- [x] Error buffer initialisé dans `main.tsx` avant `createRoot()`
- [x] Modal fonctionnel : titre requis, 3 types, screenshot preview, contexte collapsible
- [x] Screenshot capturé avant ouverture modal (type bug), `scale: 1`, JPEG ≤ 5MB
- [x] Redaction appliquée sur toutes les données contextuelles avant affichage et envoi
- [x] Confirmation avant fermeture si formulaire non vide
- [x] `fetch` direct vers le Worker en `multipart/form-data` (pas via axios/backend local)
- [x] Variables d'env Vite : `VITE_FEEDBACK_WORKER_URL`, `VITE_FEEDBACK_API_KEY`
- [x] Gestion erreurs : toast par code HTTP, modal préservé en cas d'échec
- [x] Cooldown 30s visible sur le bouton après envoi réussi

---

### Phase 3 : Intégration UI (bouton + palette + i18n)

#### 3.1 Bouton Sidebar

**Fichier** : `src/components/layout/NavigationSidebar.tsx` (section footer, ~ligne 116)

Ajout d'un bouton `MessageSquarePlus` (Lucide) dans le footer, **avant** le lien Settings.

```tsx
// Dans le footer de NavigationSidebar
<Tooltip>
  <TooltipTrigger asChild>
    <button
      onClick={() => feedback.openWithType('bug')}
      disabled={!browserOnline || feedback.cooldownRemaining > 0 || feedback.isPreparingScreenshot}
      aria-label={t('feedback.button_label')}
      className="..."
    >
      {feedback.isPreparingScreenshot ? <Loader2 className="animate-spin" /> : <MessageSquarePlus />}
      {feedback.cooldownRemaining > 0 && (
        <span className="text-xs">{feedback.cooldownRemaining}s</span>
      )}
    </button>
  </TooltipTrigger>
  <TooltipContent>
    {!browserOnline ? t('feedback.offline_tooltip') : t('feedback.button_label')}
  </TooltipContent>
</Tooltip>
```

**États du bouton** :
| État | Visuel |
|------|--------|
| Normal | Icône `MessageSquarePlus`, tooltip "Envoyer un feedback" |
| Hors connexion | Grisé, tooltip "Feedback indisponible hors connexion" |
| Capture en cours | Spinner `Loader2` rotatif, disabled |
| Cooldown actif | Compteur "23s" à côté de l'icône, disabled |

**Modes sidebar** :
- `full` : icône + label texte
- `compact` : icône seule + tooltip
- `hidden` : bouton absent (Command Palette uniquement)

**Détection offline pour cette feature** : utiliser un hook local `useBrowserOnlineStatus()` basé sur `navigator.onLine` et `online/offline`. Ne pas réutiliser `useNetworkStatus().isOffline`, qui dépend du backend local.

**Vérification TooltipProvider** : le sidebar utilise déjà des tooltips — le provider est disponible dans le contexte.

**Condition projet chargé** : le bouton n'apparaît que dans `MainLayout` (le `WelcomeScreen` est une route séparée sans sidebar), donc le gating est naturel.

#### 3.2 Command Palette

**Fichier** : `src/components/layout/CommandPalette.tsx` (~ligne 134, groupe Tools)

```tsx
// Nouveau CommandItem dans le groupe Tools
  <CommandItem
    value="feedback"
    keywords={['feedback', 'bug', 'report', 'suggestion', 'question', 'signaler']}
    onSelect={() => {
      setCommandPaletteOpen(false);
      feedback.openWithType('bug');
    }}
    disabled={!browserOnline}
  >
  <MessageSquarePlus className="mr-2 h-4 w-4" />
  {t('feedback.command_palette_label')}
</CommandItem>
```

**Mécanisme** : le modal feedback est rendu au niveau `App.tsx` ou `MainLayout` (pas dans le sidebar), ce qui le rend accessible depuis n'importe quel déclencheur. L'état `isOpen` est géré par le hook `useFeedback` qui peut être partagé via un context léger ou un store zustand minimal.

#### 3.3 i18n

**Fichiers à créer** :
- `src/i18n/locales/fr/feedback.json`
- `src/i18n/locales/en/feedback.json`

**Fichier à modifier** :
- `src/i18n/index.ts` — ajouter `feedback` aux namespaces et imports

```json
// locales/fr/feedback.json
{
  "button_label": "Envoyer un feedback",
  "offline_tooltip": "Feedback indisponible hors connexion",
  "command_palette_label": "Envoyer un feedback",
  "modal_title": "Feedback",
  "type_bug": "Bug",
  "type_suggestion": "Suggestion",
  "type_question": "Question",
  "title_label": "Titre",
  "title_placeholder": "Décrivez brièvement le problème",
  "title_required": "Le titre est requis",
  "description_label": "Description",
  "description_placeholder": "Détails supplémentaires (optionnel)",
  "screenshot_label": "Inclure la capture d'écran",
  "screenshot_unavailable": "Capture indisponible",
  "context_label": "Données envoyées",
  "send": "Envoyer",
  "sending": "Envoi...",
  "success": "Feedback envoyé !",
  "issue_created": "Votre retour a été enregistré.",
  "view_issue": "Voir",
  "send_error": "Impossible d'envoyer le feedback. Réessayez.",
  "rate_limited": "Trop de feedbacks envoyés, réessayez dans quelques minutes.",
  "confirm_close_title": "Abandonner le feedback ?",
  "confirm_close_description": "Le contenu du formulaire sera perdu.",
  "confirm_close_cancel": "Continuer",
  "confirm_close_confirm": "Abandonner",
  "cooldown": "Envoyé ({{seconds}}s)"
}
```

#### 3.4 Montage du modal

**Fichier** : `src/app/App.tsx` ou `src/components/layout/MainLayout.tsx`

Le `<FeedbackModal />` est rendu dans le layout principal, indépendant du sidebar. L'état est partagé via un `FeedbackProvider` context ou un store zustand minimal.

```tsx
// MainLayout.tsx — ajout
import { FeedbackProvider } from '@/features/feedback';

// Dans le JSX, au même niveau que le Toaster
<FeedbackProvider>
  {/* existing layout */}
  <FeedbackModal />
</FeedbackProvider>
```

#### Acceptance Criteria Phase 3

- [x] Bouton feedback visible dans la sidebar (modes full et compact)
- [x] Bouton grisé hors connexion avec tooltip explicatif
- [x] Spinner sur le bouton pendant la capture screenshot
- [x] Entrée "Envoyer un feedback" dans la Command Palette (Cmd+K)
- [x] Command Palette grisée si hors connexion
- [x] Namespace i18n `feedback` avec traductions fr et en
- [x] Modal accessible depuis sidebar ET Command Palette
- [x] Bouton non visible sur le WelcomeScreen (pas de projet chargé)

---

### Phase 4 : Polish et accessibilité

#### 4.1 Accessibilité

- [x] `aria-label` sur le bouton sidebar (icône seule)
- [x] Focus automatique sur le champ titre à l'ouverture du modal
- [x] Focus retour sur le déclencheur à la fermeture (natif Radix Dialog)
- [x] Validation formulaire avec `aria-invalid` et `aria-describedby` sur les champs en erreur
- [ ] Cooldown countdown en `aria-live="polite"` pour les lecteurs d'écran
- [x] Toast `sonner` utilise `aria-live` par défaut — vérifier

#### 4.2 Gestion offline pendant la saisie

Le feedback ne doit pas dépendre du backend local. On utilise **uniquement** `navigator.onLine` + événements `online`/`offline` pour l'état interactif de la feature, car :
- Le feedback POST va directement au Worker, pas au backend local
- Si le backend local est down mais internet disponible, on veut pouvoir envoyer
- La vraie vérification finale reste le résultat du POST lui-même

```typescript
// Dans useBrowserOnlineStatus.ts ou FeedbackProvider
const browserOnline = useSyncExternalStore(
  (cb) => { window.addEventListener('online', cb); window.addEventListener('offline', cb); return () => { ... }; },
  () => navigator.onLine
);
```

Si `browserOnline` passe à `false` pendant la saisie :
- Bouton "Envoyer" grisé + message inline "Connexion perdue — réessayez quand la connexion reviendra"
- Formulaire reste éditable (pas de perte de données)
- Quand `browserOnline` repasse à `true`, le bouton se réactive

#### 4.3 Transition offline détaillée

Pour le **bouton sidebar**, la **Command Palette** et le **bouton "Envoyer" dans le modal**, on utilise le même signal `browserOnline`.

On évite volontairement `useNetworkStatus().isOffline` dans cette feature, car il mélange disponibilité Internet et disponibilité du backend local. Ce couplage est incorrect ici.

#### 4.4 Tests

- [x] Tests unitaires : `redact.ts` (macOS paths, Windows paths, paths dans stack traces, unicode)
- [x] Tests unitaires : `error-buffer.ts` (push, circular, getRecentErrors)
- [ ] Tests composants : `FeedbackModal` (rendu, soumission, validation, états)
- [ ] Test intégration : envoi complet feedback → vérification payload (mock du Worker)
- [ ] Test manuel : vérifier html2canvas sur les 10 thèmes

#### Acceptance Criteria Phase 4

- [x] Accessibilité ARIA complète sur bouton et modal
- [x] Gestion offline cohérente basée sur `browserOnline` pour toute la feature
- [x] Tests unitaires redact + error-buffer passent
- [ ] Tests composants modal passent
- [ ] html2canvas vérifié visuellement sur au moins 3 thèmes (frond, basalt, forest)

---

## Décisions de design

### Direct POST vs. Proxy Backend

**Choix : Direct POST au Worker.**

Le backend local FastAPI peut crasher. C'est précisément le moment où l'utilisateur veut envoyer un feedback. Passer par le backend rendrait le feedback indisponible quand il est le plus utile.

Conséquence : CORS nécessaire sur le Worker, mais c'est 5 lignes de config.

### API Key : `import.meta.env` vs `define`

**Choix : `import.meta.env.VITE_FEEDBACK_API_KEY`.**

Avantages :
- Configurable par environnement (`.env.development`, `.env.production`)
- Pattern standard Vite, cohérent avec d'autres configs
- Rotation = rebuild + redeploy (acceptable pour une clé garde-fou)

### Error Buffer : `main.tsx` vs `RootProviders.tsx`

**Choix : `main.tsx` avant `createRoot()`.**

Les erreurs les plus utiles au diagnostic sont celles qui surviennent au boot (crash React, API failure, module import). Initialiser le buffer après le montage React les raterait.

### Screenshot `scale: 1` vs `devicePixelRatio`

**Choix : `scale: 1` (résolution standard).**

Sur un écran Retina (2x), `html2canvas` par défaut capture à la résolution native (3840×2400 pour un écran 1920×1200). Le JPEG résultant dépasse facilement 5MB. Forcer `scale: 1` produit un screenshot 1920×1200 qui reste sous 2MB en JPEG 0.7.

Perte : résolution réduite. Acceptable pour du feedback — la description textuelle complète l'image.

### Screenshot transport : base64 JSON vs. `multipart/form-data`

**Choix : `multipart/form-data`.**

Avantages :
- Pas d'inflation base64 dans le payload
- Contrat clair entre "payload JSON" et "fichier screenshot"
- Plus simple à valider côté Worker (type MIME + taille)

Conséquence : le `fetch` frontend construit un `FormData` et le Worker parse la requête multipart.

### Cooldown : state React vs. Zustand

**Choix : state React au niveau feature.**

Le cooldown de 30s n'a pas besoin de persister entre les sessions. Un simple state React dans un `FeedbackProvider` monté dans `MainLayout` suffit. Il persiste tant que l'app reste dans le layout principal.

### Offline detection : `useNetworkStatus` vs. `navigator.onLine`

**Choix : `navigator.onLine` pour toute la feature feedback.**

- Sidebar / Command Palette / modal → `navigator.onLine`
- Le POST réel au Worker reste l'arbitre final du succès ou de l'échec

### Contexte système : enrichissement léger vs. dépendances Tauri supplémentaires

**Choix : contexte minimal en V1, sans ajouter de dépendance Tauri filesystem.**

- `navigator.userAgent` suffit pour `os` en V1
- `diagnostic` est facultatif et ne doit jamais bloquer si le backend local ne répond pas
- `db_size` sort du scope V1, sauf si le backend `/api/health/diagnostic` l'expose déjà proprement plus tard

## Dependencies & Prerequisites

| Prérequis | Phase | Notes |
|-----------|-------|-------|
| Compte Cloudflare avec Workers activé | Phase 1 | Free tier suffisant |
| R2 bucket `niamoto-feedback` + custom domain | Phase 1 | Free tier (10GB) |
| Fine-grained PAT GitHub `issues:write` sur `niamoto/niamoto` | Phase 1 | Secret Worker (`wrangler secret`) |
| `html2canvas` npm package | Phase 2 | `pnpm add html2canvas` |
| Variables d'env Vite | Phase 2 | `.env.production` avec URL Worker et clé API |
| Aucun plugin Tauri supplémentaire requis en V1 | Phase 2 | Pas de dépendance `plugin-fs`/`plugin-os` nécessaire pour la première version |

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Screenshots illisibles sur certains thèmes (html2canvas + CSS vars) | Moyenne | Faible | Description textuelle complète l'image ; `scale: 1` réduit la complexité |
| Clé API extraite du bundle | Moyenne | Faible | Rate limit IP + garde-fou, pas une auth forte — accepté |
| Screenshots avec données sensibles sur l'écran | Faible | Moyen | Preview visible avant envoi, checkbox opt-in |
| Redaction incomplète (paths dans stack traces) | Moyenne | Moyen | Tests unitaires extensifs, regex conservatif |
| R2 URLs énumérables | Faible | Faible | Nanoid 10 chars = ~1 trillion combinaisons |
| Backend local indisponible alors qu'Internet fonctionne | Moyenne | Élevé | La feature n'utilise pas `useNetworkStatus`; contexte minimal si `/api/health/diagnostic` échoue |

## Hors Scope

- File d'attente offline (YAGNI)
- Annotation sur screenshot
- Authentification utilisateur
- Dashboard feedback dans l'app
- Raccourci clavier dédié (Cmd+Shift+F)

## Fichiers Impactés

### Nouveaux

| Fichier | Rôle |
|---------|------|
| `src/features/feedback/components/FeedbackModal.tsx` | Modal principal |
| `src/features/feedback/components/FeedbackTypeSelector.tsx` | Sélecteur Bug/Suggestion/Question |
| `src/features/feedback/components/ScreenshotPreview.tsx` | Miniature screenshot |
| `src/features/feedback/components/ContextDetails.tsx` | Section collapsible contexte |
| `src/features/feedback/context/FeedbackProvider.tsx` | État partagé feedback |
| `src/features/feedback/hooks/useFeedback.ts` | Hook principal (état, envoi, cooldown) |
| `src/features/feedback/hooks/useScreenshot.ts` | Hook capture html2canvas |
| `src/features/feedback/hooks/useContextData.ts` | Hook collecte contexte |
| `src/features/feedback/lib/feedback-api.ts` | Client API Worker |
| `src/features/feedback/lib/redact.ts` | Redaction données sensibles |
| `src/features/feedback/lib/error-buffer.ts` | Buffer erreurs console |
| `src/features/feedback/types.ts` | Types TypeScript |
| `src/features/feedback/index.ts` | Barrel exports |
| `src/i18n/locales/fr/feedback.json` | Traductions FR |
| `src/i18n/locales/en/feedback.json` | Traductions EN |
| `workers/niamoto-feedback-proxy/` | Worker CF (repo séparé) |

### Modifiés

| Fichier | Modification |
|---------|-------------|
| `src/app/main.tsx` | Init error buffer avant `createRoot()` |
| `src/components/layout/NavigationSidebar.tsx` | Ajout bouton feedback dans le footer |
| `src/components/layout/CommandPalette.tsx` | Ajout entrée "Feedback" dans Tools |
| `src/components/layout/MainLayout.tsx` | Montage `FeedbackModal` + provider |
| `src/i18n/index.ts` | Ajout namespace `feedback` |
| `package.json` | Ajout `html2canvas` |
| `.env.production` | `VITE_FEEDBACK_WORKER_URL`, `VITE_FEEDBACK_API_KEY` |

## References

### Internes
- Brainstorm : `docs/brainstorms/2026-04-03-feedback-system-brainstorm.md`
- Offline support plan : `docs/plans/2026-02-05-feat-offline-support-desktop-app-plan.md`
- Sidebar : `src/niamoto/gui/ui/src/components/layout/NavigationSidebar.tsx`
- Command Palette : `src/niamoto/gui/ui/src/components/layout/CommandPalette.tsx`
- useNetworkStatus : `src/niamoto/gui/ui/src/shared/hooks/useNetworkStatus.ts`
- Theme store : `src/niamoto/gui/ui/src/stores/themeStore.ts`
- Toast (sonner) : `src/niamoto/gui/ui/src/app/App.tsx:202`
- i18n config : `src/niamoto/gui/ui/src/i18n/index.ts`
- Dialog shadcn : `src/niamoto/gui/ui/src/components/ui/dialog.tsx`
