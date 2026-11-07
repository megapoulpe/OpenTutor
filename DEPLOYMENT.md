# Déployer OpenTutor : Vercel + Render + Supabase

L'application conserve Next.js (`apps/web`), FastAPI (`apps/api`), SQLAlchemy et
les fonctions pédagogiques existantes. Supabase fournit PostgreSQL, Auth et un
bucket privé ; le navigateur parle à FastAPI, pas à la Data API des tables.

**Aucun service cloud n'a été créé ou déployé pendant cette adaptation.**
Les validations cloud et LLM réelles nécessitent vos paramètres et votre accord.
Utiliser un projet Supabase dédié à OpenTutor.

## 1. Créer et configurer Supabase

1. Créer un projet, choisir sa région, conserver son mot de passe PostgreSQL dans
   un gestionnaire de secrets. Ne jamais le committer.
2. Dans **Connect**, copier l'URL **Session pooler**, port **5432**. L'API Render
   est persistante ; le pooler session convient aussi aux réseaux IPv4. Ne pas
   déduire le nom du pooler depuis la région.
3. Préfixer l'URL par `postgresql+psycopg://` (les préfixes `postgresql://` et
   `postgres://` sont aussi normalisés). Encoder les caractères du mot de passe
   dans l'URL. Utiliser le propriétaire des tables pour l'API : le backend assure
   l'autorisation, les tables sont fermées aux rôles navigateur.
4. Télécharger le certificat CA indiqué dans Database Settings pour la connexion
   choisie ; configurer `DATABASE_SSL_ROOT_CERT` avec son chemin. Avec un pooler
   utilisant une CA publique, fournir un bundle CA approprié au certificat du
   pooler. Conserver `DATABASE_SSL_MODE=verify-full` ; ne pas désactiver TLS sur
   une connexion cloud pour contourner une erreur de certificat.
