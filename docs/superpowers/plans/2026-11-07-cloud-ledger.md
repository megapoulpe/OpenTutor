# Journal d'exécution

- Audit : repository propre, main, origin fork, upstream absent ; branche dédiée.
- Décision utilisateur : Supabase Auth, après présentation JWT local / Supabase.
- Builder check indépendant : nothing important left.
- PostgreSQL : bootstrap figé 33 tables, migrations idempotentes et RLS vérifiés
  sur PostgreSQL 16 local isolé (port 55432, données tmp/postgres-cloud).
- Stockage : HTTPX existant ; bucket privé vérifié au démarrage, références
  durables, extraction temporaire, pipeline/Canvas adaptés, outbox de suppression.
- Auth : validation serveur Supabase, UUID sans fusion email, UI connexion,
  renouvellement, séparation persona et appels directs Render authentifiés.
- Ruling : pilote psycopg dans requirements-cloud et extra cloud plutôt que core,
  pour conserver le verrou Windows natif existant ; installation cloud explicite
  documentée. Risque si oublié : URL PostgreSQL sans pilote installé.
- Ruling : conserver les imports Canvas optionnels en mémoire, documenter leur
  reprise manuelle ; ne pas ajouter un orchestrateur. Risque : relancer un import
  interrompu. Le sandbox isolé n'étant pas disponible sur Render, le désactiver
  plutôt que lancer du code élève sans isolation.
- Vérification initiale : frontend existant 239 tests ; après session auth 241.
  Lint/TypeScript/build Next réussis. Démarrage API réel + health PostgreSQL réussi.
- Suite backend avant corrections d'environnement : 17 échecs ; CA tokenizer,
  fixture auth et placement du pilote corrigés. Puis 1221 pass / 13 skip,
  couverture 52,51 %. Suite complète relancée après corrections de revue.
- Revue indépendante : corriger import tokenizer dans étage Docker runtime après
  COPY, états terminaux ingestion, reprise embedding et saturation du sémaphore.
  Trois tests reproduisent les régressions puis passent ; 54 tests engine/services
  passent. Intégration PostgreSQL finale : 4 tests, dont PDF réel et annulation/
  échec Storage suivis de suppression, réussis. Transport cloud simulé.
- Sans accès cloud : aucune création/déploiement ni vérification Supabase réelle,
  aucun appel LLM payant. Docker Desktop indisponible : build image non exécuté.
- Vérification finale après corrections de revue : 1224 tests backend réussis,
  14 ignorés, couverture 52,58 % ; 4 tests PostgreSQL dédiés réussis. Build Next
  relancé avec succès. Aucun finding de revue important laissé sans correction.
