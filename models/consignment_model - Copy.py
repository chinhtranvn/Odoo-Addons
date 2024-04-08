# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    consignment_location = fields.Many2one(
        'stock.location', 
        string='Consignment Location', 
        domain=[('usage', '=', 'internal')],
        help='The location used for consignment purposes.'
    )

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('consignment', 'Consignment Order')]
    )

    def action_confirm_consignment(self):
        self.ensure_one()
        self.write({'state': 'consignment'})
        self._create_consignment_stock_picking()

    def _create_consignment_stock_picking(self):
        StockPicking = self.env['stock.picking']
        StockPickingType = self.env['stock.picking.type']
        picking_type = StockPickingType.search([('code', '=', 'internal')], limit=1)
        consignment_location = self.partner_id.consignment_location

        _logger.info(f"Location ID: {self.warehouse_id.lot_stock_id.id}")
        _logger.info(f"Consignment Location ID: {consignment_location.id}")
        if consignment_location:
            picking_vals = {
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
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

            StockPicking.create(picking_vals)

    def action_cancel_consignment(self):
        self.ensure_one()
        self.write({'state': 'cancel'})
