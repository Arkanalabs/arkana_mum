from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(
            lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            calendar_start = pytz.utc.localize(datetime.combine(
                max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(datetime.combine(
                min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals(
                calendar_start, calendar_end) - work_entries._to_intervals()
            # if outside:
            #     raise UserError(_("Some part of %s's calendar is not covered by any work entry. Please complete the schedule.") % contract.employee_id.name)

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(
                self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(
                self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(
                self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(
                _("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = self.employee_ids._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close'])
        contracts._generate_work_entries(
            payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', self.employee_ids.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        # validated = work_entries.action_validate()
        # if not validated:
        #     raise UserError(_("Some work entries could not be validated."))

        default_values = Payslip.default_get(Payslip.fields_get())
        for contract in contracts:
            values = dict(default_values, **{
                'employee_id': contract.employee_id.id,
                'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslip = self.env['hr.payslip'].new(values)
            payslip._onchange_employee()
            values = payslip._convert_to_write(payslip._cache)
            payslips += Payslip.create(values)
        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }


class Contract(models.Model):
    _inherit = 'hr.contract'

    name = fields.Char('Contract Reference', required=False)
    job_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Type', related='job_id.job_type')
    contract_type = fields.Selection([
        ("pkwt", "PKWT"),
        ("phl", "PHL"),
        ("ppkwt", "PPKWT"),
        # ("tetap","TETAP")
    ], string='Contract Type')
    month_end = fields.Integer(string='End Month', default=4)
    date_now = fields.Date(string='Date_now', default=fields.Date.today())
    date_interval = fields.Integer(
        string='Interval Date', compute="_date_interval", readonly=1)
    benefits_ids = fields.One2many(
        'hr.applicant.benefits', 'contract_id', 'Line')
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
        if 'state' in vals:
            if vals.get('state') == 'open':
                if self.contract_type == 'pkwt' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_pkwt')
                    # self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_pkwt')})
                elif self.contract_type == 'phl' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_phl')
                    # self.write({'name': self.env['ir.sequence'].next_by_code('kontrak_phl')})
                elif self.contract_type == 'ppkwt' and self.job_type == 'internal':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_ppkwt')

                elif self.contract_type == 'pkwt' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_pkwt_ext')
                elif self.contract_type == 'phl' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_phl_ext')
                elif self.contract_type == 'ppkwt' and self.job_type == 'external':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'kontrak_ppkwt_ext')
                else:
                    raise UserError(
                        "Please fill the 'Contract Type' field before !")

                if not self.date_end:
                    raise UserError(
                        "Please fill the 'End Date' field before !")

                if not self.employee_id.birthday:
                    raise UserError(
                        "Please fill the 'Birthday' field on Employee's Form before !")

                code = self.company_id.code
                if not code:
                    code = ''
                name_code = str(vals['name']).split('*')
                vals['name'] = name_code[0] + code + name_code[1]
                self.write({'name': vals['name']})

                if self.contract_type != 'phl' or self.job_type != 'external':
                    deduction = self.env['hr.salary.rule.category'].search(
                        [('name', '=', 'Deduction')])
                    allowance = self.env['hr.salary.rule.category'].search(
                        [('name', '=', 'Allowance')])
                    struct = self.structure_type_id.default_struct_id
                    struct.rule_ids.filtered(
                        lambda x: x.name == 'Net Salary').amount_python_compute = 'result = categories.BASIC + categories.ALW - categories.DED'
                    if not struct.flag_code:
                        # Potongan Pajak
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'BPJSK',
                            'name': 'BPJS Kesehatan',
                            'sequence': 110,
                            'amount_python_compute': 'result = GROSS * 1 / 100',
                        })
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'JHT',
                            'name': 'BPJS Jaminan Hari Tua',
                            'sequence': 120,
                            'amount_python_compute': 'result = GROSS * 1 / 100',
                        })
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'amount_select': 'code',
                            'code': 'JP',
                            'name': 'BPJS Jaminan Pensiun',
                            'sequence': 130,
                            'amount_python_compute': 'result = GROSS * 1 / 100',
                        })
                        struct.flag_code = True

                        # Other Inputs
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': deduction.id,
                            'code': 'ATTD',
                            'name': 'Potongan Kehadiran',
                            'sequence': 150,
                            'amount_select': 'code',
                            'amount_python_compute': 'result = inputs.ATTD and inputs.ATTD.amount',
                        })
                        self.env['hr.payslip.input.type'].create({
                            'name': 'Potongan Kehadiran',
                            'code': 'ATTD',
                            'struct_ids': [(4, struct.id)]
                        })
                        self.env['hr.salary.rule'].create({
                            'struct_id': struct.id,
                            'category_id': allowance.id,
                            'code': 'INS',
                            'name': 'Insentif Kehadiran',
                            'sequence': 140,
                            'amount_select': 'code',
                            'amount_python_compute': 'result = inputs.INS and inputs.INS.amount',
                        })
                        self.env['hr.payslip.input.type'].create({
                            'name': 'Insentif Kehadiran',
                            'code': 'INS',
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
                _logger.warning(
                    '===================> Stop Recruitment %s <===================' % (contract.name))
                before_three_months = contract.date_end - \
                    relativedelta(months=+3)
                before_two_months = contract.date_end - \
                    relativedelta(months=+2)
                before_one_months = contract.date_end - \
                    relativedelta(months=+1)

                if before_three_months == date.today() \
                        or before_two_months == date.today() or before_one_months == date.today():
                    contract.month_end -= 1
                    contract.notif = True
                    template = self.env.ref(
                        'hr_mum.template_mail_notif_contract')
                    template.sudo().send_mail(contract.id, raise_exception=True, force_send=True)

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
    flag_category = fields.Boolean(
        string='Category', compute='_compute_category')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        string="Currency", related='company_id.currency_id', readonly=True)

    @api.depends('category_id')
    def _compute_category(self):
        for rec in self:
            if rec.category_id.name == 'Net':
                rec.flag_category = True
            else:
                rec.flag_category = False
