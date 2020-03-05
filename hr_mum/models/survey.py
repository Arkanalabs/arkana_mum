from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    applicant_id = fields.Many2one('hr.applicant', 'Applicant', compute="_domain_applicant")
    email = fields.Char(compute="_compute_email")

    def _compute_email(self):
        for rec in self:
            email_line = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Email Anda')
            rec.email = email_line.value_text
    
    # @api.constrains('applicant_id')
    def _domain_applicant(self):
        for rec in self:
            nama_line = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Nama Anda')
            email_line = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Email Anda')        
            expected_salary = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Berapa gaji yang diharapkan jika Anda diterima sebagai karyawan?')
            applicant = rec.applicant_id.search([('partner_name', '=', nama_line.value_text), ('email_from', '=', email_line.value_text)])
            applicant.salary_expected = expected_salary.value_number
            rec.applicant_id = applicant.id
            # if applicant in rec.applicant_id.search([]):
            # else:
            #     raise UserError('Mohon maaf tidak bisa ..')

    
    # @api.model
    # def create(self, vals):
    #     survey = super(SurveyUserInput, self).create(vals)
    #     if not survey.applicant_id:
    #         raise UserError('Mohon maaf tidak bisa ..')
    #     return survey
    
    # def create(self, vals):
    #     rec = super(SurveyUserInput, self).create(vals)
    #     nama = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Nama Anda')
    #     name_applicant = rec.applicant_id.filtered(lambda x: x.partner_name == nama.value_text)
    #     rec.applicant_id = name_applicant.id

    #     nama = self.user_input_line_ids.search([]).filtered(lambda x: x.question_id.title == 'Nama Anda')
    #     for rec in self:
    #         for res in nama:
                
    #             name_applicant = rec.applicant_id.earch([]).filtered(lambda x: x.partner_name == res.value_text)
    #             for apply in name_applicant:
    #                 rec.applicant_id = apply.id
    #     # if rec.applicant_id.partner_name == nama.value_text:
    #     #     rec.applicant_id = 
    #     return rec