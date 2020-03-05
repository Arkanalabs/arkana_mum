# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payroll - Attendance Integration',
    'summary': 'Read attendance from payroll',
    'license': 'AGPL-3',
    'version': '13.0',
    'category': 'Human Resources',
    'author': 'Arkana, Joenan <joenan@arkana.co.id>',
    'website': 'https://www.arkana.co.id',
    'description': """Read attendance from payroll""",
    'depends': [
        'project',
    ],
    'data': [
        # 'data/service_cron.xml',
        # 'data/config_data.xml',
        # 'data/message_data.xml',
        # 'data/template_mail_notif_contract.xml',
        # 'security/ir.model.access.csv',
        # 'security/mum_security.xml',
        # 'views/view_payroll.xml',
        # 'views/view_res_config_settings.xml',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'application': True,
}
