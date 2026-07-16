# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleProformaInvoiceWizard(models.TransientModel):
    _name = 'sale.proforma.invoice.wizard'
    _description = 'Wizard Cetak Proforma Invoice'

    order_id = fields.Many2one('sale.order', string='Sales Order', required=True)

    proforma_no = fields.Char(string='Nomor PI', required=True,
                               help="Nomor Proforma Invoice, contoh: 0625/PI-SPRINT/VI/26")
    proforma_date = fields.Date(string='Tanggal PI', default=fields.Date.context_today, required=True)

    sph_no = fields.Char(string='No. SPH')
    tanggal_po = fields.Date(string='Tanggal PO')

    # 1. Fix amount DP diinput manual oleh user
    dp_amount = fields.Float(string='Nilai DP (Fix Amount)', required=True)

    # 2. PPN diambil dari master account.tax (Odoo standar)
    tax_id = fields.Many2one(
        'account.tax', string='PPN',
        domain=[('type_tax_use', '=', 'sale')],
        required=True,
    )

    # 3. Preview hasil hitungan sebelum cetak
    order_total = fields.Float(string='Total SO', compute='_compute_amounts')
    dp_tax_amount = fields.Float(string='PPN atas DP', compute='_compute_amounts')
    total_dp_payment = fields.Float(string='Total Pembayaran DP', compute='_compute_amounts')

    @api.depends('dp_amount', 'tax_id', 'order_id')
    def _compute_amounts(self):
        for rec in self:
            rec.order_total = rec.order_id.amount_total if rec.order_id else 0.0
            tax_amount = 0.0
            if rec.tax_id and rec.dp_amount:
                res = rec.tax_id.compute_all(rec.dp_amount, quantity=1.0)
                tax_amount = sum(t['amount'] for t in res.get('taxes', []))
            rec.dp_tax_amount = tax_amount
            rec.total_dp_payment = rec.dp_amount + tax_amount

    @api.model
    def default_get(self, fields_list):
        res = super(SaleProformaInvoiceWizard, self).default_get(fields_list)

        order = False
        order_id = res.get('order_id') or self.env.context.get('default_order_id') or self.env.context.get(
            'active_id')
        if order_id and self.env.context.get('active_model', 'sale.order') == 'sale.order':
            order = self.env['sale.order'].browse(order_id)

        if order and order.exists():
            res['order_id'] = order.id

            # Auto-isi No. SPH: coba ambil dari SQ pada order line, fallback ke client_order_ref/nomor SO
            sph_no = order.client_order_ref or order.name
            for line in order.order_line:
                sq = getattr(line, 'x_sq', False)
                if sq and sq.name:
                    sph_no = sq.name
                    break
            res['sph_no'] = sph_no

            # Auto-isi Tanggal PO dari tanggal order (silakan diedit manual jika beda)
            if order.date_order:
                res['tanggal_po'] = order.date_order[:10]

            # Default nomor PI kosong -> user isi manual, PPN default cari tarif 11% jika ada
            default_tax = self.env['account.tax'].search(
                [('type_tax_use', '=', 'sale'), ('amount', '=', 11)], limit=1)
            if default_tax:
                res['tax_id'] = default_tax.id

        return res

    @api.multi
    def action_print_proforma(self):
        self.ensure_one()
        if not self.order_id.order_line:
            raise UserError(_('Sales Order tidak memiliki item, tidak bisa mencetak Proforma Invoice.'))
        if self.dp_amount <= 0:
            raise UserError(_('Nilai DP harus lebih besar dari 0.'))
        return self.env.ref('sp_sale_proforma.action_report_proforma_invoice').report_action(self)

