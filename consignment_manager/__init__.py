# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
from . import models

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sale_order_obj = env['sale.order']
    consignment_orders = sale_order_obj.search([('state', '=', False)])
    if consignment_orders:
        consignment_orders.write({'state': 'consignment'})
