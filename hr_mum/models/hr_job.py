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
    user_applicant_id = fields.Integer(related='job_id.create_uid.id')
    # stage_id = fields.Many2one(readonly=True)
    flag_admin = fields.Boolean(string='Flag Admin', compute='_compute_flag_admin')
    flag_ol = fields.Boolean(string='Flag', compute='_compute_flag_ol')
    flag_archive = fields.Boolean(string='Flag Archive')
    flag_client = fields.Boolean(string='Flag Client', compute='_compute_flag_client')
    # psikotes = fields.Binary('Psikotes')
    file_psikotes = fields.Char('File Psikotes')
    progress = fields.Char(string='Progress', related='stage_id.progress')
    time_ids = fields.One2many('hr.applicant.time', 'applicant_id', 'Time')
    sequence_stage = fields.Integer('Sequence', related='stage_id.sequence')
    gender_applicant = fields.Selection([("Pria","Pria"),("Wanita","Wanita")], string='Gender')
    place_of_birth = fields.Char(string='Place')
    birth = fields.Date(string='Place, Date of Birth', store=True)
    age = fields.Integer(string='Age', default=False, compute='_age_compute')
    no_ktp = fields.Char(string='No. KTP')
    address = fields.Text(string='Address')
    degree = [("SD","SD"),("SMP","SMP"),("SMA","SMA"),("MAN","MAN"),("SMK","SMK"),("D1","D1"),("D2","D2"),
        ("D3","D3"),("D4","D4"),("S1","S1"),("S2","S2"),
        ("S3","S3"),("Lainnya","Lainnya")]
    degree_applicant = fields.Selection(degree, string='Degree')
    school = fields.Char(string='University/School')
    # marital_status = fields.Char(string='Marital Status')
    marital_status_applicant = fields.Selection([
        ("Lajang","Lajang"),
        ("Menikah","Menikah"),
        ("Duda/Janda","Duda/Janda"),
        ], string='Marital Status')
    work_experience = fields.Integer(string='Work Experience')
    career_summary = fields.Text(string='Career Summary')
    image_applicant = fields.Image(string="Image")
    file_name = fields.Char(string='File Name')
    stage_end = fields.Boolean(string='Stage End')
    stage_early = fields.Boolean(string='Stage Early', compute='_compute_stage_early')
    benefits_ids = fields.One2many('hr.applicant.benefits', 'applicant_id', 'Benefits')
    base_salary = fields.Monetary(string='Base Salary')
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    contract_period = fields.Integer(string='Contract Period', default=1)
    effective_date = fields.Date(string='Effective Date', default=lambda x: fields.Datetime.today())
    facility = fields.Text(string='Facility')
    thp_total = fields.Monetary(string='Total THP', compute='_compute_thp')
    salary_proposed = fields.Monetary("Proposed Salary")
    salary_expected = fields.Monetary("Expected Salary")
    flag_benefits = fields.Boolean("Show Allowance")
    benefits_id = fields.Many2one('hr.applicant.benefits', 'Benefits')
    availability = fields.Date(default=fields.Date.today())
    job_location_id = fields.Many2one('hr.job.location', 'Job Location', related='job_id.job_location_id')
  
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
    
    def _compute_flag_client(self):
      for rec in self:
        if self.env.user.has_group('hr_mum.group_mum_client'):
            rec.flag_client = True
        else :
            rec.flag_client = False
    
    def _compute_flag_ol(self):
      for rec in self:
        if self.stage_id.name == 'Offering Letter':
            rec.flag_ol = True
        else :
            rec.flag_ol = False
    
    def _compute_stage_early(self):
        for rec in self:
            if self.stage_id.search([('sequence', '=', 0)]) == self.stage_id:
                rec.stage_early = True
            else :
                rec.stage_early = False

    @api.depends('benefits_ids.wage')
    def _compute_thp(self):
        for rec in self:
            thp = 0.0
            for benefits in rec.benefits_ids:
                thp += benefits.wage
            rec.thp_total = thp + rec.salary_proposed

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
        res = super(Applicant, self.with_context({
            'image_applicant': self.image_applicant,
            'no_ktp': self.no_ktp,
            'birth': self.birth,
            'place_of_birth': self.place_of_birth,
            'address': self.address,
            'phone': self.partner_phone,
            'gender': self.gender_applicant,
            'degree': self.degree_applicant,
            'marital': self.marital_status_applicant,
            'school': self.school,
        })).create_employee_from_applicant()
        # self = self.with_context({
        #     'image_applicant': self.image_applicant,
        #     'no_ktp': self.no_ktp,
        #     'birth': self.birth,
        #     'place_of_birth': self.place_of_birth,
        #     'address': self.address,
        #     'phone': self.partner_phone,
        #     'gender': self.gender_applicant,
        #     'degree': self.degree_applicant,
        #     'marital': self.marital_status_applicant,
        #     'school': self.school,
        # })
        
        work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Attendance')])
        payroll_type = self.env['hr.payroll.structure.type'].create({
            'emp_id': self.emp_id.id,
            'name': 'Gaji %s' % (self.emp_id.name),
            'wage_type': 'monthly',
            'default_schedule_pay': 'monthly',
            'default_work_entry_type_id': work_entry_type.id
        })

        # contract = self.env['hr.contract'].search([])
        self.env['hr.contract'].create({
            'employee_id': self.emp_id.id,
            'job_id': self.job_id.id,
            'wage': self.salary_proposed,
            'job_type': self.job_type,
            'structure_type_id': payroll_type.id
        })

        structure_id = self.env['hr.payroll.structure'].create({
            'name': self.emp_id.name,
            'type_id': payroll_type.id,
        })

        allowance = self.env['hr.salary.rule.category'].search([('name', '=', 'Allowance')])
        thp = self.env['hr.salary.rule.category'].search([('name', '=', 'Net')])
        if self.benefits_ids:
            for rec in self.benefits_ids:
                self.env['hr.salary.rule'].create({
                    'struct_id': structure_id.id,
                    'category_id': allowance.id,
                    'code': rec.code,
                    'name': rec.name,
                    'amount_fix': rec.wage,
                })        
        return res

