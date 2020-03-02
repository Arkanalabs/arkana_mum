from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    applicant_id = fields.Many2one('hr.applicant', 'Applicant')
    user_input_line_id = fields.Many2one('survey.user_input_line', 'User Input Line', domain=[('question_id.title', '=', 'Email Anda')])
    email = fields.Char(compute="_compute_email")
    # realted="user_input_line_id.value_text"
    # compute="_compute_email"

    def _compute_email(self):
        for rec in self:
            email_line = rec.user_input_line_ids.filtered(lambda x: x.question_id.title == 'Email Anda')
            rec.email = email_line.value_text
    
    # def create(self, vals):
    #     rec = super(SuperUserInput, self).create(vals)
    #     rec.applicant