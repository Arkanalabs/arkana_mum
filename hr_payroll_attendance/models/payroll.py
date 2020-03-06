from odoo import models, fields, tools, api, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

import time
import math
from datetime import date
from datetime import datetime
from datetime import time as datetime_time
from dateutil.relativedelta import relativedelta

import babel
import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        if not self:
            return super(HrPayslip, self).compute_sheet()
        if self.company_id.atd_period == 'current':
            date_from = self.date_from
            date_to = self.date_to
        else:
            date_from_df = fields.Date.from_string(self.date_from)
            date_to_df = fields.Date.from_string(self.date_to)
            date_from_prev_df = date_from_df - relativedelta(months=1)
            date_from = fields.Date.to_string(date_from_prev_df) + ' 00:00:01'
            date_to_prev_df = date_to_df - relativedelta(months=1)
            date_to = fields.Date.to_string(date_to_prev_df) + ' 23:59:59'
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', date_from),
            ('check_in', '<=', date_to),
        ])
        days = len(attendances)
        # find input with code ATD
        work_line = self.env['hr.payslip.worked_days'].search([
            ('payslip_id', '=', self.id),
            ('work_entry_type_id.code', '=', 'WORK100'),
        ], limit=1)
        if work_line:
            work_line.number_of_days = days if attendances else 0
        else:
            self.env['hr.payslip.worked_days'].create({
                'payslip_id': self.id,
                'work_entry_type_id': self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1).id,
                'name': 'Attendance',
                'number_of_days': days if attendances else 0,
            })
        return super(HrPayslip, self).compute_sheet()
