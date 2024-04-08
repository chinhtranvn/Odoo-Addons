# -*- coding: utf-8 -*-
{
    'name': 'Consignment Manager',
    'version': '1.0',
    'summary': 'Manages Consignment Orders and Locations',
    'sequence': 10,
    'description': """Manage consignment processes in Odoo""",
    'category': 'Sales',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'sale', 'stock'],
    'data': [
        'views/consignment_views.xml',
    #    'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