5. Copier Project URL, une clé **publishable** (ou l'ancienne clé anon) et la clé
   **service_role** serveur. Cette dernière ne doit jamais être dans Vercel ni
   dans une variable `NEXT_PUBLIC_*`.

Le mode transaction 6543 est facultatif : il nécessite
`DATABASE_POOL_MODE=transaction`, désactive la préparation automatique psycopg et
utilise NullPool. Préférer le mode session ; le pooler hébergé n'a pas été testé
pendant cette session. Connexions directes possibles si le réseau atteint l'hôte.
Limiter le pool par instance : taille 5, débordement 5 par défaut.

## 2. Authentification familiale

1. Dans Supabase Auth, activer email/mot de passe et **désactiver les inscriptions
   publiques** ainsi que les connexions anonymes. La route register d'OpenTutor
   est également fermée en mode Supabase.
2. Créer les comptes dans Auth > Users avec un mot de passe initial fort et un
   email confirmé. Ne pas utiliser le parcours d'invitation par lien : cette
   adaptation fournit la connexion par mot de passe, sans page d'acceptation
   d'invitation ni récupération de mot de passe. L'administrateur gère les mots
   de passe dans Supabase pour cette première instance privée.
3. Configurer `AUTH_ENABLED=true`, `AUTH_PROVIDER=supabase`,
   `DEPLOYMENT_MODE=multi_user`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`.
4. L'API vérifie chaque identité auprès de `/auth/v1/user` et crée le `User`
   applicatif avec le même UUID. Elle ne fusionne jamais deux comptes par email.
   Un ancien compte avec le même email demande une migration d'identité explicite.

Les jetons sont conservés dans sessionStorage pour l'onglet, renouvelés toutes
les minutes et après rechargement. La déconnexion appelle Supabase pour cette
session et efface les jetons locaux. Comme pour tout JWT Supabase, une révocation
ne garantit pas l'invalidation immédiate d'un access token déjà émis ; conserver
une durée d'accès courte adaptée à l'usage. Pour un blocage applicatif immédiat,
désactiver le `User.is_active` concerné avec un administrateur de la base.
Les profils locaux de préférences sont séparés par identité. Les relations
utilisateur/cours et les contrôles d'accès restent côté API.

## 3. Bucket Storage privé

1. Créer un bucket nommé `documents` avec **Public désactivé**.
2. Régler sa taille maximale sur la même valeur que `MAX_UPLOAD_SIZE_MB` (50 par
   défaut), et ses types MIME autorisés selon les formats réellement utilisés.
3. Ne créer aucune policy autorisant anon/authenticated à lire ce bucket : le
   backend utilise la clé service_role après contrôle de propriété du document.
4. Configurer `STORAGE_BACKEND=supabase`, `SUPABASE_STORAGE_BUCKET=documents`,
   `SUPABASE_SERVICE_ROLE_KEY` et `APP_RUN_ACTIVITY_ENGINE=true`.

Le démarrage vérifie que le bucket existe et est privé. Les objets sont rangés
par UUID utilisateur/cours/document. Il n'y a ni objet public ni URL publique.
`GET /api/content/files/{job_id}` télécharge via le backend authentifié et envoie
`Cache-Control: private, no-store`. Le compte d'un autre élève reçoit 404.
`ALLOWED_UPLOAD_EXTENSIONS` limite les extensions, `MAX_UPLOAD_SIZE_MB` la taille
de l'upload ; la liste ne peut pas ajouter un nouveau parseur par configuration.

Les uploads cloud sont enregistrés avec une tâche SQL dans la base avant de
répondre ; le frontend utilise son suivi d'ingestion existant. L'extraction
télécharge le document dans un TemporaryDirectory, nettoyé même en cas d'erreur
ou d'annulation. Les imports Canvas utilisent aussi Storage et nettoient leur
copie locale. Une extraction échouée garde sa source privée liée au job pour
diagnostic/suppression ; elle n'est pas considérée comme un document prêt.

## 4. Variables à préparer

Toutes les valeurs ci-dessous vont sur le **backend uniquement**, sauf la dernière.

| Variable | Valeur / action manuelle |
|---|---|
| `DATABASE_URL` | URL Session pooler du projet, mot de passe encodé |
| `DATABASE_SSL_MODE` | `verify-full` en cloud, `disable` uniquement en local |
| `DATABASE_SSL_ROOT_CERT` | Chemin du certificat CA, Render `/etc/secrets/supabase-ca.crt` |
| `DATABASE_POOL_MODE` | `session` |
| `SUPABASE_URL` | `https://VOTRE_PROJET.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Clé publique du projet utilisée par le proxy Auth serveur |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé service_role, exclusivement serveur |
| `SUPABASE_STORAGE_BUCKET` | `documents` |
| `AUTH_ENABLED` / `AUTH_PROVIDER` | `true` / `supabase` |
| `DEPLOYMENT_MODE` | `multi_user` |
| `STORAGE_BACKEND` | `supabase` |
| `JWT_SECRET_KEY` | Aléatoire, au moins 32 caractères ; sert notamment à CSRF, pas à signer les JWT Supabase |
| `ENCRYPTION_KEY` | Clé Fernet pour les credentials d'intégration existants |
| `LLM_PROVIDER` / `LLM_MODEL` | `openai` / `gpt-4o-mini`, ou autre provider existant |
| `OPENAI_API_KEY` | Votre clé OpenAI ; aucune vraie clé n'est fournie dans les exemples |
| `LLM_REQUIRED` | `true` en production, afin de refuser le fallback simulé |
| `CORS_ORIGINS` | Origines exactes Vercel, séparées par virgules, sans chemin ni slash final |
| `APP_AUTO_CREATE_TABLES` | `false` : migrations avant démarrage |
| `APP_AUTO_SEED_SYSTEM` / `APP_AUTO_SEED_DEMO` | `true` / `false` |
| `APP_RUN_ACTIVITY_ENGINE` / `ACTIVITY_USE_REDIS_NOTIFY` | `true` / `false` |
| `APP_RUN_SCHEDULER` | `false` initialement, activable pour les fonctions planifiées |
| `UPLOAD_DIR` | `/tmp/opentutor-uploads` sur Render, uniquement temporaire |
| `CODE_SANDBOX_BACKEND` | `disabled` sur Render sans environnement conteneur isolé |
| `MAX_UPLOAD_SIZE_MB` | `50` par défaut, à aligner avec le bucket |
| `NEXT_PUBLIC_API_URL` | **Vercel uniquement** : `https://VOTRE_API.onrender.com/api` |

Générer localement les deux clés internes, les copier dans le gestionnaire de
secrets approprié ; ces commandes affichent de nouvelles valeurs à conserver :

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

En production, la modification des providers depuis l'UI est refusée. Régler les
providers et secrets dans Render puis redémarrer ; un fichier `.env` local à un
conteneur Render ne fournirait aucune persistance fiable. Les autres providers
et leurs variables existantes restent disponibles.

## 5. Développement Windows / PowerShell

Prérequis : Python 3.11+, Node **22.12+**, npm et Docker Desktop si l'on utilise
Compose. Les dépendances du frontend actuel ne supportent pas Node 20.12.

Depuis la racine, créer les fichiers ignorés et les éditer :

```powershell
Copy-Item .env.example .env
Copy-Item apps/web/.env.example apps/web/.env.local
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r apps/api/requirements-cloud.txt
```

Dans `.env`, remplacer l'URL SQLite de l'exemple par une URL PostgreSQL et régler
`DATABASE_SSL_MODE`, Auth et Storage comme indiqué ci-dessus. Pour les fonctions
optionnelles avancées, installer `requirements-full.txt` au lieu de cloud.

Deux façons de lancer PostgreSQL : utiliser le projet Supabase de développement,
ou démarrer uniquement la base locale dédiée à ce projet :

```powershell
# Dans .env : LOCAL_POSTGRES_PASSWORD = un mot de passe alphanumérique aléatoire
docker compose -f docker-compose.cloud.yml up -d postgres
```

Pour cette base locale, mettre dans `.env` :
`DATABASE_URL=postgresql+psycopg://opentutor:VOTRE_MOT_DE_PASSE@127.0.0.1:55432/opentutor`
et `DATABASE_SSL_MODE=disable`, `ENVIRONMENT=development`.
Ne pas utiliser le mot de passe d'un autre projet. Le port est configurable par
`LOCAL_POSTGRES_PORT`. Supabase Auth/Storage peuvent être hébergés même si SQL est local.

Terminal API (le module choisit la boucle asyncio compatible Windows/psycopg) :

```powershell
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m services.server
```

Terminal frontend, depuis la racine :

```powershell
Set-Location apps/web
npm ci
npm run dev
```

Ouvrir `http://localhost:3001`. La variable frontend locale pointe vers
`http://127.0.0.1:8000/api`. Pour lancer aussi l'API dans Docker :

```powershell
docker compose -f docker-compose.cloud.yml up --build -d api
# Arrêt limité à CE projet, sans suppression de volume :
docker compose -f docker-compose.cloud.yml stop
```

Les lancements natifs historiques et SQLite restent disponibles pour compatibilité
upstream. La configuration PostgreSQL décrite ici n'utilise aucune base SQLite.

## 6. Initialisation et mises à jour SQL

Sur une base entièrement vierge, Alembic applique le snapshot figé
`alembic/postgres-baseline.sql`, marque la révision historique correspondante,
puis poursuit les nouvelles migrations. Le snapshot évite les révisions anciennes
qui supposaient déjà présentes les tables de base. Les bases déjà versionnées
conservent leur historique ; aucune ancienne révision n'a été réécrite.

La révision `20261107_0027` active RLS sur les 33 tables applicatives et retire les
droits de anon/authenticated. Aucun accès Data API navigateur n'est ajouté.
Ne pas lancer create_all puis stamp manuellement : cela contournerait les contrôles.
Une base partiellement initialisée demande un diagnostic avant migration.

La commande idempotente habituelle reste : `python -m alembic upgrade head` depuis
`apps/api`. Sauvegarder avant une mise à jour de données réelles. Aucun downgrade
ou transfert SQLite n'est lancé automatiquement.

## 7. Render

1. Après validation du code et autorisation de push, connecter votre fork à Render.
2. Créer le service API à partir du Blueprint `render.yaml`, ou un Web Service Docker
   avec Dockerfile `apps/api/Dockerfile` et contexte `apps/api`.
3. Ajouter les paramètres et secrets du tableau. Ajouter le certificat dans les
   **Secret Files**, nom `supabase-ca.crt` ; son chemin correspond au Blueprint.
4. Ne pas ajouter de disque persistant. Garder **une instance** API au démarrage.
   Le moteur de tâches SQL est exécuté dans ce service ; Redis n'est pas requis.
5. Le CMD exécute Alembic, puis démarre Uvicorn sur `0.0.0.0:$PORT` (8000 par défaut).
   Une migration ou un contrôle du bucket échoué empêche le démarrage applicatif.
6. Utiliser `/api/health/live` pour la sonde Render. Vérifier aussi
   `/api/health/ready` et `/api/health` pour la base, le schéma et le LLM.
7. Lire les logs de migration/démarrage et relever l'URL HTTPS de l'API.

Ne pas activer les déploiements automatiques tant que le premier déploiement
n'est pas validé. Les builds Docker et le fonctionnement Render réels restent à
vérifier sur votre compte ; Docker Desktop n'était pas disponible pendant les tests.

## 8. Vercel et liaison des services

1. Importer votre fork ; sélectionner **Root Directory `apps/web`** et le framework
   Next.js. Choisir Node 22, installation `npm ci`, build `npm run build`.
2. Configurer `NEXT_PUBLIC_API_URL=https://VOTRE_API.onrender.com/api` en Production
   et, si nécessaire, une API de test distincte pour Preview. Cette variable est
   intégrée au build : un changement nécessite un nouveau build Vercel.
3. Les appels navigateur utilisent cette adresse directement, y compris upload,
   téléchargement et chat SSE. Les rewrites Next existants restent une solution
   locale relative lorsque cette variable est absente. Aucun backend Python ne
   tourne en fonction Vercel.
4. Régler `CORS_ORIGINS` dans Render avec les origines Vercel exactes puis redémarrer.
   Ajouter seulement les previews que vous autorisez ; aucun wildcard en production.
5. Vérifier connexion, déconnexion, rechargement, requêtes OPTIONS et SSE depuis
   le domaine Vercel. Les bearer tokens sont explicites ; la protection CSRF reste
   applicable aux requêtes utilisant des credentials ambiants par cookie.

## 9. Tâches, suppression et limites

Les imports PDF/documents cloud réutilisent AgentTask : réponse courte après
persistance, puis extraction/génération en arrière-plan, polling frontend existant.
Une tâche d'import est limitée à 900 s ; une revendication abandonnée peut être
reprise après 1 200 s. Les effets de dispatch déjà enregistrés ne sont pas rejoués
lors d'une reprise pendant l'embedding. Les générations de quiz/flashcards ont
déjà des gardes de déduplication par cours. Les appels LLM réels restent à valider.

La suppression d'un document (`DELETE /api/content/files/{job_id}`) ou d'un cours
enregistre le nettoyage Storage dans la même transaction SQL. La suppression
distante est ensuite retentée par le moteur ; elle est idempotente. Sur échec
définitif, inspecter les tâches `delete_document_objects` et les relancer après
correction. Le document devient immédiatement inaccessible via son endpoint
après commit, même si sa destruction physique attend le traitement de la tâche.
Les résultats pédagogiques déjà générés sont conservés selon les FK existantes
(référence de contenu remise à NULL ou cascade selon le modèle) ; la suppression
ne doit pas effacer arbitrairement les résultats d'autres documents du cours.

Les imports Canvas/navigateur et certains traitements optionnels upstream restent
des tâches en mémoire : une interruption peut nécessiter de relancer l'import.
Leurs fichiers traités sont persistés dans Storage. Les flux chat SSE ont une
limite configurable `SSE_TIMEOUT_SECONDS` de 300 s et ne passent pas par le proxy
Vercel en configuration cloud. Ne pas multiplier les workers sans valider le
comportement du scheduler et les reprises. Le sandbox Python exige une isolation
conteneur que Render ne fournit pas ici : il est désactivé, sans fallback process
non isolé. Les fonctions optionnelles qui dépendent d'un navigateur interactif,
d'un état local de cookies ou d'un sandbox nécessitent un environnement adapté.

## 10. Validation et diagnostic

Résultats exécutés le 7 novembre 2026 :

| Contrôle | Résultat |
|---|---|
| Suite backend complète | 1 224 réussis, 14 ignorés, couverture 52,58 % (seuil 45 %) |
| PostgreSQL 16 réel, suite dédiée | 4 réussis, dont PDF et erreurs/annulation |
| Frontend Vitest | 241 tests réussis, 43 fichiers |
| Frontend lint et TypeScript | Réussis |
| Build Next.js webpack | Réussi |
| Démarrage API + HTTP health sur PostgreSQL | `status=ok`, `schema=ready`, `migration_required=false` |
| Blueprint/contexte Render et YAML Compose | Vérifiés localement |
| Build d'image Docker | Non exécuté : daemon Docker Desktop indisponible |
| Supabase Auth/Storage hébergés, pooler et TLS cloud | Non exécutés : ressources/identifiants non fournis |
| Générations OpenAI réelles et parcours navigateur cloud | Non exécutés : clé/accès et validation manuelle nécessaires |

Les premiers échecs de tests ont été corrigés : téléchargement initial du
tokenizer via le magasin de certificats local, fixture auth et dépendance cloud
facultative. Aucun test échoué ne reste dans les suites ci-dessus.

Commandes depuis la racine (adapter le venv et utiliser une base dédiée `_test`) :

```powershell
.venv\Scripts\python.exe -m pytest tests -q
$env:POSTGRES_TEST_DATABASE_URL='postgresql://UTILISATEUR:MOT_DE_PASSE@127.0.0.1:55432/opentutor_test'
.venv\Scripts\python.exe -m pytest tests/test_postgres_integration.py -q -o addopts=
Set-Location apps/web
npm run test:run
npm run lint
npm run build
```

Les tests PostgreSQL utilisent une vraie base : migrations répétées, RLS,
transactions, JSONB/UUID, recherche et isolation, puis upload d'un vrai PDF,
extraction, persistance/rechargement, téléchargement et suppression. Le transport
Storage/Auth est simulé dans les tests sans identifiants ; cela ne valide pas un
bucket cloud réel. Les fonctions pédagogiques sont couvertes par la suite existante.

Après déploiement : avec deux comptes, importer un PDF, vérifier extraction et
cours, générer notes/flashcards/quiz, répondre/corriger, retrouver les résultats,
recharger puis télécharger et supprimer le document. L'autre compte ne doit rien
voir ni pouvoir télécharger avec un UUID connu. Vérifier que la suppression
physique Storage termine et qu'aucun secret n'est présent dans le bundle frontend.

| Symptôme | Vérification |
|---|---|
| Erreur TLS PostgreSQL | Hôte exact et CA du pooler/de la base ; chemin du certificat lisible |
| Connexion PostgreSQL refusée | URL session 5432, mot de passe encodé, réseau IPv4/IPv6, projet actif |
| 401 | Compte confirmé, bon projet Supabase, token utilisateur, session expirée ; se reconnecter |
| 409 au premier login | Ancien compte avec email identique : migration d'identité manuelle nécessaire |
| API ne démarre pas, bucket | Bucket existant et privé, bonne clé service_role, pas de clé publishable pour Storage |
| 403/CORS | Origine navigateur exacte dans Render, adresse API avec `/api`, headers Authorization autorisés |
| Jobs bloqués | `APP_RUN_ACTIVITY_ENGINE=true`, logs et statut AgentTask, attente de reprise d'une ancienne revendication |
| 503 LLM | Clé/projet/quota/modèle du provider ; `LLM_REQUIRED=true` ne simule pas de réponse |
| Tokenizer au premier import | Le Dockerfile précharge le cache tiktoken ; en local autoriser son téléchargement initial avec des certificats valides |
| Modification LLM refusée | Configurer les variables serveur Render, pas le fichier .env du conteneur |

## 11. Migration de données SQLite : stratégie uniquement

Ne pas remplacer l'URL d'une base existante et supposer que les données sont transférées.
Prévoir une copie de sauvegarde cohérente SQLite + uploads, vérifier les comptes
et définir explicitement la correspondance anciens UUID / identités Supabase.
Créer une base PostgreSQL vierge, transférer les tables dans l'ordre des FK en
conservant UUID/JSON/timestamps, copier les fichiers privés et remplacer leurs
références seulement après upload réussi. Comparer comptes de lignes, FK et
échantillons de résultats, puis tester les parcours avant bascule. Conserver la
source intacte pour retour arrière. Aucun script de transfert ni copie n'a été exécuté.

## 12. Mise à jour après un commit

Exécuter tests et build, relire les migrations et sauvegarder les données. Après
votre validation, pousser la branche puis déployer l'API ; Alembic est exécuté par
le CMD avant le serveur. Vérifier ready, migrations et tâches, puis déployer le
frontend. Les tâches durables utilisent la même base après redémarrage.
Un retour à une ancienne image ne supprime pas les nouvelles colonnes/données :
préférer les migrations compatibles et ne jamais lancer un downgrade destructeur
automatiquement. Aucun push, merge ou déploiement n'est inclus dans cette session.

Références : [connexion Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres),
[Storage privé](https://supabase.com/docs/guides/storage/security/access-control),
[TLS PostgreSQL](https://www.postgresql.org/docs/current/libpq-ssl.html),
[Render Web Services](https://render.com/docs/web-services),
[rewrites Vercel](https://vercel.com/docs/routing/rewrites).
