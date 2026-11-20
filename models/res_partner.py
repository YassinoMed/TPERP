# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    est_membre = fields.Boolean(string="Membre de la bibliothèque")
    carte_membre = fields.Char(string="N° de carte", copy=False)
    emprunt_ids = fields.One2many(
        "biblio.emprunt",
        "membre_id",
        string="Emprunts",
    )
    nb_emprunts = fields.Integer(
        string="Nombre d'emprunts",
        compute="_compute_nb_emprunts",
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared_values = []
        for vals in vals_list:
            values = dict(vals)
            if values.get("est_membre") and not values.get("carte_membre"):
                card_number = (
                    self.env["ir.sequence"].sudo().next_by_code("biblio.carte")
                )
                if card_number:
                    values["carte_membre"] = card_number
            prepared_values.append(values)
        return super().create(prepared_values)

    @api.depends("emprunt_ids")
    def _compute_nb_emprunts(self):
        for partner in self:
            partner.nb_emprunts = len(partner.emprunt_ids)

    @api.onchange("est_membre")
    def _onchange_est_membre(self):
        if self.est_membre and not self.carte_membre:
            self.carte_membre = (
                self.env["ir.sequence"].sudo().next_by_code("biblio.carte")
            )

    def action_view_emprunts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Emprunts de %s" % self.name,
            "res_model": "biblio.emprunt",
            "view_mode": "list,form",
            "domain": [("membre_id", "=", self.id)],
            "context": {"default_membre_id": self.id},
        }

    def unlink(self):
        active_states = ("cours", "retard")
        for partner in self:
            active_loan_count = self.env["biblio.emprunt"].search_count(
                [
                    ("membre_id", "=", partner.id),
                    ("state", "in", active_states),
                ]
            )
            if active_loan_count:
                raise UserError(
                    "Ce membre ne peut pas être supprimé car il possède "
                    "au moins un emprunt en cours."
                )
        return super().unlink()
