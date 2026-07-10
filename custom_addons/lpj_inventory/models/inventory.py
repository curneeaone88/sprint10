# -*- coding: utf-8 -*-
import subprocess

from odoo import models, fields, api, _
import requests
import json
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class lot_barang(models.Model):
    _inherit = 'stock.picking'

    x_no_sj_internal = fields.Char(string="No SJ Internal", readonly=True)
    x_note_sjk = fields.Text(string="Note")
    x_sj_supplier = fields.Char(string="Nomor Surat Jalan Supplier")
    x_status_invoice = fields.Selection([('created','Created'),('none','Not Yet')],string='Status Invoice',readonly=True, default='none')

    @api.multi
    def push_invoice_jurnal(self):

        jurnal_api_key = "609a299b93e63dadacd05ca5b8b69532"
        headers = {
            'apikey': jurnal_api_key,
            'Content-Type': "application/json"
        }

        self.env.cr.execute(
            " select sp.name sjk,sp.min_date tgl_kirim, sls.so,sls.customer,sls.alamat,sls.email, \n"
            " sls.product, sm.product_uom_qty, sls.price_unit, sls.tax,sp.state ,sls.cus_jurnal, \n"
            " sls.phone, sls.mobile,sls.npwp, sls.cus_id,sls.sales \n "
            " from stock_picking sp  \n"
            " left join stock_move sm on sp.id = sm.picking_id \n"
            " left join ( select so.id soid,so.name so, so.procurement_group_id group_id, rp.id cus_id, \n"
            " rp.name customer, rp.x_name_jurnal cus_jurnal, rp.street alamat, rp.email, \n"
            " rp.phone, rp.mobile, rp.x_npwp npwp, \n"
            " sol.product_id,pt.name product, \n"
            " sol.price_unit,act.id idtax,act.name tax,rps.name sales \n"
            " from sale_order so  \n"
            " left join res_partner rp on so.partner_id = rp.id \n"
            " left join sale_order_line sol on so.id = sol.order_id \n"
            " left join product_product pp on sol.product_id = pp.id \n"
            " left join product_template pt on pp.product_tmpl_id = pt.id \n"
            " left join account_tax_sale_order_line_rel tx on sol.id = tx.sale_order_line_id  \n"
            " left join account_tax act on tx.account_tax_id = act.id \n"
            " left join res_users ru on so.user_id = ru.id \n"
			" left join res_partner rps on ru.partner_id = rps.id \n"
            " where so.state in ('done','sale')) sls on sm.group_id = sls.group_id and sm.product_id = sls.product_id \n"
            " where sp.picking_type_id = 4 and \n "
            " sm.picking_id = '" + str(self.id) + "' \n"
            " order by sp.min_date,sp.id desc ")
        sql = self.env.cr.fetchall()

        x_tgl_kirim = ""
        x_no_SJK = ""
        x_address = ""
        x_email = ""
        x_cusjurnalid = ""
        x_sales = ""

        dt_product = []

        if sql:
            for sjk in sql:
                x_tgl_kirim = datetime.strptime(sjk[1], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                # x_duedate_inv = (datetime.strptime(sjk[1], '%Y-%m-%d %H:%M:%S') + datetime.a  (days=7)).strftime('%Y-%m-%d')
                x_no_SJK = sjk[0]
                x_address = sjk[4]
                x_email = sjk[5]
                x_no_so = sjk[2]
                x_memo = sjk[2] + " , " + sjk[0]
                x_sales = sjk[16]


                if x_cusjurnalid == "":
                    x_cusjurnalid = sjk[11]

                if x_cusjurnalid ==  "" or x_cusjurnalid is None:
                    jurnal_api_url = "https://api.jurnal.id/core/api/v1/customers"
                    jurnal_data = {
                                      "customer": {
                                        "associate_company": sjk[3],
                                        "display_name": sjk[3],
                                        "address": sjk[4],
                                        # "email": sjk[5],
                                        "tax_no": 'null',
                                        "mobile": sjk[13],
                                        "phone": sjk[12],
                                        "disable_max_credit_limit": True,
                                        "deleted_at": 'null',
                                        "deletable": True,
                                        "editable": True,
                                        "has_transactions": True,
                                        "has_close_the_book": False,
                                        "source": 'null',
                                        "custom_id": sjk[15],
                                        "default_ar_account": {
                                          "id": 34106265,
                                          "name": "Piutang Usaha (Account Receivable)"
                                        },
                                        "default_ap_account": {
                                          "id": 34106264,
                                          "name": "Hutang Usaha Lokal (Account Payable)"
                                        }
                                      }
                                    }

                    #
                    response = requests.post(jurnal_api_url, data=json.dumps(jurnal_data), headers=headers)
                    x_cusjurnalid = sjk[3]
                    #
                    if response.status_code in (200, 201):
                        print("Panggilan API Jurnal.ID berhasil.")
                        self.env.cr.execute(" update res_partner set x_name_jurnal = '" + str(sjk[3]) + "' where id = '" + str(sjk[15]) + "'; ")
                        self.env.cr.commit()
                    else:
                        print("Panggilan API Jurnal.ID gagal. Kode status: {}".format(response.content))


                dt_product.append({
                    "quantity": sjk[7],
                    "rate": sjk[8],
                    "discount": 0,
                    "product_name": "STICKER",
                    "description": sjk[6],
                    "line_tax_id": 583130,
                    "line_tax_name": "PPN"
                })

        jurnal_api_url = "https://api.jurnal.id/core/api/v1/sales_invoices"
        jurnal_data = {
            "sales_invoice": {
                "transaction_date": x_tgl_kirim,
                "transaction_lines_attributes": dt_product,
                "shipping_date": x_tgl_kirim,
                "shipping_price": 0,
                "shipping_address": "Test Street",
                # "is_shipped": 'true',
                # "ship_via": "ship",
                "reference_no": x_no_so,
                "tracking_no": x_no_SJK,
                "address": x_address,
                # "term_name": "Cash on Delivery",
                "due_date": x_tgl_kirim,
                "person_name": x_cusjurnalid,
                "tags":[x_sales],
                # "email": x_email,
                "source": "ERP",
                "use_tax_inclusive": 'false',
                "memo": x_memo,
                # "credit_memos": x_no_SJK,
                "tax_after_discount": 'true'
            }
            # ...Tambahkan data lain yang diperlukan untuk Jurnal.ID...
        }

        # # print (json.dumps(jurnal_data))
        #
        response = requests.post(jurnal_api_url, data=json.dumps(jurnal_data), headers=headers)
        #
        if response.status_code in (200, 201):
            print("Panggilan API Jurnal.ID berhasil.")
            self.x_status_invoice = 'created'
            # self.push_invoice_jurnal.invisible = True
        else:
            print("Panggilan API Jurnal.ID gagal. Kode status: {}".format(response.content))


class stock_line(models.Model):
    _inherit = 'stock.pack.operation'

    x_weight = fields.Float(string='Total Weight (Kg)')
    x_qty_total = fields.Float(string='Qty Total (Roll/Sheet)')
    x_note = fields.Char(string='Description')
    x_picking_type_id = fields.Integer(string='Picking Type')
