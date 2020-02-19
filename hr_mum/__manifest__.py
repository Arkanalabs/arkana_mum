# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'HR MUM',
    'summary': 'Custom HR for MUM',
    'license': 'AGPL-3',
    'version': '13.0',
    'category': 'Human Resources',
    'author': 'Arkana, Joenan <joenan@arkana.co.id>, Romskuy',
    'website': 'https://www.arkana.co.id',
    'description': """HR MUM""",
    'depends': [
        'website_hr_recruitment',
        'report_py3o',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/mum_security.xml',
        'report/report_hr_mum.xml',
        'data/service_cron.xml',
        'data/config_data.xml',
        'data/message_data.xml',
        'data/sequence.xml',
        'data/template_mail_notif_contract.xml',
        'views/view_hr_recruitment.xml',
        'views/templates_website_hr_recruitment.xml',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'application': True,
}
