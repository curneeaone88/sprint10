# -*- coding: utf-8 -*-
# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# Copyright 2016 Acsone SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from datetime import datetime

from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp
from odoo import _, api, exceptions, fields, models


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('pending', 'Pending'),
        ('cancel', 'Cancelled')])

    # Action button pending PO / RFQ
    @api.multi
    def action_pending(self):
        self.state = 'pending'

    # Action button continue order PO / RFQ
    @api.multi
    def action_back_to_rfq(self):
        self.state = 'draft'


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # x_category = fields.Float(related='product_uom.factor_inv')
    x_qty_meterpersegi_po = fields.Float(string = 'Quantity (m2)', compute = '_compute_qty_m2', store = True)
    x_harga_meterpersegi = fields.Float(string = 'Unit Price (m2)')
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'), compute = '_compute_unit_price', store = True)

    x_dudedate = fields.Datetime(string='Duedate')
    x_bahan = fields.Char(string='Bahan') #related='product_id.x_bahan')
    x_bentuk = fields.Char(string='Bentuk') #related='product_id.x_finishing')
    x_sts_repeat = fields.Char(string='Is New')
    x_ukuran = fields.Char(string='Ukuran')
    x_finishing = fields.Char(string='Finishing')
    x_no_so = fields.Many2one("sale.order", string="SO Number")

    purchase_request_lines = fields.Many2many(
            'purchase.request.line',
            'purchase_request_purchase_order_line_rel',
            'purchase_order_line_id',
            'purchase_request_line_id',
            'Purchase Request Lines', readonly=True, copy=False)
    x_quo_purchase_m2 = fields.Float('Purchase Price / m2', readonly=True)
    x_quo_purchase_price_pcs = fields.Float('Purchase Price / PCS', readonly=True)

    @api.one
    @api.depends('x_harga_meterpersegi', 'product_id', 'x_qty_meterpersegi_po', 'product_qty')
    def _compute_unit_price(self):
        qty_m2 = self. x_qty_meterpersegi_po
        unit_price_m2 = self.x_harga_meterpersegi
        qty_pcs = self.product_qty
        product_id = self.product_id

        product = self.env['product.product'].search([('id', '=', product_id.id)])
        if product:
            for row in product:
                if row.categ_id.x_price_m2 == True:
                    price_unit = (unit_price_m2 * qty_m2)/qty_pcs
                    self.price_unit = price_unit
                else:
                    self.price_unit = unit_price_m2

    @api.one
    @api.depends('product_qty', 'product_id')
    def _compute_qty_m2(self):
        quantity = self.product_qty
        product_id = self.product_id

        # pembagi = 0.7
        # Ammar ubah 22-Okt-2021
        # sesuai permintaan, jika item digital dibagi 0,7
        # Jika internal category item name prd dibagi 0,8
        product = self.env['product.product'].search([('id', '=', product_id.id)])
        if "PRD" in str(product.categ_id.parent_id.name).upper():
            if "STC DIGITAL" in str(product.categ_id.name).upper():
                pembagi = 0.7
            else:
                pembagi = 0.8

            for row in product:
                lenght = row.x_length / 1000
                width = row.x_width / 1000

                meter_persegi = (lenght * quantity * width) / pembagi
                self.x_qty_meterpersegi_po = round(meter_persegi, 2)

    @api.multi
    def action_openRequestLineTreeView(self):
        """
        :return dict: dictionary value for created view
        """
        request_line_ids = []
        for line in self:
            request_line_ids += line.purchase_request_lines.ids

        domain = [('id', 'in', request_line_ids)]

        return {'name': _('Purchase Request Lines'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.request.line',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': domain}
