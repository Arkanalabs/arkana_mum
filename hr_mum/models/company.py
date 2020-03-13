from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char('Company Code')

    