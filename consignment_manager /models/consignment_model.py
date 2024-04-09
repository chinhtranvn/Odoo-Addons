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


from odoo import models, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_consignment_sale(self):
        self.ensure_one()  # Đảm bảo chỉ xử lý một đơn hàng
        if not self.partner_id.consignment_location_id:
            raise UserError(_('Địa điểm ký gửi không được thiết lập cho đối tác này.'))

        # Ghi nhận các phiếu xuất kho hiện có
        existing_picking_ids = set(self.picking_ids.ids)

        # Thực hiện quy trình xác nhận đơn hàng mặc định
        res = super(SaleOrder, self).action_confirm()

        # Xác định các phiếu xuất kho mới được tạo
        new_picking_ids = set(self.picking_ids.ids) - existing_picking_ids
        new_pickings = self.env['stock.picking'].browse(new_picking_ids)

        for picking in new_pickings:
            picking.write({'location_id': self.partner_id.consignment_location_id.id})
            for move_line in picking.move_lines.mapped('move_line_ids'):
                move_line.write({'location_id': self.partner_id.consignment_location_id.id})

        return res

    def action_confirm_consignment(self):
        self.ensure_one()
        self.write({'state': 'consignment'})
        self._create_consignment_stock_picking()

    def _create_consignment_stock_picking(self):
        StockPicking = self.env['stock.picking']
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
        if not picking_type:
            raise UserError(_("Chưa thiết lập loại hình chuyển kho hoặc xuất kho"))
        
        consignment_location = self.partner_id.consignment_location_id
        if not consignment_location:
            raise UserError(_("Vui lòng cấu hình kho ký gửi cho đối tác này."))

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
