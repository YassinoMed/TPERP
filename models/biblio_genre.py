from odoo import fields, models


class BiblioGenre(models.Model):
    _name = 'biblio.genre'
    _description = 'Genre'
    _order = 'name'

    name = fields.Char(string="Genre", required=True)
    description = fields.Char(string="Description")

    _sql_constraints = [
        ('name_unique', 'unique(name)', "Ce genre existe déjà."),
    ]