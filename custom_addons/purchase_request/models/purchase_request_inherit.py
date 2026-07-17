# from mock.mock import self

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, time


class purchase_request_inherit(models.Model):
    _inherit = 'purchase.request'

    # Tambahan no-SO -Uswa
    x_no_so = fields.Many2one('sale.order', string="SO Number")

    # Function untuk flagging create PR
    @api.model
    def create(self, vals):

        # kasi if else

        res = super(purchase_request_inherit, self).create(vals)

        order_number = vals['x_no_so']

        if order_number:
            # Tambahan PR SO -Uswa

            # select from table berdasarkan id
            purchase_request = self.env['sale.order'].search([('id', '=', order_number)])
            # write di is_responsible
            purchase_request.write({'is_responsible': True})
            purchase_request.write({'x_status_pr': 'done'})

            # Automatically filled in line_ids sales order
            terms_obj = self.env['sale.order']
            terms = []
            astate = "New"
            termsids = terms_obj.search([('id', '=', order_number)])
            if termsids:
                for rec in termsids.order_line:
                    # cek jika ada new item di SO dan cek jika ada product internal category like %Delivery%
                    if "NEW ITEM" not in str(rec.product_id.name).upper():
                        if "DELIVERY" not in str(rec.product_id.categ_id.sts_bhn_utama.name).upper():
                            values = {}
                            values['product_id'] = rec.product_id
                            values['name'] = rec.product_id.name
                            values['product_uom_id'] = rec.product_uom
                            values['product_qty'] = rec.product_uom_qty

                            if rec.x_new_product == False:
                                astate = "Repeat"

                            values['x_pr_prdrepeat'] = astate
                            values['x_pr_ukuran'] = str(rec.x_panjang) + " x " + str(rec.x_lebar)
                            values['x_pr_panjang'] = rec.x_panjang
                            values['x_pr_lebar'] = rec.x_lebar
                            values['x_pr_bahan'] = rec.x_bahan.name
                            values['x_pr_finishing'] = rec.x_feature
                            values['x_internal_categ'] = rec.x_internal_categ.name
                            values['x_no_so'] = rec.order_id
                            values['x_quo_purchase_m2'] = rec.x_quo_purchase_m2
                            values['x_quo_purchase_price_pcs'] = rec.x_quo_purchase_price_pcs
                            terms.append((0, 0, values))

                res.update({'line_ids': terms})

        return res


class purchase_request_line(models.Model):
    _inherit = 'purchase.request.line'

    x_pr_prdrepeat = fields.Char(string="New/Repeat")
    x_pr_ukuran = fields.Char(string="Ukuran")
    x_pr_panjang = fields.Float(string="Panjang")
    x_pr_lebar = fields.Float(string="Lebar")
    x_pr_bahan = fields.Char(string="Bahan")
    x_pr_finishing = fields.Char(string="Finishing")
    x_internal_categ = fields.Char(string="Internal Category")
    x_no_so = fields.Many2one("sale.order", string="SO Number")
    x_quo_purchase_m2 = fields.Float('Purchase Price / m2', readonly=True)
    x_quo_purchase_price_pcs = fields.Float('Purchase Price / PCS', readonly=True)
