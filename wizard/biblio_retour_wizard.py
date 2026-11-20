# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class BiblioRetourWizard(models.TransientModel):
    _name = "biblio.retour.wizard"
    _description = "Assistant de retour de livre"

    emprunt_id = fields.Many2one(
        "biblio.emprunt",
        string="Emprunt",
        required=True,
        domain="[('state', 'in', ['cours', 'retard'])]",
    )
    date_retour = fields.Date(
        string="Date de retour effectif",
        required=True,
        default=lambda self: fields.Date.context_today(self.env.user),
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "emprunt_id" in fields_list:
            loan_id = self.env.context.get("default_emprunt_id")
            if not loan_id:
                active_model = self.env.context.get("active_model")
                active_id = self.env.context.get("active_id")
                if active_model == "biblio.emprunt" and active_id:
                    loan_id = active_id
            if loan_id:
                values["emprunt_id"] = loan_id
        return values

    def action_confirm_retour(self):
        self.ensure_one()
        if not self.emprunt_id:
            raise UserError("Sélectionnez l'emprunt à clôturer.")
        self.emprunt_id.action_retour(self.date_retour)
        return {"type": "ir.actions.act_window_close"}
