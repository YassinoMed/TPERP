from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestBiblioSecurity(TransactionCase):
    """Regression tests for TP4 role-based access control."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader_group = cls.env.ref("biblio_gestion.group_biblio_lecteur")
        cls.librarian_group = cls.env.ref("biblio_gestion.group_biblio_bibliothecaire")
        cls.reader = cls.env["res.users"].create(
            {
                "name": "Lecteur de test",
                "login": "biblio_reader_test",
                "groups_id": [Command.set([cls.reader_group.id])],
            }
        )
        cls.librarian = cls.env["res.users"].create(
            {
                "name": "Bibliothécaire de test",
                "login": "biblio_librarian_test",
                "groups_id": [Command.set([cls.librarian_group.id])],
            }
        )

    def test_librarian_group_implies_reader_group(self):
        self.assertIn(self.reader_group, self.librarian_group.implied_ids)
        self.assertIn(self.reader_group, self.reader.groups_id)
        self.assertIn(self.librarian_group, self.librarian.groups_id)

    def test_acl_permissions_follow_the_documented_roles(self):
        expected_permissions = {
            ("biblio.livre", self.reader_group): (1, 0, 0, 0),
            ("biblio.livre", self.librarian_group): (1, 1, 1, 1),
            ("biblio.auteur", self.reader_group): (1, 0, 0, 0),
            ("biblio.auteur", self.librarian_group): (1, 1, 1, 1),
            ("biblio.genre", self.reader_group): (1, 0, 0, 0),
            ("biblio.genre", self.librarian_group): (1, 1, 1, 1),
            ("biblio.emprunt", self.reader_group): (1, 0, 0, 0),
            ("biblio.emprunt", self.librarian_group): (1, 1, 1, 1),
            ("biblio.retour.wizard", self.reader_group): (0, 0, 0, 0),
            ("biblio.retour.wizard", self.librarian_group): (1, 1, 1, 1),
        }

        for (model_name, group), expected in expected_permissions.items():
            model = self.env["ir.model"]._get(model_name)
            access = self.env["ir.model.access"].search(
                [
                    ("model_id", "=", model.id),
                    ("group_id", "=", group.id),
                ]
            )
            self.assertEqual(len(access), 1, model_name)
            actual = (
                access.perm_read,
                access.perm_write,
                access.perm_create,
                access.perm_unlink,
            )
            self.assertEqual(actual, expected, "%s for %s" % (model_name, group.name))

    def test_reader_can_read_but_cannot_change_catalogue(self):
        livre = self.env["biblio.livre"].create({"name": "Livre de lecture"})
        reader_env = self.env(user=self.reader.id, su=False)
        reader_livre = reader_env["biblio.livre"]

        self.assertTrue(reader_livre.search([("id", "=", livre.id)]))
        reader_livre = reader_livre.browse(livre.id)
        with self.assertRaises(AccessError):
            reader_livre.write({"name": "Modification interdite"})
        with self.assertRaises(AccessError):
            reader_livre.create({"name": "Création interdite"})

    def test_librarian_has_full_catalogue_access(self):
        librarian_env = self.env(user=self.librarian.id, su=False)
        librarian_livre = librarian_env["biblio.livre"]
        livre = librarian_livre.create({"name": "Livre géré"})
        livre.write({"name": "Livre mis à jour"})
        livre.unlink()

        librarian_auteur = librarian_env["biblio.auteur"]
        auteur = librarian_auteur.create({"name": "Auteur géré"})
        auteur.unlink()

        librarian_genre = librarian_env["biblio.genre"]
        genre = librarian_genre.create({"name": "Genre géré"})
        genre.unlink()

    def test_reader_is_read_only_for_loans(self):
        member = self.env["res.partner"].create(
            {
                "name": "Membre sécurité",
                "est_membre": True,
            }
        )
        livre = self.env["biblio.livre"].create({"name": "Livre sécurité"})
        loan = self.env["biblio.emprunt"].create(
            {
                "membre_id": member.id,
                "livre_id": livre.id,
            }
        )
        reader_env = self.env(user=self.reader.id, su=False)
        reader_loan = reader_env["biblio.emprunt"].browse(loan.id)

        self.assertTrue(reader_loan.read(["reference", "state"]))
        with self.assertRaises(AccessError):
            reader_loan.write({"date_retour_prevue": "2027-01-01"})
        with self.assertRaises(AccessError):
            reader_env["biblio.emprunt"].create(
                {
                    "membre_id": member.id,
                    "livre_id": livre.id,
                }
            )
        with self.assertRaises(AccessError):
            reader_env["biblio.retour.wizard"].create({"emprunt_id": loan.id})

    def test_librarian_can_manage_loans_and_return_wizard(self):
        member = self.env["res.partner"].create(
            {
                "name": "Membre bibliothécaire",
                "est_membre": True,
            }
        )
        livre = self.env["biblio.livre"].create({"name": " Livre"})
        librarian_env = self.env(user=self.librarian.id, su=False)
        loan = librarian_env["biblio.emprunt"].create(
            {
                "membre_id": member.id,
                "livre_id": livre.id,
            }
        )

        wizard = librarian_env["biblio.retour.wizard"].create(
            {"emprunt_id": loan.id}
        )
        self.assertEqual(wizard.emprunt_id, loan)
        loan.action_emprunter()
        loan.unlink()

    def test_loan_record_rules_are_defined(self):
        reader_rule = self.env.ref("biblio_gestion.rule_biblio_emprunt_lecteur")
        librarian_rule = self.env.ref(
            "biblio_gestion.rule_biblio_emprunt_bibliothecaire"
        )

        self.assertEqual(reader_rule.model_id.model, "biblio.emprunt")
        self.assertEqual(librarian_rule.model_id.model, "biblio.emprunt")
        self.assertIn(self.reader_group, reader_rule.groups)
        self.assertIn(self.librarian_group, librarian_rule.groups)
