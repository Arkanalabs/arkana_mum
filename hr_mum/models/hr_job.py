from odoo import models, fields, tools, api, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

import time
import math
from datetime import date
from datetime import datetime
from datetime import time as datetime_time
from dateutil.relativedelta import relativedelta

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
    user_id = fields.Many2one(related='job_id.user_id')
    psikotes = fields.Binary('Psikotes')
    user_applicant_id = fields.Integer(string='User', related='job_id.create_uid.id')
    progress = fields.Char(string='Progress', related='stage_id.progress')
    time_ids = fields.One2many('hr.applicant.time', 'applicant_id', 'Time')
    sequence_stage = fields.Integer('Sequence', related='stage_id.sequence')
    qualified = fields.Boolean(string='Qualified')
    gender = fields.Selection([("pria","Pria"),("wanita","Wanita")], string='Gender')
    place_of_birth = fields.Char(string='Place')
    birth = fields.Date(string='Place, Date of Birth', store=True)
    age = fields.Integer(string='Age', default=False, compute='_age_compute')
    no_ktp = fields.Char(string='No. KTP', default=False)
    address = fields.Text(string='Address')
    # marital_status = fields.Char(string='Marital Status')
    marital_status = fields.Selection([
        ("single","Single"),
        ("married","Married"),
        ("widow","Widow"),
        ("widower","Widower")], string='Marital Status')
    work_experience = fields.Char(string='Work Experience (year)')
    image_applicant = fields.Image(string="Image")

    @api.depends('birth')
    def _age_compute(self):
        for rec in self:
            birth = rec.birth.strftime("%Y-%m-%d")
            d1 = datetime.strptime(birth, "%Y-%m-%d").date()
            d2 = date.today()
            rec.age = relativedelta(d2, d1).years

    def button_process(self):
        for process in self:
            stage_id = process.stage_id.search([('sequence', '>', self.stage_id.sequence)], limit=1)
            if self.qualified and stage_id:
                process.stage_id = stage_id
                self.env['hr.applicant.time'].create({
                    'applicant_id': process.id,
                    'name': self.stage_id.name,
                    'time_process': fields.Datetime.now()
                })
            # elif process.stage_id == process.stage_id.search([])[-1]:
            #     raise UserError('Sorry, This is the last process')    
            elif not stage_id:
                raise UserError('Sorry, This is the last stage')
            else :
                raise UserError('Sorry, You are not qualified')

    def create_employee_from_applicant(self):
        self = self.with_context({
            'image_applicant': self.image_applicant
        })
        
        return super(HrApplicant, self).create_employee_from_applicant()

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def create(self, vals):
        vals['image_1920'] = self.env.context.get('image_applicant', False)
        return super(HrEmployee, self).create(vals)

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

    @api.model
    def _default_type(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            return [('internal', 'Internal'), ('external', 'External')]
        else :
            return [('external', 'External')]
    
    code = fields.Char('Code', compute="_compute_code", store=True)
    job_ids = fields.Many2many('hr.job.order', string='Job Order')
    job_type = fields.Selection(_default_type, string='Type')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda x: x.env.user.id)
    file_template_id = fields.Many2one('hr.file.template', default=lambda r: r.env[
                                       'hr.file.template'].search([], limit=1))
    date_start = fields.Date('Date Start', default=lambda self: fields.Datetime.now().strftime("%Y-%m-%d"))
    date_finish = fields.Date('Date Finish')
    state = fields.Selection(selection_add=[("finish", "Finish")])
    date_dif = fields.Integer('Day Difference')
    address_id = fields.Many2one('res.partner', 'Job Location', domain=[('type', '=', 'recruitment')])
    salary_expected = fields.Float('Expected Salary')
    flag_salary = fields.Boolean(string='Flag')
    qualification = fields.Text(string='Qualification')

    @api.depends('date_start', 'address_id', 'name')
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
    
        if value.user_id:
            value.notification_action()
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
    
    def notification_action(self):
        # notification = {
        #         'mail_message_id': self.env['mail.notification'].mail_message_id.id,
        #         'res_partner_id': self.user_id.partner_id.browse(3),
     	#         'notification_type': 'inbox',
        #         'notification_status': 'ready',
        #     }
        # create_notif = self.env['mail.notification'].create(notification).ids

        message = self.env['mail.message'].create({'message_type':"notification",
            'subject': "New Job Position",
            'subtype_id': self.env.ref("hr_recruitment.mt_job_new").id, # subject type
            'body': "New job position %s" % (self.name),   
            'model': self._name,
            'res_id': self.id,
        })
        
        self.env['mail.notification'].create({
                'res_partner_id': self.env.ref('base.partner_admin').id,
                'notification_type': 'inbox',
                'notification_status': 'ready',   
                'mail_message_id': message.id,
            })

class Contract(models.Model):
    _inherit = 'hr.contract'

    name = fields.Char('Contract Reference', required=False)
    month_end = fields.Integer(string='End Month', default=4)

    def write(self, vals):
        if 'state' in vals :
            if vals.get('state') == 'open':
                self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_number')})
        # elif vals.get('state') == 'open':
        #     vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_number')
        return super(Contract, self).write(vals)

    @api.model
    def _notif_contract(self): 
        contract_ids = self.search([('state', '=', 'open')])
        for contract in contract_ids:
            if contract.date_end:
                _logger.warning('===================> Stop Recruitment %s <===================' % (contract.name))
                before_three_months = contract.date_end - relativedelta(months=+3)
                before_two_months = contract.date_end - relativedelta(months=+2)
                before_one_months = contract.date_end - relativedelta(months=+1)

                if before_three_months == date.today() \
                    or before_two_months == date.today() or before_one_months == date.today():
                    contract.month_end -= 1
                    template = self.env.ref('hr_mum.template_mail_notif_contract')
                    template.sudo().send_mail(contract.id, raise_exception=True, force_send= True)

    
    class HrRecruitmentStage(models.Model):
        _inherit = 'hr.recruitment.stage'

        progress = fields.Char(string='Progress')
 
    class Project(models.Model):
        _inherit = 'project.project'

        date_start = fields.Date('Date Start', default=fields.Date.today())
        
        @api.model
        def _create_task_project(self):
            project_ids = self.search([])
            for project in project_ids:
                 _logger.warning('===================> Stop Recruitment %s <===================' % (project.name))
                 if project.date_start:
                    after_one_months = project.date_start + relativedelta(months=+1)
                    if after_one_months:
                        project.env['project.task'].create([
                            {
                               'project_id': project.id,
                               'name': 'Invoice',
                               'user_id': False
                            },
                            {
                               'project_id': project.id,
                               'name': 'Rekap Absensi',
                               'user_id': False
                            },
                            {
                               'project_id': project.id,
                               'name': 'Slip Gaji',
                               'user_id': False
                            }
                        ])

    class Partner(models.Model):
        _inherit = 'res.partner'

        # rekrutment = fields.Boolean('Rekrutment')
        type = fields.Selection(selection_add=[("recruitment", "Recruitment")])
    
        
