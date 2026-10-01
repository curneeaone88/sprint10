# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_allow_negative_stock_production = fields.Boolean(
        string='Izinkan Stok Minus saat Transfer Bahan Produksi', default=True,
        help="Kalau AKTIF: stock.picking bahan baku tetap dibuat & divalidasi "
             "meski stok tidak cukup (bisa minus), dan sistem mencatat "
             "reminder di chatter OK. Kalau NONAKTIF: validasi Done OK "
             "diblokir sampai stok bahan dicukupi.")


class ResConfigSettings(models.TransientModel):
    """PENTING: sengaja TIDAK pakai related='company_id...' -- di instalasi
    Odoo 10 Anda, res.config.settings bawaan ternyata tidak selalu punya
    field company_id siap pakai (beda dari versi yang lebih baru), jadi
    related field gagal resolve saat startup (KeyError: 'company_id').

    Dipakai pola get_default_/set_ yang memang standar buat res.config.settings
    di Odoo 10 -- lebih verbose tapi tidak bergantung field company_id yang
    tidak pasti ada."""
    _inherit = 'res.config.settings'

    x_allow_negative_stock_production = fields.Boolean(
        string='Izinkan Stok Minus saat Transfer Bahan Produksi')

    @api.model
    def get_default_x_allow_negative_stock_production(self, fields_list):
        return {
            'x_allow_negative_stock_production':
                self.env.user.company_id.x_allow_negative_stock_production,
        }

    @api.multi
    def set_x_allow_negative_stock_production(self):
        for rec in self:
            self.env.user.company_id.write({
                'x_allow_negative_stock_production': rec.x_allow_negative_stock_production,
            })
