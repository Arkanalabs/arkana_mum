from odoo import models, fields, tools, api, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

import time
import math
from datetime import datetime
from datetime import time as datetime_time
from dateutil import relativedelta

import babel


class HrJobOrder(models.Model):
    _name = 'hr.job.order'
    _description = 'Job Order'
    _order = 'name desc, id desc'

    name = fields.Char(string='Name', required=True)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    file_ids = fields.One2many(
        'hr.applicant.file', 'applicant_id', string='File')


class HrApplicantFile(models.Model):
    _name = 'hr.applicant.file'
    _description = 'File'

    name = fields.Char(string='Name', required=True)
    applicant_id = fields.Many2one('hr.applicant', ondelete='cascade')
    file = fields.Binary(string='File')
    is_required = fields.Boolean(string='Required')


class HrFileTemplate(models.Model):
    _name = 'hr.file.template'
    _description = 'File Template'

    name = fields.Char(string='Name', required=True)
    file_ids = fields.One2many(
        'hr.file.template.line', 'template_id', string='File Template Line')


class HrFileTemplateLine(models.Model):
    _name = 'hr.file.template.line'
    _description = 'File Template Line'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_required = fields.Boolean(string='Required')
    template_id = fields.Many2one('hr.file.template', ondelete='cascade')


class HrJob(models.Model):
    _inherit = 'hr.job'

    job_ids = fields.Many2many('hr.job.order', string='Job Order')
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type')
    file_template_id = fields.Many2one('hr.file.template', default=lambda r: r.env[
                                       'hr.file.template'].search([], limit=1))
