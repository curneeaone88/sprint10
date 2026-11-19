# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderDesign(models.Model):
    """Begitu SO di-confirm, tiap item yang punya SQ otomatis masuk antrean
    tim Desain (status Outstanding), kecuali data produknya sudah lengkap
    (mis. repeat order) -- langsung Selesai. Item tanpa SQ (mis. jasa
    pengiriman) tidak ikut alur desain sama sekali."""
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super(SaleOrderDesign, self).action_confirm()
        self.mapped('order_line')._init_design_status()
        return res


class SaleOrderLineDesign(models.Model):
    _inherit = 'sale.order.line'

    x_design_status = fields.Selection([
        ('na', 'Tidak Perlu Desain'),
        ('outstanding', 'Outstanding'),
        ('in_progress', 'Sedang Dikerjakan'),
        ('done', 'Selesai'),
    ], string='Status Desain', default='na', copy=False, index=True,
       help="Status kelengkapan data produk (Routing, Layout) oleh tim "
            "Desain untuk item SO yang punya SQ. OK hanya bisa dibuat kalau "
            "statusnya Selesai. Diubah lewat tombol di Kanban Desain, bukan "
            "digeser manual.")
    x_design_missing = fields.Char(
        string='Data yang Belum Lengkap',
        related='product_id.product_tmpl_id.x_design_missing', readonly=True)
    x_so_confirm_date = fields.Datetime(
        related='order_id.confirmation_date', string='Tgl Konfirmasi SO',
        store=True, readonly=True,
        help="Dipakai untuk mengurutkan Kanban Desain: yang paling lama "
             "dikonfirmasi ada di atas.")
    x_design_customer_id = fields.Many2one(
        'res.partner', related='order_id.partner_id', string='Customer',
        readonly=True)

    # ==== Penentuan status awal ====

    @api.multi
    def _init_design_status(self):
        """Dipanggil saat SO confirm / baris baru ditambah ke SO yang sudah
        confirm. Hanya menyentuh baris yang masih 'na' dan punya SQ."""
        for line in self.filtered(lambda l: l.x_design_status == 'na'
                                  and l.x_sq and l.product_id
                                  and not l.qty_delivered):
            tmpl = line.product_id.product_tmpl_id
            if not tmpl._get_design_missing():
                # Routing & Layout sudah ada: otomatis Bisa Produksi + Selesai
                if not tmpl.x_can_be_production:
                    tmpl.sudo().write({'x_can_be_production': True})
                status = 'done'
            else:
                status = 'outstanding'
            line.sudo().with_context(design_status_internal=True).write(
                {'x_design_status': status})

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        """Urutan kolom Kanban Desain: Outstanding, Sedang Dikerjakan, Selesai
        (bukan urutan abjad nilai di database)."""
        res = super(SaleOrderLineDesign, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy)
        first = groupby[0] if isinstance(groupby, (list, tuple)) and groupby else groupby
        if first == 'x_design_status':
            order = ['na', 'outstanding', 'in_progress', 'done']

            def _key(g):
                v = g.get('x_design_status')
                v = v[0] if isinstance(v, (list, tuple)) else v
                return order.index(v) if v in order else len(order)
            res = sorted(res, key=_key)
        return res

    @api.model
    def create(self, vals):
        line = super(SaleOrderLineDesign, self).create(vals)
        if line.order_id.state in ('sale', 'done'):
            line._init_design_status()
        return line

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('design_board') and not order:
            order = 'x_so_confirm_date asc, id asc'
        return super(SaleOrderLineDesign, self).search(
            args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def write(self, vals):
        if 'x_design_status' in vals and not self.env.context.get('design_status_internal'):
            raise UserError(_(
                "Status Desain tidak bisa diubah manual atau digeser di "
                "Kanban. Gunakan tombol Mulai atau Selesai pada kartunya."))
        return super(SaleOrderLineDesign, self).write(vals)

    # ==== Aksi dari Kanban Desain ====

    @api.multi
    def action_design_start(self):
        lines = self.filtered(lambda l: l.x_design_status == 'outstanding')
        lines.sudo().with_context(design_status_internal=True).write(
            {'x_design_status': 'in_progress'})
        return True

    @api.multi
    def action_design_open_product(self):
        self.ensure_one()
        # Sekalian tandai Sedang Dikerjakan kalau masih Outstanding.
        self.action_design_start()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Master Product'),
            'res_model': 'product.template',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.product_id.product_tmpl_id.id,
            'target': 'current',
        }

    @api.multi
    def action_design_done(self):
        """Validasi kelengkapan lewat produknya, lalu semua item SO dari
        produk yang sama ikut Selesai."""
        for line in self:
            line.product_id.product_tmpl_id.action_mark_design_complete()
        return True
