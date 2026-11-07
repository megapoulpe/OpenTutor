# Simplification approuvée — exécution native

Périmètre validé : infrastructure uniquement. Conserver appels directs Render,
Supabase Auth, protections SQL, isolation FastAPI, tâches et migrations existantes.
Reporter suppression des comptes et améliorations de génération. Aucun push/cloud write.

- [x] Tests ciblés puis configuration PostgreSQL unique : pool session 5432,
  petit pool fixe, TLS verify-full et CA standard automatique. Même configuration
  pour API et Alembic. Pas de contournement TLS distant.
- [x] Valeurs de production sûres dans Settings ; Blueprint limité aux secrets,
  CORS et environnement. Clés internes stables générées par Render.
- [x] Un lanceur portable avec migrations automatiques en production ; conserver
  compatibilité upstream locale, moteur de tâches et schéma initial figé.
- [x] DEPLOYMENT.md ~100 lignes, six valeurs manuelles backend et une frontend.
  Aucun rôle SQL supplémentaire : projet dédié, Data API désactivée, protections
  SQL et contrôles API conservés. Le compte SQL existant reste privilégié ; cette
  limite est explicite, aucun privilège supplémentaire n'est ajouté.
- [x] Suites backend, PostgreSQL réel, frontend/lint/build ; image Docker si daemon
  disponible. Revue indépendante, corrections nécessaires, commits locaux.

Décision TLS : bundle CA public fourni par certifi (déjà installé via HTTPX).
Une CA fournisseur nécessaire peut être indiquée dans l'URL PostgreSQL standard
via sslrootcert ; la vérification du serveur reste obligatoire. La compatibilité
avec le projet hébergé reste à confirmer faute d'endpoint/identifiants.

Vérifications et résultats : à compléter pendant l'exécution.