class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    emp_id = fields.Many2one('hr.employee', 'Employee', ondelete='cascade')
    active = fields.Boolean('Active', default=True)

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    flag_code = fields.Boolean(string='Rules Fix')

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    thp = fields.Monetary(string='Salary THP')
    flag_category = fields.Boolean(string='Category', compute='_compute_category')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)

    @api.depends('category_id')
    def _compute_category(self):
        for rec in self:
            if rec.category_id.name ==  'Net':
                rec.flag_category = True
            else:
                rec.flag_category = False

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
    job_location_id = fields.Many2one('hr.job.location', 'Job Location', related='job_id.job_location_id')
    marital_status_employee = fields.Selection([
        ("Lajang","Lajang"),
        ("Menikah","Menikah"),
        ("Duda/Janda","Duda/Janda"),
        ], string='Status Marital')
    employee_gender = fields.Selection([("Pria","Pria"),("Wanita","Wanita")], string='Gender Employee')
    address = fields.Text(string='Address')
    nip = fields.Char(string='NIP (Nomor Induk Pegawai)')
    departure_date = fields.Date('Departure Date')
    bank_name = fields.Char('Bank Name')
    bank_no_rec = fields.Char('No Account Bank')
    phone_employee = fields.Char('Phone')
    degree = [("SD","SD"),("SMP","SMP"),("SMA","SMA"),("MAN","MAN"),("SMK","SMK"),("D1","D1"),("D2","D2"),
        ("D3","D3"),("D4","D4"),("S1","S1"),("S2","S2"),
        ("S3","S3"),("Lainnya","Lainnya")] 
    degree_employee = fields.Selection(degree, string='Degree')
    
    @api.model
    def create(self, vals):
        vals.update({
            'image_1920': self.env.context.get('image_applicant', False), 
            'identification_id': self.env.context.get('no_ktp', False), 
            'birthday': self.env.context.get('birth', False), 
            'place_of_birth': self.env.context.get('place_of_birth', False), 
            'address': self.env.context.get('address', False),
            'phone_employee': self.env.context.get('phone', False),
            'employee_gender': self.env.context.get('gender', False), 
            'degree_employee': self.env.context.get('degree', False),
            'marital_status_employee': self.env.context.get('marital', False),
            'study_school': self.env.context.get('school', False),
            })
        
        res = super(HrEmployee, self).create(vals)
        
        if res.job_type == 'internal':
            res.nip = self.env['ir.sequence'].next_by_code('nip_internal')
        elif res.job_type == 'external':
            res.nip = self.env['ir.sequence'].next_by_code('nip_external')

        return res

