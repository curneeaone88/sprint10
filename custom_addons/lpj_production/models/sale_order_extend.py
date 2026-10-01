# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderExtendProduction(models.Model):
    """Smart button 'Order Kerja' di form SO, sesuai screenshot mockup Anda
    (tombol 'Order Kerja' di header form Sales Order) -- memudahkan tim sales
    memonitor proses produksi langsung dari SO tanpa pindah layar."""
    _inherit = 'sale.order'

    ok_ids = fields.One2many(
        'lpj.production.ok', 'sale_order_id', string='Order Kerja')
    ok_count = fields.Integer(compute='_compute_ok_count', string='Jumlah OK')

    @api.multi
    def _compute_ok_count(self):
        for rec in self:
            rec.ok_count = len(rec.ok_ids)

    @api.multi
    def action_view_ok(self):
        self.ensure_one()
        action = self.env.ref('lpj_production.action_production_ok').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {
            'default_sale_order_id': self.id,
        }
        return action


class SaleOrderLineExtendProduction(models.Model):
    """Tombol 'Create OK' per baris SO (lihat mockup daftar SO -> tombol
    Create OK di kolom paling kanan)."""
    _inherit = 'sale.order.line'

    ok_ids = fields.One2many(
        'lpj.production.ok', 'sale_order_line_id', string='Order Kerja')
    ok_count = fields.Integer(compute='_compute_ok_count', string='Jumlah OK')

    # Related fields dipakai di menu "Planning Order Kerja" (views/planning_view.xml)
    order_partner_id = fields.Many2one(
        'res.partner', related='order_id.partner_id', store=True, string='Customer')
    order_salesperson_id = fields.Many2one(
        'res.users', related='order_id.user_id', store=True, string='Sales')
    order_confirm_date = fields.Datetime(
        related='order_id.x_confirm_date', store=True, string='Confirmation Date')
    production_closed = fields.Boolean(
        string='Produksi Ditutup', copy=False,
        help="Ditandai otomatis kalau Supervisor Produksi memutuskan "
             "menutup SO Line ini meski Qty Production dari OK terakhir "
             "kurang dari Qty Plan (tidak dibuatkan OK susulan). Lihat "
             "lpj.production.ok.shortage.wizard.")

    @api.multi
    def _compute_ok_count(self):
        for rec in self:
            rec.ok_count = len(rec.ok_ids)

    @api.multi
    def action_create_ok(self):
        """Buat OK baru untuk baris SO ini. Routing default diambil dari
        product (fallback ke kategori produk) -- lihat product_extend.py.

        WAJIB: produk sudah ditandai 'Bisa Produksi', dan Routing & Layout-nya
        harus sudah terisi -- kalau belum, diblokir dengan reminder supaya
        PPIC menghubungi tim Desain, bukan bikin OK dengan data tidak lengkap."""
        self.ensure_one()
        product_tmpl = self.product_id.product_tmpl_id

        if not product_tmpl.x_can_be_production:
            raise UserError(_(
                "Produk '%s' belum ditandai 'Bisa Produksi'. Data Routing, "
                "Layout, dan Bahan Baku (BOM) untuk produk ini kemungkinan "
                "belum lengkap. Hubungi tim Desain untuk melengkapi data "
                "produksi produk ini sebelum OK bisa dibuat."
            ) % product_tmpl.display_name)

        routing = product_tmpl.get_default_routing()
        missing = []
        if not routing:
            missing.append(_("Routing"))
        if not (product_tmpl.x_layout_qty_pcs and product_tmpl.x_layout_width
                and product_tmpl.x_layout_length):
            missing.append(_("Layout"))
        if missing:
            raise UserError(_(
                "Produk '%s' sudah ditandai 'Bisa Produksi', tapi %s belum "
                "diisi lengkap di Master Product. Hubungi tim Desain untuk "
                "melengkapi data ini sebelum OK bisa dibuat."
            ) % (product_tmpl.display_name, ' & '.join(missing)))

        vals = {
            'sale_order_line_id': self.id,
            'routing_id': routing.id,
        }
        ok = self.env['lpj.production.ok'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Kerja'),
            'res_model': 'lpj.production.ok',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': ok.id,
        }
