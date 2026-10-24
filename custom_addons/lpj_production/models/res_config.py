# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_ok_ref_days = fields.Integer(
        string='Hari Referensi Kirim', default=7,
        help="Jumlah hari dari tanggal SO di-confirm untuk menghitung "
             "Tanggal Referensi Kirim di Order Kerja.")


class ResConfigSettings(models.TransientModel):
    # Pola get_default_/set_ sama seperti di lpj_design (tanpa related company_id).
    _inherit = 'res.config.settings'

    x_ok_ref_days = fields.Integer(string='Hari Referensi Kirim')

    @api.model
    def get_default_x_ok_ref_days(self, fields_list):
        return {'x_ok_ref_days': self.env.user.company_id.x_ok_ref_days}

    @api.multi
    def set_x_ok_ref_days(self):
        for rec in self:
            self.env.user.company_id.sudo().write(
                {'x_ok_ref_days': max(rec.x_ok_ref_days, 0)})
