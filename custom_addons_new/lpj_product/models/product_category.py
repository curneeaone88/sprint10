import subprocess
import odoo.addons.decimal_precision as dp

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError



class ProductCategory_msr(models.Model):
    _inherit = 'product.category'

    sts_bhn_utama = fields.Many2one('x.tipe.bahan',string="Component Type", help="Field ini digunakan untuk perhitungan "
                                                                                    "1. Qty Max OK. "
                                                                                    "2. Domain untuk product OK (Tinta, PLDC, Bahan Utama).", default='1')
    x_kode_item = fields.Char(string="Kode Item")
    x_sequence = fields.Many2one('ir.sequence', string='Sequence')
    x_price_m2 = fields.Boolean(string='Unit Price (m2)')

class Product_Categories_msr(models.Model):
     _name = 'x.tipe.bahan'

     name = fields.Char(string="Keterangan")