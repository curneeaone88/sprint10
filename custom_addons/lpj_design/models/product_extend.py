# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
        string='Bisa Produksi', default=False, copy=False,
        help="Data desain produk sudah lengkap (Routing dan Layout). Otomatis tercentang. "
             "Tidak dicentang manual: diset otomatis saat SO confirm atau lewat tombol "
             "'Tandai Data Lengkap' (di form produk atau di Kanban Desain), "
             "yang memeriksa kelengkapannya dulu. OK baru bisa dibuat untuk "
             "item SO dari produk yang sudah Bisa Produksi.")
    x_design_missing = fields.Char(
        string='Data yang Belum Lengkap', compute='_compute_x_design_missing',
        help="Daftar data desain yang masih kosong: Routing, Layout.")

    # ==== Layout (untuk hitung m2 riil berbasis Meter Lari, bukan L x W x Qty) ====
    x_layout_qty_pcs = fields.Integer(
        string='Qty per Layout',
        help="Berapa pcs sticker/produk muat dalam satu bentangan layout cetak.")
    x_layout_width = fields.Float(
        string='Lebar Kertas (mm)', default=330.0,
        help="Lebar roll kertas yang dipakai, dalam MM -- default 330mm (33cm) "
             "sesuai standar Sprint, bisa di-override kalau ada produk yang "
             "pakai lebar lain.")
    x_layout_length = fields.Float(
        string='Panjang per Layout (mm)',
        help="Panjang kertas (dalam MM) untuk SATU layout -- tetap, dipakai "
             "ulang untuk order apa pun dari produk ini (tim desain desain "
             "sekali, dipakai berulang).")

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

    @api.multi
    def _get_design_missing(self):
        """List nama data desain yang belum lengkap untuk produk ini."""
        self.ensure_one()
        missing = []
        if not self.get_default_routing():
            missing.append(_("Routing"))
        if not (self.x_layout_qty_pcs and self.x_layout_width and self.x_layout_length):
            missing.append(_("Layout"))
        return missing

    @api.multi
    @api.depends('x_default_routing_id', 'categ_id.x_default_routing_id',
                 'x_layout_qty_pcs', 'x_layout_width', 'x_layout_length')
    def _compute_x_design_missing(self):
        for rec in self:
            rec.x_design_missing = u', '.join(rec._get_design_missing())

    @api.multi
    def action_mark_design_complete(self):
        """Tim Desain menandai data produk lengkap. Diperiksa dulu (Routing,
        Layout), baru Bisa Produksi dicentang otomatis dan semua item SO
        (yang punya SQ) untuk produk ini ikut berstatus Selesai di Kanban
        Desain."""
        for rec in self:
            missing = rec._get_design_missing()
            if missing:
                raise UserError(_(
                    "Data produk '%s' belum lengkap: %s. Lengkapi dulu di "
                    "Master Product."
                ) % (rec.display_name, u', '.join(missing)))
            rec.sudo().write({'x_can_be_production': True})
        rec_ids = self.ids
        lines = self.env['sale.order.line'].sudo().search([
            ('product_id.product_tmpl_id', 'in', rec_ids),
            ('x_design_status', 'in', ['outstanding', 'in_progress'])])
        lines.with_context(design_status_internal=True).write(
            {'x_design_status': 'done'})
        return True

    @api.multi
    def action_reopen_design(self):
        """Buka kembali data desain (mis. ada revisi BOM/routing). Item SO
        yang berstatus Selesai dan BELUM punya OK kembali ke Sedang
        Dikerjakan, supaya OK tidak bisa dibuat sebelum desain selesai lagi."""
        self.sudo().write({'x_can_be_production': False})
        lines = self.env['sale.order.line'].sudo().search([
            ('product_id.product_tmpl_id', 'in', self.ids),
            ('x_design_status', '=', 'done')])
        for line in lines:
            if 'ok_ids' in line._fields and line.ok_ids:
                continue  # sudah punya OK, jangan diutak-atik
            line.with_context(design_status_internal=True).write(
                {'x_design_status': 'in_progress'})
        return True
