from odoo import models, fields, api


class Company(models.Model):
    _inherit = 'res.company'

    atd_period = fields.Selection([
        ('previous', 'Previous'),
        ('current', 'Current'),
    ], string='Period', default='previous')
    # atd_date_from = fields.Integer('Date form', default='1')
    # atd_date_to = fields.Integer('Date to', default='31')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    atd_period = fields.Selection([
        ('previous', 'Previous'),
        ('current', 'Current'),
    ], string='Period', related='company_id.atd_period', store=True, readonly=False)
    # atd_date_from = fields.Integer('Date form', related='company_id.atd_date_from')
    # atd_date_to = fields.Integer('Date to', related='company_id.atd_date_to')
