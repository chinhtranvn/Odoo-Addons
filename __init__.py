# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID, _
from odoo.addons.base.models.res_model import get_models

def post_init_hook(cr, registry):
  """
  Hàm này được thực hiện sau khi module được cài đặt.
  Sửa trạng thái của các đơn hàng có trạng thái trống thành 'consignment'.
  """
  env = api.Environment(cr, SUPERUSER_ID, {})
  model_names = get_models(env, ['sale.order'])
  if 'sale.order' in model_names:
    sale_order_obj = env['sale.order']
    consignment_orders = sale_order_obj.search([('state', '=', False)])
    if consignment_orders:
      consignment_orders.write({'state': 'consignment'})
      # Ghi log thông báo
      env['ir.logging'].create({
        'name': 'Consignment module',
        'level': 'info',
        'message': _('Đã cập nhật trạng thái cho %d đơn hàng thành "ký gửi".') % len(consignment_orders),
      })
