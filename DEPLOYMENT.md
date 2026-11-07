# Déployer OpenTutor

Frontend Next.js sur Vercel ; API FastAPI sur Render ; PostgreSQL, Auth et Storage sur Supabase.
Une seule instance API contient aussi le moteur de tâches SQL existant. Aucun Redis ni worker séparé.

## 1. Préparer Supabase

- Créer un projet **dédié à OpenTutor** et conserver son mot de passe de base de données.
- Dans Data API, désactiver **Enable Data API** : FastAPI utilise SQLAlchemy, pas cette API.
- Dans Auth, activer email/mot de passe et désactiver inscriptions publiques et comptes anonymes.
- Créer les premiers utilisateurs avec email confirmé et mot de passe dans Auth > Users.
- Créer le bucket **documents**, privé, limité à 50 Mo ; ne pas ajouter de policy publique.
- Copier l'URL **Session pooler, port 5432**, depuis Connect. Encoder les caractères spéciaux du mot de passe.

Pas de rôle SQL supplémentaire à créer pour cette première version. Le compte de connexion existant
reste privilégié : réserver ce projet à OpenTutor et protéger ses secrets. RLS, révocations SQL et
contrôles de propriété FastAPI restent actifs ; ne pas réactiver la Data API sans revue de sécurité.
Supprimer un utilisateur dans Auth seul ne supprime pas ses documents/données applicatives.
La suppression complète des comptes et les parcours invitation/récupération seront traités séparément.

## 2. Déployer Render

Importer votre fork dans Render avec le Blueprint `render.yaml`, après autorisation de push/déploiement.
Il configure le Dockerfile et son contexte `apps/api`, sans disque persistant.
Renseigner uniquement ces **six valeurs** côté serveur :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | URL Session pooler Supabase, port 5432 ; préfixe `postgresql://` accepté |
| `SUPABASE_URL` | `https://VOTRE_PROJET.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Clé publishable du projet, ou ancienne clé anon |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé service_role, exclusivement serveur |
| `OPENAI_API_KEY` | Votre clé OpenAI, exclusivement serveur |
| `CORS_ORIGINS` | Origine Vercel exacte, sans chemin ni slash final ; virgules si plusieurs |

Render génère et conserve automatiquement `JWT_SECRET_KEY` et `ENCRYPTION_KEY`.
Ne pas les régénérer après utilisation : des tokens d'intégration sont chiffrés avec cette dernière.
Les valeurs de production sont automatiques : Supabase Auth/Storage, moteur SQL actif, démo désactivée,
OpenAI `gpt-4o-mini` avec erreurs explicites si indisponible, et fichiers d'extraction temporaires.
Les autres providers upstream restent configurables avec leurs variables existantes si nécessaire.

Le lanceur applique Alembic avant de démarrer l'API sur `0.0.0.0:$PORT`.
Le schéma initial figé est un détail interne : aucun SQL, snapshot ou stamp à manipuler au déploiement.
Le démarrage échoue si les migrations échouent ou si le bucket n'existe pas ou est public.
Sonde Render : `/api/health/live`. Vérifier également `/api/health/ready` après configuration du LLM.

## 3. Déployer Vercel

- Importer le même fork, framework Next.js, **Root Directory `apps/web`**, Node 22.12 ou supérieur.
- Installation `npm ci`, build `npm run build`, paramètres Next.js standard.
- Ajouter **`NEXT_PUBLIC_API_URL=https://VOTRE_API.onrender.com/api`**, puis déployer.
- Reporter l'origine Vercel dans `CORS_ORIGINS` sur Render ; redémarrer l'API si elle change.
- Les appels restent **directs du navigateur vers Render**, y compris uploads, téléchargements et SSE.
- Ne mettre aucune clé OpenAI/service_role, aucun mot de passe SQL dans Vercel.

## 4. Vérifier avant utilisation

Se connecter avec deux comptes distincts. Importer un PDF, vérifier extraction et cours, générer fiche,
flashcards et quiz, répondre/corriger, recharger et retrouver données/documents. Tester aussi un gros PDF,
le téléchargement et le chat SSE. Un autre compte doit recevoir 404 pour un document dont il connaît l'UUID.
Supprimer un document et vérifier sa disparition dans Storage après traitement de la tâche de nettoyage.
Les nettoyages échoués sont retentés par le moteur existant ; consulter ses tâches et les logs Render.

## 5. Développement local Windows

Python 3.11+, Node 22.12+. Utiliser un projet Supabase de développement ou PostgreSQL local indépendant.
Depuis la racine, créer `.venv`, installer `apps/api/requirements-cloud.txt` (ou full pour les intégrations),
copier `.env.example` vers `.env` et `apps/web/.env.example` vers `apps/web/.env.local`.
Mettre PostgreSQL dans `DATABASE_URL` ; garder `ENVIRONMENT=development` pour le développement local.
La configuration locale conserve les réglages upstream ; les défauts cloud s'activent en production.
Pour PostgreSQL Docker local : définir `LOCAL_POSTGRES_PASSWORD` dans `.env`, puis :

```powershell
docker compose -f docker-compose.cloud.yml up -d postgres
# Dans .env : DATABASE_URL=postgresql://opentutor:MOT_DE_PASSE@127.0.0.1:55432/opentutor
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m services.server
# Autre terminal, depuis la racine :
Set-Location apps/web
npm ci
npm run dev
```

L'API applique aussi ses migrations PostgreSQL en local. SQLite upstream reste disponible sans transfert.
Pour utiliser Auth/Storage Supabase en développement, activer leurs réglages dans `.env.example`.

## 6. Diagnostic et mises à jour

- **TLS SQL** : les connexions distantes imposent `verify-full` avec le bundle CA public déjà fourni par HTTPX/certifi.
  Si votre endpoint exige une CA Supabase spécifique, indiquer son chemin via `sslrootcert` dans `DATABASE_URL`.
  Ne jamais contourner une erreur distante avec `sslmode=require` ou `disable` ; le code impose la vérification.
- **401** : vérifier compte confirmé, bon projet et session ; **CORS** : vérifier origine exacte et URL API avec `/api`.
- **Bucket** : vérifier nom `documents`, privé et clé service_role ; **503 LLM** : clé, quota ou modèle du provider.
- **Import interrompu** : consulter les tâches SQL ; les imports Canvas optionnels en mémoire peuvent nécessiter une relance.
- **Sandbox** : désactivé sur Render faute d'isolation conteneur ; aucun fallback de code élève non isolé.
- Avant mise à jour : tests, build et sauvegarde. Après votre accord, pousser puis déployer API et frontend.
  Alembic est automatique ; ne lancer aucun downgrade destructeur. Vérifier ready et le parcours PDF après mise à jour.
- Tests : `python -m pytest tests -q` ; PostgreSQL dédié `_test` via `POSTGRES_TEST_DATABASE_URL` et
  `python -m pytest tests/test_postgres_integration.py -q -o addopts=` ; frontend : test:run, lint, build.

Les vérifications locales ne remplacent pas la validation Auth/Storage/TLS/LLM sur votre projet hébergé.
