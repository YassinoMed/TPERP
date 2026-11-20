from odoo import fields, models


class BiblioLivre(models.Model):
    _name = 'biblio.livre'
    _description = 'Livre'
    _order = 'name'

    name = fields.Char(string="Titre", required=True)
    isbn = fields.Char(string="ISBN")
    date_publication = fields.Date(string="Date de parution")
    nb_pages = fields.Integer(string="Nombre de pages")
    resume = fields.Text(string="Résumé")
    couverture = fields.Image(string="Couverture", max_width=512, max_height=512)
    disponible = fields.Boolean(string="Disponible", default=True)
    etat = fields.Selection(
        [('neuf', 'Neuf'), ('bon', 'Bon'), ('use', 'Usé')],
        string="État physique",
        default='bon',
    )
    auteur_id = fields.Many2one('biblio.auteur', string="Auteur", ondelete='restrict')
    genre_ids = fields.Many2many('biblio.genre', string="Genres")
    emprunt_ids = fields.One2many(
        'biblio.emprunt',
        'livre_id',
        string="Emprunts",
    )
