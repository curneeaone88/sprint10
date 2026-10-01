# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    x_default_routing_id = fields.Many2one(
        'lpj.routing', string='Default Routing Produksi',
        help="Dipakai sebagai fallback kalau product-nya sendiri belum punya "
             "routing default.")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_default_routing_id = fields.Many2one(
        'lpj.routing', string='Default Routing Produksi',
        help="Routing yang otomatis dipakai saat PPIC membuat OK untuk produk ini. "
             "Kalau kosong, sistem pakai default routing di Kategori Produk.")

    # x_length, x_width, x_bahan, x_diecut, x_satuan, x_type_roll SUDAH ADA
    # di product.template (didefinisikan lpj_product/models/models.py) --
    # tidak didefinisikan ulang di sini, cukup dipakai sebagai sumber default
    # untuk Data Forms OK (lihat production_ok.py: create()).
    #
    # Diecut Code & Hotprint Code BELUM ADA di master product -- baru
    # ditambahkan di sini sesuai permintaan.
    x_diecut_code = fields.Char(string='Diecut Code')
    x_hotprint_code = fields.Char(string='Hotprint Code')

    x_can_be_production = fields.Boolean(
        string='Bisa Produksi', default=False,
        help="Dicentang oleh tim Desain setelah Routing, Layout, dan BOM produk "
             "ini selesai dilengkapi. Tab 'Layout & Bahan Baku' baru muncul "
             "setelah ini dicentang, dan OK baru bisa dibuat untuk produk ini "
             "kalau sudah dicentang (lihat action_create_ok di sale_order_extend.py).")

    # ==== Layout (untuk hitung m2 riil berbasis Meter Lari, bukan L x W x Qty) ====
    x_layout_qty_pcs = fields.Integer(
        string='Qty per Layout',
        help="Berapa pcs sticker/produk muat dalam satu bentangan layout cetak.")
    x_layout_width = fields.Float(
        string='Lebar Kertas (cm)', default=33.0,
        help="Lebar roll kertas yang dipakai -- default 33cm sesuai standar Sprint, "
             "bisa di-override kalau ada produk yang pakai lebar lain.")
    x_layout_length = fields.Float(
        string='Panjang per Layout (cm)',
        help="Panjang kertas (cm) untuk SATU layout -- tetap, dipakai ulang untuk "
             "order apa pun dari produk ini (tim desain desain sekali, dipakai berulang).")

    bom_line_ids = fields.One2many(
        'lpj.product.bom.line', 'product_tmpl_id', string='Bahan Baku (BOM)',
        help="Daftar bahan baku sederhana yang dipakai produk ini, dipakai untuk "
             "hitung konsumsi bahan & auto stock.picking saat OK divalidasi Done.")

    @api.multi
    def get_default_routing(self):
        """Helper dipanggil saat create OK: product dulu, fallback ke kategori."""
        self.ensure_one()
        if self.x_default_routing_id:
            return self.x_default_routing_id
        if self.categ_id and self.categ_id.x_default_routing_id:
            return self.categ_id.x_default_routing_id
        return self.env['lpj.routing']

    @api.multi
    def get_ok_dataform_defaults(self):
        """Nilai default untuk tab 'Data Forms' pada OK, diambil dari master
        product -- dipanggil dari lpj.production.ok.create()."""
        self.ensure_one()
        return {
            'x_length': self.x_length,
            'x_width': self.x_width,
            'x_material_id': self.x_bahan.id if self.x_bahan else False,
            'x_satuan': self.x_satuan,
            'x_type_roll_id': self.x_type_roll.id if self.x_type_roll else False,
            'x_diecut_id': self.x_diecut.id if self.x_diecut else False,
            'x_diecut_code': self.x_diecut_code,
            'x_hotprint_code': self.x_hotprint_code,
            'x_feature_ids': [(6, 0, self.x_feature.ids)],
        }
