from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _get_layout(self):
        if (
            self
            and len(self) == 1
            and self.report_name == "biblio_gestion.report_emprunt"
        ):
            return self.env.ref(
                "biblio_gestion.report_minimal_layout",
                raise_if_not_found=False,
            )
        return super()._get_layout()
