# OpenTutor : Vercel, Render et Supabase

## Demande et décisions

Adapter l'infrastructure du fork sans réécrire les fonctions pédagogiques.
Frontend Next.js sur Vercel (`apps/web`), API FastAPI sur Render (`apps/api`),
PostgreSQL et documents privés chez Supabase. Développement Windows/PowerShell.
L'utilisateur a choisi **Supabase Auth** après présentation de l'alternative JWT locale.
Aucun push, déploiement, transfert SQLite ou migration destructrice sans accord.

## Audit du code au commit 153bac7

| Sujet | Constat dans le code | Adaptation nécessaire |
|---|---|---|
| Monorepo | `apps/api`, `apps/web`, tests Python dans `tests`, tests Vitest auprès des composants, Playwright à la racine | Conserver cette structure |
| Next.js | Next 16.4.3 / React 19, `next.config.ts`, build webpack, port dev 3001 | Root Directory Vercel `apps/web`, vérifier build et lint |
| API | `main.py`, `services/app_lifecycle.py`, registre de routeurs et middleware CORS/CSRF | Conserver FastAPI et les routeurs |
| Connexion SQL | SQLAlchemy 2 async ; `config.py` refuse toute URL hors SQLite | Accepter PostgreSQL, ajouter pilote, TLS et petit pool configurable |
| Modèles | `models/compat.py` transforme UUID en varchar, JSONB en JSON, vecteurs en texte | Types par dialecte ; conserver noms et relations existants |
| Migrations | Alembic historique PostgreSQL, mais première révision ne crée pas les tables de base ; bootstrap SQLite distinct | Ajouter un bootstrap PostgreSQL explicite et tester une base vierge ainsi que la seconde exécution |
| Recherche | Les types de compatibilité permettent déjà des vecteurs sérialisés | Conserver la recherche actuelle sans imposer pgvector ni un nouveau moteur |
| Documents | `routers/upload.py` écrit dans `UPLOAD_DIR`, extrait en local, sauvegarde `IngestionJob.file_path` ; téléchargement avec contrôle user_id | Stocker un identifiant d'objet durable ; extraction temporaire et téléchargement backend authentifié |
| Autres imports | `services/ingestion/canvas_ingest.py` télécharge aussi sur disque | Inclure les imports Canvas dans la persistance distante |
| Suppression | `courses_crud.delete_course` supprime la base, sans nettoyage de fichiers | Associer nettoyage Storage et suppression, prévoir erreurs partielles |
| Auth | Inscription/login/refresh JWT locaux, `get_current_user`, filtres propriétaires existants | Validation Supabase et synchronisation par UUID, connexion frontend, pas d'inscription publique |
| Frontend auth | `lib/auth.ts` lit des jetons mais aucune page de login ; certains fetch (scrape-now) n'utilisent pas les headers communs | Unifier les appels authentifiés et prévoir expiration/renouvellement |
| Tâches | Moteur `services/activity` avec tables, polling et `FOR UPDATE SKIP LOCKED` ; notification Redis facultative ; auto-générations aussi via create_task | Réutiliser le moteur existant ; tester les interruptions et éviter les longs traitements dans les requêtes |
| Timeouts | Client ordinaire 30 s, scraping 120 s, chat SSE 300 s ; navigateur passe actuellement par rewrite Next | Appels directs Render configurables pour fichiers/SSE/traitements longs ; CORS et CSRF adaptés aux bearer tokens |
| LLM | Plusieurs providers existants, configuration locale .env modifiable depuis l'UI | OpenAI par défaut dans les exemples cloud ; garder les autres providers ; ne pas dépendre d'un fichier .env persistant sur Render |
| Render | Blueprint actuel déploie API et web, SQLite sur disque ; contexte Docker racine incompatible avec COPY des requirements API | Un seul service API, contexte apps/api, port PORT, migrations avant démarrage |
| Docker local | Redis et volumes SQLite/uploads, noms de conteneurs fixes | Compose cloud/local PostgreSQL isolé, sans toucher aux autres projets |
| Health | live/ready/diagnostic présents ; backend diagnostic renvoie littéralement sqlite | Corriger diagnostic et maintenir health minimal public |
| CI | Python 3.11, tests/couverture 45 %, audit dépendances, migrations SQLite, frontend et E2E | Ajouter intégration PostgreSQL sans retirer la couverture existante |

Git initial : propre, branche principale `main`, `origin` sur `megapoulpe/OpenTutor`,
pas de remote `upstream`. Branche de travail créée : `feat/vercel-render-supabase`.
Aucune configuration globale Git ni remote n'est modifié.

