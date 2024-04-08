# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    consignment_location_id = fields.Many2one(
        'stock.location',
        string='Consignment Location',
        domain=[('usage', '=', 'internal')],
        help='The location used for consignment purposes.'
    )

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def onchange_location_id(self):
        for move in self.move_lines:
            move.write({'location_id': self.location_id})

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('consignment', 'Consignment Order')],
        track_visibility='onchange',
    )

    consignment_picking_count = fields.Integer(
        compute='_compute_consignment_picking_count',
        string='Consignment Pickings Count',
    )

def action_consignment_sale(self):
    """
    Xử lý bán hàng ký gửi
    """
    self.ensure_one()

    try:
        # Kiểm tra vị trí ký gửi
        consignment_location = self.partner_id.consignment_location_id
        if not consignment_location:
            raise UserError(_('Vị trí ký gửi chưa được định nghĩa cho đối tác này.'))

        # Lấy loại giao hàng "delivery" và vị trí xuất hàng từ kho
        picking_type = self.env.ref('stock.picking_type_out')
        default_location_src_id = consignment_location.id

        # Bắt đầu transaction
        self.env.cr.commit()

        # Tạo phiếu xuất kho
        picking_vals = {
            'partner_id': self.partner_id.id,
            'location_id': default_location_src_id,
            'location_dest_id': self.partner_id.property_stock_customer.id,
            'picking_type_id': picking_type.id,
            'origin': self.name,
            'sale_order_id': self.id
        }
        new_picking = self.env['stock.picking'].create(picking_vals)

        # Tạo di chuyển kho cho từng dòng sản phẩm
        Move = self.env['stock.move']
        for line in self.order_line:
            move_vals = {
                'name': line.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'location_id': default_location_src_id,
                'location_dest_id': self.partner_id.property_stock_customer.id,
                'picking_id': new_picking.id,
            }
            Move.create(move_vals)

        # Xác nhận và chỉ định phiếu xuất kho
        new_picking.action_confirm()
        new_picking.action_assign()

        # Cập nhật trạng thái và commit transaction
        self.state = 'sale'
        self.env.cr.commit()

        return True

    except Exception as e:
        # Rollback nếu có lỗi
        self.env.cr.rollback()
        raise UserError(_('Lỗi khi xử lý bán hàng ký gửi cho consignment %s: %s') % (self.id, str(e)))


    def action_confirm_consignment(self):
        self.ensure_one()
        self.write({'state': 'consignment'})
        self._create_consignment_stock_picking()

    def _create_consignment_stock_picking(self):
        StockPicking = self.env['stock.picking']
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
        if not picking_type:
            raise UserError(_("Internal Picking Type not found. Please configure an internal picking type."))
        
        consignment_location = self.partner_id.consignment_location_id
        if not consignment_location:
            raise UserError(_("Please configure a Consignment Location for this partner."))

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': consignment_location.id,
            'scheduled_date': fields.Datetime.now(),
            'origin': self.name,
            'move_lines': [
                (0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': self.warehouse_id.lot_stock_id.id,
                    'location_dest_id': consignment_location.id,
                }) for line in self.order_line if line.product_id.type != 'service'
            ],
        }
        picking = StockPicking.create(picking_vals)
        picking.action_confirm()
        picking.action_assign()

    def _compute_consignment_picking_count(self):
        for order in self:
            pickings = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('picking_type_id.code', '=', 'internal'),
            ])
            order.consignment_picking_count = len(pickings)

    def action_view_consignment_picking(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.env['stock.picking'].search([
            ('origin', '=', self.name),
            ('picking_type_id.code', '=', 'internal'),
        ])
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    def action_cancel_consignment(self):
        self.ensure_one()
        self.write({'state': 'cancel'})
