from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBiblioMember(TransactionCase):
    """Regression tests for the TP5 res.partner inheritance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.member = cls.env["res.partner"].create(
            {
                "name": "Membre de test",
                "est_membre": True,
                "carte_membre": "CARD-TP5-001",
            }
        )
        cls.livre = cls.env["biblio.livre"].create({"name": "Livre du membre"})

    def test_new_member_receives_a_card_number(self):
        member = self.env["res.partner"].create(
            {
                "name": "Nouveau membre",
                "est_membre": True,
            }
        )

        self.assertRegex(member.carte_membre, r"^MBR/\d{4}$")

    def test_member_fields_and_computed_loan_count(self):
        loan = self.env["biblio.emprunt"].create(
            {
                "membre_id": self.member.id,
                "livre_id": self.livre.id,
                "date_debut": self.today,
                "date_retour_prevue": self.today + timedelta(days=14),
            }
        )

        self.assertTrue(self.member.est_membre)
        self.assertEqual(self.member.carte_membre, "CARD-TP5-001")
        self.assertEqual(self.member.emprunt_ids, loan)
        self.assertEqual(self.member.nb_emprunts, 1)

    def test_member_with_active_loan_cannot_be_deleted(self):
        loan = self.env["biblio.emprunt"].create(
            {
                "membre_id": self.member.id,
                "livre_id": self.livre.id,
                "date_debut": self.today,
                "date_retour_prevue": self.today + timedelta(days=14),
            }
        )
        loan.action_emprunter()

        with self.assertRaises(UserError):
            self.member.unlink()

    def test_partner_form_displays_library_fields(self):
        view = self.env.ref("biblio_gestion.res_partner_view_biblio")
        arch = view.arch

        self.assertIn("est_membre", arch)
        self.assertIn("carte_membre", arch)
        self.assertIn("emprunt_ids", arch)
