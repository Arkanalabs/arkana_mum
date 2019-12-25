from odoo import models, fields, tools, api, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

import time
import math
from datetime import datetime
from datetime import time as datetime_time
from dateutil import relativedelta

import babel, logging

_logger = logging.getLogger(__name__)

class HrJobOrder(models.Model):
    _name = 'hr.job.order'
    _description = 'Job Order'
    _order = 'name desc, id desc'

    name = fields.Char(string='Name', required=True)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    file_ids = fields.One2many(
        'hr.applicant.file', 'applicant_id', string='File')
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type', related='job_id.job_type')
    psikotes = fields.Binary('Psikotes')
    progress = fields.Char(string='Progress', related='stage_id.progress')
    time_ids = fields.One2many('hr.applicant.time', 'applicant_id', 'Time')
    sequence_stage = fields.Integer('Sequence', related='stage_id.sequence')
    qualified = fields.Boolean(string='Qualified')
    gender = fields.Selection([("pria","Pria"),("wanita","Wanita")], string='Gender')
    birth = fields.Char(string='Place, Date of Birth')
    age = fields.Integer(string='Age', default=False)
    no_ktp = fields.Char(string='No. KTP', default=False)
    address = fields.Text(string='Address')
    work_experience = fields.Char(string='Work Experience (year)')

    def button_process(self):
        for process in self:
            stage_id = process.stage_id.search([('sequence', '>', self.stage_id.sequence)], limit=1)
            if self.qualified:
                process.stage_id = stage_id
                self.env['hr.applicant.time'].create({
                    'applicant_id': process.id,
                    'name': self.stage_id.name,
                    'time_process': fields.Datetime.now()
                })
            else:
                raise UserError('Sorry, You are not qualified')    
    

class HrApplicantFile(models.Model):
    _name = 'hr.applicant.file'
    _description = 'File'

    name = fields.Char(string='Name', required=True)
    applicant_id = fields.Many2one('hr.applicant', ondelete='cascade')
    file = fields.Binary(string='File')
    is_required = fields.Boolean(string='Required')

class HrApplicantTime(models.Model):
    _name = 'hr.applicant.time'

    name = fields.Char(string='Name')
    time_process = fields.Datetime('Time')
    applicant_id = fields.Many2one('hr.applicant', 'Applicant')

class HrFileTemplate(models.Model):
    _name = 'hr.file.template'
    _description = 'File Template'

    name = fields.Char(string='Name', required=True)
    file_ids = fields.One2many(
        'hr.file.template.line', 'template_id', string='File Template Line')
    publish_on_website = fields.Boolean('Publish On Website')


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

    code = fields.Char('Code', compute="_compute_code", store=True)
    job_ids = fields.Many2many('hr.job.order', string='Job Order')
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type')
    file_template_id = fields.Many2one('hr.file.template', default=lambda r: r.env[
                                       'hr.file.template'].search([], limit=1))
    date_start = fields.Date('Date Start', default=lambda self: fields.Datetime.now().strftime("%Y-%m-%d"))
    date_finish = fields.Date('Date Finish')
    date_dif = fields.Integer('Day Difference')
    state = fields.Selection(selection_add=[("finish", "Finish")])
    address_id = fields.Many2one('res.partner', 'Job Location', domain=[('type', '=', 'recruitment')])
    salary_expected = fields.Float('Expected Salary')
    qualification = fields.Char(string='Qualification')

    def _compute_code(self):
        for code in self:
            self.code = '%s/%s/%s/%s' % (code.env.user.name, code.date_start, code.address_id.name, code.name)
    
    def set_open(self):
        date_finish = fields.Datetime.today().strftime("%Y-%m-%d")
        # d1 = datetime.strptime(str(self.date_start),'%Y-%m-%d') 
        date_1 = datetime.strptime(date_finish, '%Y-%m-%d').date()
        date_dif = date_1 - self.date_start
        date_days = date_dif.days
        self.write({
            'date_finish': date_1,
            'date_dif': date_days
        })
        # date_dif = self.date_start - self.date_finish
        return super(HrJob, self).set_open()

    @api.model
    def _auto_stop_reqruitment(self): 
        job_ids = self.env['hr.job'].search([('state', '=', 'recruit')])
        for job in job_ids:
            date_now = fields.Datetime.today().strftime("%Y-%m-%d")
            date = datetime.strptime(date_now, '%Y-%m-%d').date()
            interval_time = date - job.date_start
            if interval_time.days > 10 :
                _logger.warning('===================> Stop Recruitment %s <===================' % (job.name))
                job.state = 'finish'
    
    @api.model
    def create(self, vals):
        value = super(HrJob, self).create(vals)
        if value.job_type == 'internal':
            value.website_published = True
        else:
            value.website_published = False
        # vals['website_published'] = self.file_template_id.browse(vals['file_template_id']).publish_on_website
        return value

    def close_dialog(self):
        form_view = self.env.ref('hr.view_hr_job_form')
        return {
            'name': _('Job'),
            'res_model': 'hr.job',
            'res_id': self.id,
            'views': [(form_view.id, 'form'),],
            'type': 'ir.actions.act_window',
            'context': {'form_view_initial_mode': 'edit', 'force_detailed_view': 'true'},
        }

    class HrRecruitmentStage(models.Model):
        _inherit = 'hr.recruitment.stage'

        progress = fields.Char(string='Progress')
 
    class Partner(models.Model):
        _inherit = 'res.partner'

        # rekrutment = fields.Boolean('Rekrutment')
        type = fields.Selection(selection_add=[("recruitment", "Recruitment")])
    
        
