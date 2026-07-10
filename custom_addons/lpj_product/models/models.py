# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp

class data_form(models.Model):
    _inherit = 'product.template'

    can_be_expensed = fields.Boolean(help="Specify whether the product can be selected in an HR expense.", string="Can be Expensed")
    x_customer = fields.Many2one('res.partner', string='Customer/Supplier', domain=['|', ('customer', '=', True), ('supplier', '=', True)], track_visibility='onchange')
    x_length = fields.Float('Length (mm)', track_visibility='onchange')
    x_width = fields.Float('Width (mm)', track_visibility='onchange')
    # x_material = fields.Many2one('x.config.material', string='Material')
    x_bahan = fields.Many2one('x.config.bahan', string='Material')
    x_bentuk = fields.Many2one('x.config.bentuk', string='Bentuk')
    x_diecut = fields.Many2one('x.config_diecut', string='Diecut')
    x_finishing = fields.Many2one('x.config_finishing', string='Finishing')
    x_finishing_2 = fields.Many2one('x.config_finishing', string='Finishing 2')
    x_feature = fields.Many2many('x.feature.cost.precost', string='Feature')
    x_offering = fields.Many2one('x.offering.cost.precost', string='Offering')
    x_satuan = fields.Selection([('roll', 'Roll Standard'), ('rollc', 'Roll Custom'), ('sheet', 'Sheet - Kisscut Standard'), ('sheetfs', 'Sheet - Fullcut Standard')
                                    , ('sheetfc', 'Sheet - Fullcut Custom'), ('sheetkc', 'Sheet - Kisscut Custom')], string='Satuan',
                                Default='sheet')
    x_product_list_layout = fields.Text('List Product in Layout')
    x_variant_sku_prd = fields.Char(string='Jumlah Variant (SKU)')
    x_type_roll = fields.Many2one('x.config_typeroll_product',string='Type Roll')
