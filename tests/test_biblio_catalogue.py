from lxml import etree
from psycopg2.errors import NotNullViolation, UniqueViolation

from odoo.tests.common import TransactionCase


class TestBiblioCatalogue(TransactionCase):
    """Regression tests for the TP3/TP4 catalogue requirements."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.genre = cls.env["biblio.genre"].create(
            {
                "name": "Science-fiction",
                "description": "Romans et nouvelles futuristes",
            }
        )
        cls.auteur = cls.env["biblio.auteur"].create(
            {
                "name": "Ursule K. Le Guin",
                "biographie": "Écrivaine américaine",
                "date_naissance": "1929-10-21",
            }
        )
        cls.livre = cls.env["biblio.livre"].create(
            {
                "name": "Les darniers de la Terre",
                "isbn": "9782070409225",
                "date_publication": "1974-01-01",
                "nb_pages": 256,
                "resume": "Un récit post-apocalyptique.",
                "auteur_id": cls.auteur.id,
                "genre_ids": [cls.genre.id],
            }
        )

    def test_livre_uses_expected_defaults(self):
        self.assertTrue(self.livre.disponible)
        self.assertEqual(self.livre.etat, "bon")

    def test_auteur_relations_and_computed_count(self):
        second_livre = self.env["biblio.livre"].create(
            {
                "name": "Le Livre de la Timerie",
                "auteur_id": self.auteur.id,
            }
        )

        self.assertEqual(self.auteur.livre_ids, self.livre | second_livre)
        self.assertEqual(self.auteur.nb_livres, 2)

    def test_livre_relations(self):
        self.assertEqual(self.livre.auteur_id, self.auteur)
        self.assertEqual(self.livre.genre_ids, self.genre)
        self.assertEqual(self.genre.name, "Science-fiction")

    def test_required_names_are_enforced(self):
        with self.assertRaises(NotNullViolation):
            self.env["biblio.auteur"].create({"name": False})

        with self.assertRaises(NotNullViolation):
            self.env["biblio.livre"].create({"name": False})

    def test_genre_name_is_unique(self):
        with self.assertRaises(UniqueViolation):
            self.env["biblio.genre"].create(
                {
                    "name": self.genre.name,
                    "description": "Doublon interdit",
                }
            )
            self.env.flush_all()

    def test_expected_view_types_exist(self):
        expected_views = {
            "biblio.livre": {"list", "form", "search"},
            "biblio.auteur": {"list", "form", "search"},
            "biblio.genre": {"list", "form", "search"},
        }

        for model, expected_types in expected_views.items():
            actual_types = set(
                self.env["ir.ui.view"].search([("model", "=", model)]).mapped("type")
            )
            self.assertTrue(
                expected_types.issubset(actual_types),
                "%s should expose %s, found %s"
                % (model, sorted(expected_types), sorted(actual_types)),
            )

    def test_livre_search_filters_available_and_borrowed(self):
        search_view = self.env["ir.ui.view"].search(
            [
                ("model", "=", "biblio.livre"),
                ("type", "=", "search"),
            ],
            limit=1,
        )
        filters = etree.fromstring(search_view.arch).xpath("//filter")
        domains = {item.get("domain") for item in filters}

        self.assertIn("[('disponible', '=', True)]", domains)
        self.assertIn("[('disponible', '=', False)]", domains)

    def test_actions_and_menus_target_expected_models(self):
        expected_actions = {
            "biblio_livre_action": "biblio.livre",
            "biblio_auteur_action": "biblio.auteur",
            "biblio_genre_action": "biblio.genre",
        }
        for xml_id, model in expected_actions.items():
            action = self.env.ref("biblio_gestion.%s" % xml_id)
            self.assertEqual(action.res_model, model)
            self.assertIn("list", action.view_mode)

        expected_menus = {
            "menu_biblio_livres": "biblio_livre_action",
            "menu_biblio_auteurs": "biblio_auteur_action",
            "menu_biblio_genres": "biblio_genre_action",
        }
        for xml_id, action_xml_id in expected_menus.items():
            menu = self.env.ref("biblio_gestion.%s" % xml_id)
            action = self.env.ref("biblio_gestion.%s" % action_xml_id)
            self.assertEqual(menu.action, action)
