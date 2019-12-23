# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'HR MUM',
    'summary': 'HR MUM',
    'license': 'AGPL-3',
    'version': '13.0',
    'category': 'Human Resources',
    'author': 'Arkana, Joenan <joenan@arkana.co.id>, Romskuy',
    'website': 'https://www.arkana.co.id',
    'description': """HR MUM""",
    'depends': [
        'website_hr_recruitment',
    ],
    'data': [
        'data/service_cron.xml',
        'security/ir.model.access.csv',
        'views/view_hr_recruitment.xml',
        'views/templates_website_hr_recruitment.xml',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'application': True,
}
