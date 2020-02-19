from odoo import models, fields, tools, api, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

import time
import math
from datetime import date
from datetime import datetime
from datetime import time as datetime_time
from dateutil.relativedelta import relativedelta
from odoo.tools import html_translate

import babel, logging

_logger = logging.getLogger(__name__)

class HrJobOrder(models.Model):
    _name = 'hr.job.order'
    _description = 'Job Order'
    _order = 'name desc, id desc'

    name = fields.Char(string='Name', required=True)

class Applicant(models.Model):
    _inherit = 'hr.applicant'
    
    # file_ids = fields.One2many(
    #     'hr.applicant.file', 'applicant_id', string='File')
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type', related='job_id.job_type')
    user_id = fields.Many2one(related='job_id.user_id')
    # stage_id = fields.Many2one(readonly=True)
    flag_admin = fields.Boolean(string='Flag Admin', compute='_compute_flag_admin')
    flag_ol = fields.Boolean(string='Flag', compute='_compute_flag_ol')
    flag_archive = fields.Boolean(string='Flag Archive')
    # psikotes = fields.Binary('Psikotes')
    file_psikotes = fields.Char('File Psikotes')
    user_applicant_id = fields.Integer(string='User', related='job_id.create_uid.id')
    progress = fields.Char(string='Progress', related='stage_id.progress')
    time_ids = fields.One2many('hr.applicant.time', 'applicant_id', 'Time')
    sequence_stage = fields.Integer('Sequence', related='stage_id.sequence')
    gender = fields.Selection([("Pria","Pria"),("Wanita","Wanita")], string='Gender')
    place_of_birth = fields.Char(string='Place')
    birth = fields.Date(string='Place, Date of Birth', store=True)
    age = fields.Integer(string='Age', default=False, compute='_age_compute')
    no_ktp = fields.Char(string='No. KTP')
    address = fields.Text(string='Address')
    degree = fields.Selection([
        ("smp","SMP"),("sma","SMA"),("smk","SMK"),("d1","D1"),("d2","D2"),
        ("d3","D3"),("d4","D4"),("s1","S1"),("s2","S2"),
        ("s3","S3"),], string='Degree')
    # marital_status = fields.Char(string='Marital Status')
    marital_status = fields.Selection([
        ("single","Lajang"),
        ("married","Menikah"),
        ], string='Marital Status')
    work_experience = fields.Char(string='Work Experience (year)')
    image_applicant = fields.Image(string="Image")
    file_name = fields.Char(string='File Name')
    stage_end = fields.Boolean(string='Stage End')
    stage_early = fields.Boolean(string='Stage Early', compute='_compute_stage_early')
    benefits_ids = fields.One2many('hr.applicant.benefits', 'applicant_id', 'Benefits')
    base_salary = fields.Monetary(string='Base Salary')
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    contract_period = fields.Integer(string='Contract Period', default=1)
    effective_date = fields.Date(string='Effective Date', default=lambda x: fields.Datetime.today())
    fasility = fields.Text(string='Fasility')
    thp_total = fields.Monetary(string='Total THP', compute='_compute_thp')

    @api.model
    def create(self, vals):
        rec = super(Applicant, self).create(vals)
        if rec.image_applicant:
            allowed_extension = ['img', 'jpg', 'png', 'jpeg']
            if (len(rec.image_applicant) / 1024.0 / 1024.0) >= 2:
                raise UserError('Ukuran dokumen maksimal 2MB')
            if rec.file_name:
                if not rec.file_name.split('.')[-1].lower() in allowed_extension:
                    raise UserError('Dokumen harus berformat *.img/*.jpg/*.jpeg/*.png !')
        # for file in rec.file_ids:
        #     if file.file:
        #         if (len(file.file) / 1024.0 / 1024.0) >= 2:
        #             raise UserError('Ukuran dokumen maksimal 2MB')
                # if not self.file_name.split('.')[-1].lower() in allowed_extension:
                #     raise UserError('Dokumen harus berformat *.pdf/*.img/*.jpg/*.jpeg/*.png !')
        return rec

    def _compute_flag_admin(self):
      for rec in self:
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            rec.flag_admin = True
        else :
            rec.flag_admin = False
    
    def _compute_flag_ol(self):
      for rec in self:
        if self.stage_id.name == 'Offering Letter':
            rec.flag_ol = True
        else :
            rec.flag_ol = False
    
    def _compute_stage_early(self):
        for rec in self:
            if self.stage_id.search([('sequence', '=', 1)]) == self.stage_id:
                rec.stage_early = True
            else :
                rec.stage_early = False

    @api.depends('benefits_ids.wage')
    def _compute_thp(self):
        for rec in self:
            thp = 0.0
            for benefits in rec.benefits_ids:
                thp += benefits.wage
            rec.thp_total = thp + rec.base_salary

    def reset_applicant(self):
        """ Reinsert the applicant into the recruitment pipe in the previous stage"""
        # default_stage_id = self.stage_id.search([('sequence', '<', self.stage_id.id)], limit=1)
        default_stage_id = self.stage_id
        self.write({
            'active': True, 
            'stage_id': default_stage_id.id,
            'flag_archive': False,
        })
    
    def archive_applicant(self):
        self.flag_archive = True
        self.write({'active': False})
    
    @api.depends('birth')
    def _age_compute(self):
        for rec in self:
            if self.birth:
                # rec.age = (datetime.now().year - rec.birth.year)
                birth = rec.birth.strftime("%Y-%m-%d")
                d1 = datetime.strptime(birth, "%Y-%m-%d").date()
                d2 = date.today()
                rec.age = relativedelta(d2, d1).years
            else:
                rec.age = 0

    def button_rollback(self):
        for rec in self:
            stage_id = rec.stage_id.search([('sequence', '<', self.stage_id.sequence)], order='sequence desc', limit=1)
            stage_early = rec.stage_id.search([], order='sequence', limit=2)[1]
            rec.stage_end = False
            if rec.stage_id == stage_early:
                rec.stage_early = True
            if stage_id:
                rec.stage_id = stage_id
                self.env['hr.applicant.time'].create({
                    'applicant_id': rec.id,
                    'name': "Rollback to %s" % (self.stage_id.name),
                    'time_process': fields.Datetime.now()
                })

    def button_process(self):
        for process in self:
            stage_id = process.stage_id.search([('sequence', '>', self.stage_id.sequence)], limit=1)
            stage_end = process.stage_id.search([], order='sequence desc', limit=2)[1]
            if process.stage_id == stage_end:
                process.stage_end = True
            if stage_id:
                process.stage_id = stage_id
                process.stage_early = False
                self.env['hr.applicant.time'].create({
                    'applicant_id': process.id,
                    'name': self.stage_id.name,
                    'time_process': fields.Datetime.now()
                })
            # elif process.stage_id == process.stage_id.search([])[-1]:
            #     raise UserError('Sorry, This is the last process')    
            # elif not stage_id:
            #     raise UserError('Sorry, This is the last stage')

    def act_download_offering_letter(self):
        self.ensure_one()
        res = self.env.ref("hr_mum.mum_offering_letter_py3o").with_context({
            'discard_logo_check': True}).report_action(self)
        return res
    
    def create_employee_from_applicant(self):
        self = self.with_context({
            'image_applicant': self.image_applicant,
            'no_ktp': self.no_ktp,
            'birth': self.birth,
            'place_of_birth': self.place_of_birth,
            'address': self.address,
            'phone': self.partner_phone,
            'gender': self.gender
        })
        return super(Applicant, self).create_employee_from_applicant()

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _sql_constraints = [
        ('No. KTP', 'unique(identification_id)', 'No. KTP sudah pernah didaftarkan.'),
        ('NIP (Nomor Induk Pegawai)', 'unique(nip)', 'NIP sudah pernah digunakan.')]

    identification_id = fields.Char(string='No. KTP')
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type', related='job_id.job_type')
    marital_status = fields.Selection([
        ("single","Lajang"),
        ("married","Menikah"),
        ], string='Marital Status')
    gender_employee = fields.Selection([("Pria","Pria"),("Wanita","Wanita")], string='Gender')
    address = fields.Text(string='Address')
    nip = fields.Char(string='NIP (Nomor Induk Pegawai)')
    departure_date = fields.Date('Departure Date')
    bank_name = fields.Char('Bank Name')
    bank_no_rec = fields.Char('No Account Bank')
    phone_employee = fields.Char('Phone')
    
    @api.model
    def create(self, vals):
        vals.update({
            'image_1920': self.env.context.get('image_applicant', False), 
            'identification_id': self.env.context.get('no_ktp', False), 
            'birthday': self.env.context.get('birth', False), 
            'place_of_birth': self.env.context.get('place_of_birth', False), 
            'address': self.env.context.get('address', False),
            'phone_employee': self.env.context.get('phone', False),
            'gender_employee': self.env.context.get('gender', False) 
            })
        return super(HrEmployee, self).create(vals)