## Architecture retenue

- SQLAlchemy et Alembic restent l'unique accès applicatif aux données. PostgreSQL
  via connexion directe ou pooler **session** 5432, adapté à une API persistante.
  Le mode transaction 6543 n'est pas le mode conseillé ; il doit être explicitement
  géré/testé ou rejeté clairement pour éviter les prepared statements incompatibles.
- Les tables applicatives ne sont pas accessibles au navigateur par la Data API.
  RLS et révocation des rôles anon/authenticated protègent le schéma exposé.
  L'API vérifie toujours le propriétaire ; un jeton Supabase n'est pas une autorisation globale.
- Supabase Auth authentifie email/mot de passe et renouvelle les sessions.
  Le backend valide l'identité avec Supabase Auth et associe `sub` au `User.id`
  existant. Aucun rattachement automatique d'un ancien compte par email.
  Les inscriptions publiques sont désactivées dans Supabase. Comptes initiaux
  créés dans le dashboard. Les métadonnées éditables ne servent pas à autoriser.
- Le bucket documents reste privé. Objets organisés par utilisateur/cours/UUID.
  La clé de service reste serveur. Le navigateur passe par un endpoint contrôlant
  la propriété du document ; pas d'URL publique. HTTPX déjà présent suffit aux
  appels Auth/Storage, sans deuxième SDK ou couche d'orchestration.
- Le chemin local d'extraction ne devient jamais l'identifiant durable du document.
  Nettoyage dans finally, y compris annulation et erreurs. Upload distant et commit SQL
  ne sont pas atomiques : compensation et comportement de reprise documentés/testés.
- Réutiliser le moteur de tâches SQL existant et son polling, sans Redis obligatoire,
  Celery ou worker supplémentaire. Une seule instance API au démarrage ; ne pas
  annoncer une reprise durable pour des tâches qui n'ont pas été rendues persistantes.
- Côté navigateur, URL Render explicite en cloud, URL relative possible en local.
  Les bearer tokens ne nécessitent pas de cookie intersite pour autoriser les appels.
  Les requêtes utilisant une authentification ambiante par cookie restent protégées
  par CSRF. Vérifier spécialement previews PDF, scraping et chat SSE.
- Les secrets et la configuration de production sont gérés par Render ; aucune
  modification du provider depuis l'UI ne doit prétendre persister dans un disque éphémère.

## Tests et critères d'acceptation

Tests ciblés : normalisation URL/TLS/pool, création PostgreSQL vierge et idempotence,
contraintes/FK, transactions indépendantes, identité invalide et utilisateur inactif,
accès croisé entre deux comptes, upload/download/delete Storage (transport simulé),
limites taille/type, nettoyage temporaire, erreurs Storage et SQL, doublons par cours,
expiration session et appels frontend authentifiés. Régression des tests pédagogiques.
Intégration PostgreSQL réelle via Docker si disponible et job CI dédié ; tests cloud
avec identifiants explicitement fournis uniquement. Aucun appel LLM payant sans accord.
Build Next, lint, Vitest, pytest et build Docker : résultats séparés des contrôles non exécutés.
Parcours manuel final : importer PDF, extraire, cours, notes/flashcards/quiz, réponses,
correction, rechargement, téléchargement, suppression et isolation entre deux comptes.

## Environnement constaté pendant l'audit

Node 20.12.0, npm 10.5.0. Pas de `apps/web/node_modules` ni `.venv`.
`uv ... python find --offline` ne trouve pas Python 3.11.
`docker version` ne trouve pas le daemon Docker Desktop. Aucune ressource cloud
n'a été inspectée ou modifiée et aucun test applicatif n'est encore exécuté.

## Livrables

Adaptations incrémentales, tests ciblés et PostgreSQL CI, exemples d'environnement
sans secret, Blueprint Render, configuration Vercel/Compose, `DEPLOYMENT.md` avec
procédure complète, limites réelles et stratégie de transfert SQLite séparée et non exécutée.
Commits locaux logiques uniquement. L'absence de secrets cloud ne bloque pas les tests simulés.

## Références consultées

- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/auth/jwts
- https://supabase.com/docs/guides/storage/security/access-control
- https://vercel.com/docs/routing/rewrites
- https://render.com/docs/web-services

Le changelog markdown Supabase n'a pas pu être lu par le navigateur disponible ;
la vérification des changements pertinents reste à compléter avant usage cloud.
