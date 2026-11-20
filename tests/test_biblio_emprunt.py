import re
from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestBiblioEmprunt(TransactionCase):
    """Regression tests for the TP5 borrowing workflow."""

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
        cls.livre = cls.env["biblio.livre"].create({"name": "Livre empruntable"})

    def _create_loan(self, **overrides):
        values = {
            "membre_id": self.member.id,
            "livre_id": self.livre.id,
            "date_debut": self.today,
            "date_retour_prevue": self.today + timedelta(days=14),
        }
        values.update(overrides)
        return self.env["biblio.emprunt"].create(values)

    def test_fields_defaults_and_reference(self):
        loan = self._create_loan()

        self.assertEqual(loan.state, "draft")
        self.assertEqual(loan.date_debut, self.today)
        self.assertEqual(loan.membre_id, self.member)
        self.assertEqual(loan.livre_id, self.livre)
        self.assertTrue(re.match(r"^EMP/\d{4}/\d{4}$", loan.reference))
        self.assertTrue(loan.reference.startswith("EMP/%s/" % self.today.year))
        self.assertTrue(loan._fields["reference"].readonly)
        self.assertTrue(loan._fields["date_retour"].readonly)
        self.assertTrue(loan._fields["duree"].store)
        self.assertTrue(loan._fields["membre_id"].required)
        self.assertTrue(loan._fields["livre_id"].required)

    def test_references_are_unique(self):
        first = self._create_loan()
        second = self._create_loan()

        self.assertNotEqual(first.reference, second.reference)

    def test_member_domain_only_accepts_library_members(self):
        domain = self.env["biblio.emprunt"]._fields["membre_id"].domain
        self.assertIn("est_membre", domain)
        self.assertIn("True", domain)

    def test_onchange_sets_a_planned_return_date(self):
        start_date = date(2026, 1, 10)
        with Form(self.env["biblio.emprunt"]) as form:
            form.membre_id = self.member
            form.livre_id = self.livre
            form.date_debut = start_date

            self.assertEqual(form.date_retour_prevue, start_date + timedelta(days=14))

    def test_planned_return_cannot_precede_start(self):
        with self.assertRaises(ValidationError):
            self._create_loan(
                date_debut=self.today,
                date_retour_prevue=self.today - timedelta(days=1),
            )

    def test_workflow_makes_the_book_unavailable_then_restores_it(self):
        loan = self._create_loan()

        loan.action_emprunter()
        self.assertEqual(loan.state, "cours")
        self.assertFalse(self.livre.disponible)

        loan.action_retour()
        self.assertEqual(loan.state, "rendu")
        self.assertEqual(loan.date_retour, self.today)
        self.assertTrue(self.livre.disponible)

    def test_cancelling_an_active_loan_restores_the_book(self):
        loan = self._create_loan()
        loan.action_emprunter()

        loan.action_annuler()

        self.assertEqual(loan.state, "draft")
        self.assertTrue(self.livre.disponible)

    def test_unavailable_book_cannot_be_borrowed(self):
        self.livre.disponible = False
        loan = self._create_loan()

        with self.assertRaises(UserError):
            loan.action_emprunter()

    def test_duration_is_stored_and_recomputed(self):
        start_date = date(2026, 1, 10)
        loan = self._create_loan(
            date_debut=start_date,
            date_retour_prevue=start_date + timedelta(days=10),
        )
        self.assertEqual(loan.duree, 10)

        loan.action_emprunter()
        loan.action_retour(date_retour=start_date + timedelta(days=12))

        self.assertEqual(loan.duree, 12)

    def test_overdue_loan_is_marked_and_can_still_be_returned(self):
        loan = self._create_loan(
            date_debut=self.today - timedelta(days=20),
            date_retour_prevue=self.today - timedelta(days=1),
        )
        loan.action_emprunter()

        self.env["biblio.emprunt"]._mark_overdue_emprunts()
        loan.invalidate_recordset(["state", "en_retard"])

        self.assertEqual(loan.state, "retard")
        self.assertTrue(loan.en_retard)

        loan.action_retour()
        self.assertEqual(loan.state, "rendu")
        self.assertFalse(loan.en_retard)

    def test_wizard_closes_the_loan(self):
        loan = self._create_loan()
        loan.action_emprunter()
        wizard = (
            self.env["biblio.retour.wizard"]
            .with_context(default_emprunt_id=loan.id)
            .create({"date_retour": self.today})
        )

        result = wizard.action_confirm_retour()

        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(loan.state, "rendu")
        self.assertTrue(self.livre.disponible)
        self.assertTrue(self.env["biblio.retour.wizard"]._transient)

    def test_livre_contains_related_loans(self):
        loan = self._create_loan()
        self.assertIn(loan, self.livre.emprunt_ids)

    def test_auteur_has_a_smart_button_for_books(self):
        auteur = self.env["biblio.auteur"].create({"name": "Auteur statistique"})
        livre = self.env["biblio.livre"].create(
            {
                "name": "Livre statistique",
                "auteur_id": auteur.id,
            }
        )

        action = auteur.action_view_livres()

        self.assertEqual(action["res_model"], "biblio.livre")
        self.assertEqual(action["domain"], [("auteur_id", "=", auteur.id)])
        self.assertIn(livre, auteur.livre_ids)
        form_view = self.env.ref("biblio_gestion.biblio_auteur_view_form")
        self.assertIn("action_view_livres", form_view.arch)
        self.assertIn("oe_stat_button", form_view.arch)

    def test_views_actions_menus_and_report_are_available(self):
        view_types = set(
            self.env["ir.ui.view"]
            .search([("model", "=", "biblio.emprunt")])
            .mapped("type")
        )
        self.assertTrue({"list", "form", "search"}.issubset(view_types))

        action = self.env.ref("biblio_gestion.biblio_emprunt_action")
        self.assertEqual(action.res_model, "biblio.emprunt")
        self.assertIn("list", action.view_mode)

        wizard_action = self.env.ref("biblio_gestion.biblio_retour_wizard_action")
        self.assertEqual(wizard_action.res_model, "biblio.retour.wizard")
        self.assertEqual(wizard_action.target, "new")

        loan_menu = self.env.ref("biblio_gestion.menu_biblio_emprunts")
        self.assertEqual(loan_menu.action, action)
        self.assertTrue(self.env.ref("biblio_gestion.menu_biblio_retour"))

        report = self.env.ref("biblio_gestion.action_report_emprunt")
        self.assertEqual(report.model, "biblio.emprunt")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertTrue(self.env.ref("biblio_gestion.report_emprunt"))

    def test_receipt_template_is_autonomous(self):
        template = self.env.ref("biblio_gestion.report_emprunt")
        arch = template.arch

        self.assertNotIn("web.html_container", arch)
        self.assertNotIn("web.external_layout", arch)
        self.assertNotIn("http://", arch)
        self.assertNotIn("https://", arch)
        self.assertIn("<style", arch)

    def test_receipt_uses_a_local_minimal_pdf_layout(self):
        report = self.env.ref("biblio_gestion.action_report_emprunt")

        layout = report._get_layout()

        expected_layout = self.env.ref("biblio_gestion.report_minimal_layout")
        self.assertEqual(layout, expected_layout)
        self.assertNotIn("t-call-assets", layout.arch)

    def test_receipt_renders_as_pdf(self):
        loan = self._create_loan()
        pdf_content, file_type = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf("biblio_gestion.report_emprunt", loan.ids)
        )

        self.assertEqual(file_type, "pdf")
        self.assertTrue(pdf_content.startswith(b"%PDF"))