class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    departure_date = fields.Date(string='Departure Date', default=fields.Date.today())
    
    def action_register_departure(self):
        employee = self.employee_id
        employee.departure_date = self.departure_date
        return super(HrDepartureWizard, self).action_register_departure()

class HrApplicantFile(models.Model):
    _name = 'hr.applicant.file'
    _description = 'File'

    name = fields.Char(string='Name', required=True)
    applicant_id = fields.Many2one('hr.applicant', ondelete='cascade')
    file = fields.Binary(string='File')
    is_required = fields.Boolean(string='Required')

class HrApplicantFile(models.Model):
    _name = 'hr.applicant.benefits'
    _description = 'Benefits Info'

    name = fields.Char(string='Type')
    applicant_id = fields.Many2one('hr.applicant', ondelete='cascade')
    wage = fields.Monetary(string='Wage')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    number = fields.Integer(string='Numb', default=10)

class HrApplicantTime(models.Model):
    _name = 'hr.applicant.time'

    name = fields.Char(string='Name')
    time_process = fields.Datetime('Time')
    applicant_id = fields.Many2one('hr.applicant', 'Applicant')
    ket = fields.Text(string='Keterangan')

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


class Job(models.Model):
    _inherit = 'hr.job'
    _order = 'create_date desc'

    @api.model
    def _default_flag_admin(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            return True
        else:
            return False
    
    code = fields.Char('Code', compute="_compute_code", store=True)
    job_ids = fields.Many2many('hr.job.order', string='Job Order')
    job_type = fields.Selection([
        ('internal', 'Internal'), ('external', 'External')
    ],default='internal', string='Type')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda x: x.env.user.id)
    file_template_id = fields.Many2one('hr.file.template', default=lambda r: r.env[
                                       'hr.file.template'].search([], limit=1))
    date_start = fields.Date('Date Start', default=lambda self: fields.Datetime.now().strftime("%Y-%m-%d"))
    date_finish = fields.Date('Date Finish', readonly=True)
    state = fields.Selection(selection_add=[("finish", "Finish")])
    date_dif = fields.Integer('Day Difference', readonly=True)
    # address_id = fields.Many2one('res.partner', 'Address')
    job_location_id = fields.Many2one('hr.job.location', 'Job Location')
    salary_expected = fields.Float('Expected Salary')
    flag_for_admin = fields.Boolean(string='Flag Admin', default=_default_flag_admin)
    flag_salary = fields.Boolean(string='Flag')
    flag_employee = fields.Boolean(string='Flag')
    qualification = fields.Html(string='Qualification', translate=html_translate, sanitize=False)
    alias_name = fields.Char('Email Alias', invisible=True)
    description = fields.Html('Description', translate=html_translate, sanitize=False)
    
    @api.model
    def create(self, vals):
        value = super(Job, self).create(vals)
        if value.job_type == 'internal' or value.flag_for_admin == True:
            value.website_published = True
        else:
            value.website_published = False
    
        if value.user_id:
            value.notification_action()
        return value
    
    def write(self, vals):
        if 'state' in vals:
            if vals.get('state') == 'finish' :
                self.website_published = False
        return super(Job, self).write(vals)

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
        return super(Job, self).set_open()

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
                job.date_finish = fields.Datetime.today()
    

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
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type', related='job_id.job_type')
    contract_type = fields.Selection([
        ("pkwt","PKWT"),
        ("phl","PHL"),
        ("tetap","TETAP")
    ], string='Contract Type', required=True)
    month_end = fields.Integer(string='End Month', default=4)

    def write(self, vals):
        if 'state' in vals :
            if vals.get('state') == 'open':
                if self.contract_type == 'pkwt':
                    self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_pkwt')})
                elif self.contract_type == 'phl':
                    self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_phl')})
                else:   
                    self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_tetap')})
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
        
        project_task_ids = fields.Many2many('project.task.template', string='Automated Task', domain=[('is_active', '=', True)])
        date_start = fields.Date('Date Start', default=fields.Date.today(), readonly=True)

        @api.model
        def _create_task_project(self):
            project_ids = self.search([])
            for project in project_ids:
                 _logger.warning('===================> Stop Recruitment %s <===================' % (project.name))  
                 if project.date_start:
                    after_one_months = project.date_start + relativedelta(months=+1)
                    if after_one_months:
                        # after_one_months == date.today()
                        task = project.project_task_ids
                        if task:
                            for rec in task:
                                stage = project.env['project.task.type'].search([], order='sequence', limit=1)
                                project.env['project.task'].create([
                                    {
                                    'project_id': project.id,
                                    'name': rec.name,
                                    'user_id': False,
                                    'stage_id': stage.id
                                    },
                                ])
            
    class ProjectTaskTemplate(models.Model):
        _name = 'project.task.template'

        name = fields.Char(string='Task Name')
        is_active = fields.Boolean(string='Active')
        project_id = fields.Many2one('project.project', string="Project")

    class HrJobLocation(models.Model):
        _name = 'hr.job.location'

        name = fields.Char(string='Location')
        user_id = fields.Many2one('res.users', 'User Name')
    
    # class Partner(models.Model):
    #     _inherit = 'res.partner'

    #     # rekrutment = fields.Boolean('Rekrutment')
    #     type = fields.Selection(selection_add=[("recruitment", "Recruitment")], default="recruitment")
    #     user_id = fields.Many2one("res.users", "User")
    
        
