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


class Project(models.Model):
    _inherit = 'project.project'

    project_task_ids = fields.Many2many(
        'project.task.template', string='Automated Task', domain="[('is_active', '=', True)]")
    user_partner_id = fields.Many2one(
        'res.partner', string='Assigned To', domain="[('user_ids', '!=', False)]")
    date_start = fields.Date('Date Start', default=fields.Date.today())

    @api.model
    def _create_task_project(self):
        project_ids = self.search([])
        for project in project_ids:
            _logger.warning(
                '===================> Stop Recruitment %s <===================' % (project.name))
            # if project.date_start:
                # if after_one_months == date.today():
            task_ids = project.project_task_ids
            if task_ids:
                for rec in task_ids:
                    stage = project.env['project.task.type'].search(
                        [], order='sequence', limit=1)
                    user_id = project.user_id.search([]).filtered(
                        lambda x: x.name == project.user_partner_id.name)
                    if rec.task_type == 'weekly':
                        after_one_week = project.date_start + \
                            relativedelta(weeks=+1)
                        if after_one_week == date.today():
                            _logger.warning(
                                '===================> Stop Recruitment %s <===================' % (rec.task_type))
                            project.env['project.task'].create([
                                {
                                    'project_id': project.id,
                                    'name': rec.name,
                                    'user_id': user_id.id,
                                    'stage_id': stage.id
                                },
                            ])
                    elif rec.task_type == 'monthly':
                        after_one_months = project.date_start + \
                            relativedelta(months=+1)
                        if after_one_months == date.today():
                            _logger.warning(
                                '===================> Stop Recruitment %s <===================' % (rec.task_type))
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
    task_type = fields.Selection(
        [("weekly", "Weekly"), ("monthly", "Monthly")], string='Task Type')
    project_id = fields.Many2one('project.project', string="Project")
