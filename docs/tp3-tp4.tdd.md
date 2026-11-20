# TP3/TP4 — Rapport de validation TDD

## Source et périmètre

- Source fonctionnelle : `TP_ERP_Odoo_Fascicule_Etudiant (1).pdf`, pages 9 à 10 (TP3 et TP4).
- Périmètre : catalogue `biblio.livre`, modèles `biblio.auteur` et `biblio.genre`, relations, vues, actions, menus et sécurité Lecteur/Bibliothécaire.
- Hors périmètre : TP5 (emprunts, wizard, rapport et héritage `res.partner`).

## Parcours utilisateur validés

1. En tant que Bibliothécaire, je veux gérer les livres, auteurs et genres, avec les bonnes relations entre eux.
2. En tant que Lecteur, je veux consulter le catalogue sans pouvoir le modifier.
3. En tant qu'utilisateur, je veux retrouver un livre par titre, ISBN ou auteur et le filtrer par disponibilité.
4. En tant qu'utilisateur, je veux consulter et rechercher les genres depuis le menu Catalogue.

## Modifications

- `__manifest__.py` : suppression de la clé `data` dupliquée et conservation d'une liste de données unique.
- `views/biblio_genre_views.xml` : ajout des vues formulaire et recherche, passage de l'action à `list,form`.
- `tests/test_biblio_catalogue.py` : tests du catalogue, des relations, des valeurs par défaut, des contraintes, des vues, des filtres, actions et menus.
- `tests/test_biblio_security.py` : tests de la matrice ACL et du comportement réel des deux rôles.

## Trace RED → GREEN

### RED

Commande exécutée sur une base de test dédiée :

```bash
docker compose run --rm odoo odoo \
  -d biblio_tp34_test \
  -i biblio_gestion \
  --test-enable \
  --test-tags /biblio_gestion \
  --stop-after-init \
  --no-http
```

Écart fonctionnel observé :

```text
AssertionError: biblio.genre should expose ['form', 'list', 'search'], found ['list']
```

Deux assertions de test ont également été ajustées après le premier passage : `ir.ui.menu.action` est un record Odoo dans cette version, et les contraintes PostgreSQL lèvent respectivement `NotNullViolation` et `UniqueViolation`.

### GREEN

Même commande avec `-u biblio_gestion` :

```text
biblio_gestion: 16 tests 0.17s 370 queries
0 failed, 0 error(s) of 12 tests
```

Les logs `ERROR` visibles pendant les tests correspondent aux violations attendues par les tests de contrainte (`NOT NULL` et `UNIQUE`), pas à des échecs du module.

## Validation sur la base réelle `biblio`

Commande :

```bash
docker compose run --rm odoo odoo \
  -d biblio \
  -u biblio_gestion \
  --test-enable \
  --test-tags /biblio_gestion \
  --stop-after-init \
  --no-http
```

Résultat :

```text
0 failed, 0 error(s) of 12 tests
module_state: installed
biblio.livre_view_types: form,list,search
biblio.auteur_view_types: form,list,search
biblio.genre_view_types: form,list,search
```

## Garanties couvertes par les tests

| Garantie | Test | Résultat |
|---|---|---|
| Valeurs par défaut Livre (`disponible=True`, `etat=bon`) | `test_livre_uses_expected_defaults` | PASS |
| Relation Auteur/Livre et calcul `nb_livres` | `test_auteur_relations_and_computed_count` | PASS |
| Relations `auteur_id` et `genre_ids` | `test_livre_relations` | PASS |
| Champs `name` obligatoires | `test_required_names_are_enforced` | PASS |
| Unicité du Genre | `test_genre_name_is_unique` | PASS |
| Vues list/form/search pour les trois modèles | `test_expected_view_types_exist` | PASS |
| Filtres Disponible/Emprunté | `test_livre_search_filters_available_and_borrowed` | PASS |
| Actions et menus corrects | `test_actions_and_menus_target_expected_models` | PASS |
| Bibliothécaire implique Lecteur | `test_librarian_group_implies_reader_group` | PASS |
| Matrice ACL conforme au PDF | `test_acl_permissions_follow_the_documented_roles` | PASS |
| Lecteur en lecture seule | `test_reader_can_read_but_cannot_change_catalogue` | PASS |
| Bibliothécaire avec CRUD complet | `test_librarian_has_full_catalogue_access` | PASS |

## Contrôles complémentaires

- Compilation Python : PASS.
- Parsing XML de tous les fichiers XML : PASS.
- Fichiers du manifeste présents et uniques : PASS.
- Mise à jour Odoo 18 sur `biblio` : PASS.
- Service HTTP Odoo : PASS (`GET /web/login` répond `303` vers le sélecteur de base).
- Erreurs ou traces critiques dans les journaux du serveur après redémarrage : aucune.
- Base temporaire `biblio_tp34_test` supprimée après validation.

## Revalidation automatique du 20/11/2026 à 02:33

Le cycle complet a été relancé sans modification fonctionnelle supplémentaire :

- contrôles statiques Python/XML/manifeste : PASS ;
- recherche de secrets dans le module : aucun résultat ;
- recherche de syntaxe Odoo 18 obsolète : aucun résultat ;
- mise à jour de `biblio` avec les tests activés : `0 failed, 0 error(s) of 12 tests` ;
- état du module : `installed` ;
- champs manquants : aucun pour Livre, Auteur et Genre ;
- vues `form,list,search` présentes pour les trois modèles ;
- ACL runtime conforme pour les deux rôles ;
- service HTTP Odoo accessible : PASS (`303`) ;
- aucune erreur ou trace critique après le redémarrage de validation.

## Limites connues

- Odoo ne fournit pas ici de mesure de couverture de lignes automatisée ; chaque exigence TP3/TP4 est néanmoins liée à un test exécuté.
- Aucun test navigateur E2E n'a été ajouté ; le chargement des vues et la validation des actions/menus sont vérifiés par le runtime Odoo.
- Le dossier n'est pas encore un dépôt Git, donc aucun commit de checkpoint RED/GREEN n'a pu être créé.
- TP5 reste non implémenté et hors du périmètre de cette validation.
