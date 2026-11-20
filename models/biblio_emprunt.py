# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class BiblioEmprunt(models.Model):
    _name = "biblio.emprunt"
    _description = "Emprunt"
    _rec_name = "reference"
    _order = "date_debut desc, id desc"

    reference = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        index=True,
    )
    membre_id = fields.Many2one(
        "res.partner",
        string="Membre",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('est_membre', '=', True)]",
    )
    livre_id = fields.Many2one(
        "biblio.livre",
        string="Livre",
        required=True,
        ondelete="restrict",
        index=True,
    )
    date_debut = fields.Date(
        string="Date d'emprunt",
        required=True,
        default=lambda self: fields.Date.context_today(self.env.user),
    )
    date_retour_prevue = fields.Date(string="Retour prévu")
    date_retour = fields.Date(string="Retour effectif", readonly=True, copy=False)
    duree = fields.Integer(
        string="Durée (jours)",
        compute="_compute_duree",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("cours", "En cours"),
            ("retard", "En retard"),
            ("rendu", "Rendu"),
        ],
        string="État",
        default="draft",
        copy=False,
        required=True,
        index=True,
    )
    en_retard = fields.Boolean(
        string="En retard",
        compute="_compute_en_retard",
        search="_search_en_retard",
        readonly=True,
    )

    _sql_constraints = [
        (
            "reference_unique",
            "unique(reference)",
            "La référence d'emprunt doit être unique.",
        ),
    ]

    @api.model
    def _next_reference(self):
        reference = self.env["ir.sequence"].sudo().next_by_code("biblio.emprunt")
        if not reference:
            raise UserError("La séquence des emprunts n'est pas configurée.")
        return reference

    @api.model_create_multi
    def create(self, vals_list):
        prepared_values = []
        for vals in vals_list:
            values = dict(vals)
            if not values.get("reference"):
                values["reference"] = self._next_reference()
            date_debut = values.get("date_debut") or fields.Date.context_today(
                self.env.user
            )
            values["date_debut"] = date_debut
            if not values.get("date_retour_prevue"):
                values["date_retour_prevue"] = date_debut + timedelta(days=14)
            prepared_values.append(values)
        return super().create(prepared_values)

    @api.onchange("date_debut")
    def _onchange_date_debut(self):
        if self.date_debut:
            self.date_retour_prevue = self.date_debut + timedelta(days=14)

    @api.onchange("livre_id")
    def _onchange_livre_id(self):
        if self.livre_id and not self.livre_id.disponible:
            return {
                "warning": {
                    "title": "Livre indisponible",
                    "message": (
                        "Le livre « %s » est actuellement emprunté. "
                        "Vous pourrez le sélectionner après son retour."
                    ) % self.livre_id.name,
                }
            }

    @api.depends("date_debut", "date_retour_prevue", "date_retour")
    def _compute_duree(self):
        for loan in self:
            end_date = loan.date_retour or loan.date_retour_prevue
            if loan.date_debut and end_date:
                loan.duree = max((end_date - loan.date_debut).days, 0)
            else:
                loan.duree = 0

    @api.depends("date_retour_prevue", "date_retour", "state")
    def _compute_en_retard(self):
        today = fields.Date.context_today(self.env.user)
        for loan in self:
            loan.en_retard = bool(
                loan.state in ("cours", "retard")
                and not loan.date_retour
                and loan.date_retour_prevue
                and loan.date_retour_prevue < today
            )

    @api.model
    def _search_en_retard(self, operator, value):
        today = fields.Date.context_today(self.env.user)
        overdue_domain = [
            ("state", "in", ("cours", "retard")),
            ("date_retour", "=", False),
            ("date_retour_prevue", "<", today),
        ]
        if operator in ("=", "=="):
            is_positive = bool(value)
        elif operator in ("!=", "<>"):
            is_positive = not value
        else:
            raise UserError("Opérateur de recherche non pris en charge pour le retard.")
        return overdue_domain if is_positive else ["!"] + overdue_domain

    @api.constrains("membre_id")
    def _check_membre_id(self):
        for loan in self:
            if loan.membre_id and not loan.membre_id.est_membre:
                raise ValidationError(
                    "Le contact sélectionné n'est pas membre de la bibliothèque."
                )

    @api.constrains("date_debut", "date_retour_prevue", "date_retour")
    def _check_return_dates(self):
        for loan in self:
            if (
                loan.date_debut
                and loan.date_retour_prevue
                and loan.date_retour_prevue < loan.date_debut
            ):
                raise ValidationError(
                    "La date de retour prévue ne peut pas précéder la date d'emprunt."
                )
            if (
                loan.date_debut
                and loan.date_retour
                and loan.date_retour < loan.date_debut
            ):
                raise ValidationError(
                    "La date de retour effectif ne peut pas précéder la date d'emprunt."
                )

    @api.constrains("livre_id", "state")
    def _check_single_active_loan_per_book(self):
        for loan in self:
            if loan.state not in ("cours", "retard"):
                continue
            duplicate_count = self.search_count(
                [
                    ("livre_id", "=", loan.livre_id.id),
                    ("state", "in", ("cours", "retard")),
                    ("id", "!=", loan.id),
                ]
            )
            if duplicate_count:
                raise ValidationError(
                    "Ce livre est déjà associé à un emprunt en cours."
                )

    def action_emprunter(self):
        active_states = ("cours", "retard")
        for loan in self:
            if loan.state != "draft":
                raise UserError("Seul un emprunt brouillon peut être confirmé.")
            if not loan.membre_id.est_membre:
                raise UserError(
                    "Le membre sélectionné n'est pas membre de la bibliothèque."
                )
            if not loan.date_retour_prevue:
                raise UserError(
                    "Renseignez la date de retour prévue avant de confirmer l'emprunt."
                )
            duplicate = self.search_count(
                [
                    ("livre_id", "=", loan.livre_id.id),
                    ("state", "in", active_states),
                    ("id", "!=", loan.id),
                ]
            )
            if duplicate:
                raise UserError("Ce livre est déjà emprunté.")
            if not loan.livre_id.disponible:
                raise UserError("Ce livre n'est pas disponible.")

        for loan in self:
            loan.write({"state": "cours"})
            loan.livre_id.write({"disponible": False})
        return True

    def action_retour(self, date_retour=None):
        active_states = ("cours", "retard")
        today = fields.Date.context_today(self.env.user)
        if isinstance(date_retour, str):
            date_retour = fields.Date.to_date(date_retour)
        actual_return_date = date_retour or today

        for loan in self:
            if loan.state not in active_states:
                raise UserError(
                    "Seul un emprunt en cours ou en retard peut être clôturé."
                )
            if actual_return_date < loan.date_debut:
                raise ValidationError(
                    "La date de retour effectif ne peut pas précéder la date d'emprunt."
                )

        for loan in self:
            loan.write(
                {
                    "date_retour": actual_return_date,
                    "state": "rendu",
                }
            )
            loan.livre_id.write({"disponible": True})
        return True

    def action_annuler(self):
        active_states = ("cours", "retard")
        for loan in self:
            if loan.state == "rendu":
                raise UserError("Un emprunt rendu ne peut plus être annulé.")

        for loan in self:
            if loan.state in active_states:
                loan.livre_id.write({"disponible": True})
            loan.write({"state": "draft", "date_retour": False})
        return True

    def unlink(self):
        active_states = ("cours", "retard")
        for loan in self.filtered(lambda item: item.state in active_states):
            loan.livre_id.write({"disponible": True})
        return super().unlink()

    @api.model
    def _mark_overdue_emprunts(self):
        today = fields.Date.context_today(self.env.user)
        overdue_loans = self.search(
            [
                ("state", "=", "cours"),
                ("date_retour_prevue", "<", today),
            ]
        )
        overdue_loans.write({"state": "retard"})
        return len(overdue_loans)