class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    departure_date = fields.Date(string='Departure Date', default=fields.Date.today())
    
    def action_register_departure(self):
        employee = self.employee_id
        employee.departure_date = self.departure_date
        employee.contract_id.structure_type_id.active = False
        employee.contract_id.search([('employee_id', '=', employee.id)]).write({
            'active': False,
        })
        employee.contract_id.structure_type_id.search([('emp_id', '=', employee.id)]).write({
            'active': False,
        })
        employee.contract_id.structure_type_id.default_struct_id.search([('type_id.emp_id', '=', employee.id)]).write({
            'active': False,
        })
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

    name = fields.Char(string='Type Allowance')
    code = fields.Char(string='Code')
    applicant_id = fields.Many2one('hr.applicant', ondelete='cascade')
    wage = fields.Monetary(string='Wage')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', ondelete='cascade')
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
    state = fields.Selection(selection_add=[("finish", "Recruiting Finish")])
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
    flag_cron = fields.Boolean(string='Cron')
    
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
    
    # def write(self, vals):
    #     if 'state' in vals:
    #         if vals.get('state') == 'finish' :
    #             self.website_published = False
    #     return super(Job, self).write(vals)

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

    def set_recruit(self):
        for record in self:
            record.write({'date_start': fields.Datetime.today()})
            record.flag_cron = False
        return super(Job, self).set_recruit()

    @api.model
    def _auto_stop_reqruitment(self): 
        job_ids = self.env['hr.job'].search([('state', '=', 'recruit')])
        for job in job_ids:
            date_now = fields.Datetime.today().strftime("%Y-%m-%d")
            date = datetime.strptime(date_now, '%Y-%m-%d').date()
            interval_time = date - job.date_start
            if interval_time.days > 10 :
                _logger.warning('===================> Stop Recruitment %s <===================' % (job.name))
                job.state = 'open'
                job.date_finish = fields.Datetime.today()
                job.flag_cron = True
    

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
        ("ppkwt", "PPKWT"),
        # ("tetap","TETAP")
    ], string='Contract Type')
    month_end = fields.Integer(string='End Month', default=4)
    date_now = fields.Date(string='Date_now', default=fields.Date.today())
    date_interval = fields.Integer(string='Interval Date', compute="_date_interval", readonly=1)
    benefits_ids = fields.One2many('hr.applicant.benefits', 'contract_id', 'Line')
    thp = fields.Monetary(string='THP')
    notif = fields.Boolean(string='Notif')
    
    @api.depends('date_start', 'date_end')
    def _date_interval(self):
        for rec in self:
            if rec.date_end and rec.date_start:
                years = rec.date_end.year - rec.date_start.year
                rec.date_interval = years
            else:
                rec.date_interval = 0

    def write(self, vals):
        if 'state' in vals :
            if vals.get('state') == 'open':
                if self.contract_type == 'pkwt' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_pkwt')
                    # self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_pkwt')})
                elif self.contract_type == 'phl' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_phl')
                    # self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_phl')})
                elif self.contract_type == 'ppkwt' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_ppkwt')
                
                elif self.contract_type == 'pkwt' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_pkwt_ext')
                elif self.contract_type == 'phl' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_phl_ext')
                elif self.contract_type == 'ppkwt' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code('kontrak_ppkwt_ext')
                else:
                    raise UserError('Mohon untuk mengisi Contract Type terlebih dulu !')
                
                code = self.company_id.code
                if not code :
                    code = ''
                name_code = str(vals['name']).split('*')
                vals['name'] = name_code[0] + code + name_code[1]
                self.write({'name': vals['name']})

                if self.contract_type != 'phl' or self.job_type != 'external':
                    deduction = self.env['hr.salary.rule.category'].search([('name', '=', 'Deduction')])
                    struct = self.structure_type_id.default_struct_id
                    if not struct.flag_code:
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'BPJSK',
                            'name': 'BPJS Kesehatan',
                            'sequence': 110,
                            'amount_python_compute': 'result = GROSS * 1 / 100' ,
                        })
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'JHT',
                            'name': 'BPJS Jaminan Hari Tua',
                            'sequence': 120,
                            'amount_python_compute': 'result = GROSS * 1 / 100' ,
                        })
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'JP',
                            'name': 'BPJS Jaminan Pensiun',
                            'sequence': 130,
                            'amount_python_compute': 'result = GROSS * 1 / 100' ,
                        })
                        struct.rule_ids.filtered(lambda x: x.name == 'THP').amount_python_compute = 'result = categories.BASIC + categories.ALW - categories.DED'
                        struct.flag_code = True
                                            
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'code': 'ATTD',
                            'name': 'Attendance',
                            'sequence': 150,
                            'amount_select': 'code' ,
                            'amount_python_compute': 'result = inputs.ATTD and inputs.ATTD.amount' ,
                        })
                        self.env['hr.payslip.input.type'].create({
                            'name':'Attendance',
                            'code':'ATTD',
                            'struct_ids': [(4, struct.id)]
                        })
                # else:   
                #     self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_tetap')})
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
                    contract.notif = True
                    template = self.env.ref('hr_mum.template_mail_notif_contract')
                    template.sudo().send_mail(contract.id, raise_exception=True, force_send= True)

    def act_download_report_contract(self):
        self.ensure_one()
        if self.contract_type == 'phl' and self.job_type == 'internal':
            res = self.env.ref("hr_mum.mum_phl_py3o").with_context({
                'discard_logo_check': True}).report_action(self)
        elif self.contract_type == 'pkwt' and self.job_type == 'internal':
            res = self.env.ref("hr_mum.mum_pkwt_py3o").with_context({
                'discard_logo_check': True}).report_action(self)
        elif self.contract_type == 'ppkwt' and self.job_type == 'internal':
            res = self.env.ref("hr_mum.mum_ppkwt_py3o").with_context({
                'discard_logo_check': True}).report_action(self)
       
        elif self.contract_type == 'phl' and self.job_type == 'external':
            res = self.env.ref("hr_mum.mum_phl_external_py3o").with_context({
                'discard_logo_check': True}).report_action(self)
        elif self.contract_type == 'pkwt' and self.job_type == 'external':
            res = self.env.ref("hr_mum.mum_pkwt_external_py3o").with_context({
                'discard_logo_check': True}).report_action(self)
        else:
            raise UserError('Mohon maaf tidak bisa ..')
        return res

    
    class HrRecruitmentStage(models.Model):
        _inherit = 'hr.recruitment.stage'

        progress = fields.Char(string='Progress')

    class Project(models.Model):
        _inherit = 'project.project'
        
        project_task_ids = fields.Many2many('project.task.template', string='Automated Task', domain="[('is_active', '=', True)]")
        user_partner_id = fields.Many2one('res.partner', string='Assigned To', domain="[('user_ids', '!=', False)]")
        date_start = fields.Date('Date Start', default=fields.Date.today())

        @api.model
        def _create_task_project(self):
            project_ids = self.search([])
            for project in project_ids:
                 _logger.warning('===================> Stop Recruitment %s <===================' % (project.name))  
                 if project.date_start:
                    # if after_one_months == date.today():
                    task_ids = project.project_task_ids
                    if task_ids:
                        for rec in task_ids:
                            stage = project.env['project.task.type'].search([], order='sequence', limit=1)
                            user_id = project.user_id.search([]).filtered(lambda x: x.name == project.user_partner_id.name)
                            if rec.task_type == 'weekly':
                                after_one_week = project.date_start + relativedelta(weeks=+1)
                                if after_one_week :
                                    _logger.warning('===================> Stop Recruitment %s <===================' % (rec.task_type))
                                    project.env['project.task'].create([
                                        {
                                        'project_id': project.id,
                                        'name': rec.name,
                                        'user_id': user_id.id,
                                        'stage_id': stage.id
                                        },
                                    ])
                            elif rec.task_type == 'monthly':
                                after_one_months = project.date_start + relativedelta(months=+1)
                                if after_one_months == date.today():
                                    _logger.warning('===================> Stop Recruitment %s <===================' % (rec.task_type))
                                    project.env['project.task'].create([
                                        {
                                        'project_id': project.id,
                                        'name': rec.name,
                                        'user_id': project.user_partner_id.id,
                                        'stage_id': stage.id
                                        },
                                    ])
        
    class ProjectTaskTemplate(models.Model):
        _name = 'project.task.template'

        name = fields.Char(string='Task Name')
        is_active = fields.Boolean(string='Active')
        task_type = fields.Selection([("weekly","Weekly"),("monthly","Monthly")], string='Task Type')
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
    
        
