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


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_to_approve(self):
        for task in self:
            current_stage_id = self.stage_id
            next_stage_id = self.env['project.task.type'].search([
                ('name', '=', 'To Approve'), '|',
                ('project_ids', '=', self.project_id.id),
                ('project_ids', '=', False)
            ], limit=1)
            if next_stage_id:
                self.stage_id = next_stage_id.id
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }

    def action_done(self):
        for task in self:
            current_stage_id = self.stage_id
            next_stage_id = self.env['project.task.type'].search([
                ('name', '=', 'Done'), '|',
                ('project_ids', '=', self.project_id.id),
                ('project_ids', '=', False)
            ], limit=1)
            if next_stage_id:
                self.stage_id = next_stage_id.id
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
