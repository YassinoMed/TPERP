from odoo import api, fields, models


class BiblioAuteur(models.Model):
    _name = 'biblio.auteur'
    _description = 'Auteur'
    _order = 'name'

    name = fields.Char(string="Nom", required=True)
    biographie = fields.Text(string="Biographie")
    date_naissance = fields.Date(string="Date de naissance")
    livre_ids = fields.One2many('biblio.livre', 'auteur_id', string="Livres")
    nb_livres = fields.Integer(string="Nombre de livres", compute='_compute_nb_livres')

    @api.depends('livre_ids')
    def _compute_nb_livres(self):
        for auteur in self:
            auteur.nb_livres = len(auteur.livre_ids)

    def action_view_livres(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Livres de %s' % self.name,
            'res_model': 'biblio.livre',
            'view_mode': 'list,form',
            'domain': [('auteur_id', '=', self.id)],
            'context': {'default_auteur_id': self.id},
        }
