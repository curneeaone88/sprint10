# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductionOkShortageWizard(models.TransientModel):
    """Muncul otomatis (popup) begitu Supervisor/Manager memvalidasi OK Done
    (lihat lpj.production.ok.action_validate_done) tapi Qty Production
    ternyata kurang dari Qty Plan. SPV memilih salah satu:
    - Buat OK Susulan: OK baru untuk SO Line yang sama, Qty Plan = sisa
      kekurangan, Order Type otomatis 'Repeat' (artwork sudah ACC dari OK
      induk, tidak perlu proses desain ulang).
    - Tutup SO (Tidak Ada Susulan): SO Line ditandai selesai meski qty
      kurang -- dicatat di sale.order.line.production_closed.
    """
    _name = 'lpj.production.ok.shortage.wizard'
    _description = 'Wizard OK Susulan (Qty Kurang dari Plan)'

    ok_id = fields.Many2one('lpj.production.ok', string='Order Kerja', required=True)
    qty_plan = fields.Float(related='ok_id.qty_plan', readonly=True, string='Qty Plan')
    qty_production = fields.Float(related='ok_id.qty_production', readonly=True, string='Qty Production')
    qty_shortage = fields.Float(compute='_compute_qty_shortage', string='Sisa Kekurangan (pcs)')

    @api.multi
    @api.depends('ok_id.qty_plan', 'ok_id.qty_production')
    def _compute_qty_shortage(self):
        for rec in self:
            rec.qty_shortage = (rec.ok_id.qty_plan or 0.0) - (rec.ok_id.qty_production or 0.0)

    @api.multi
    def action_create_followup(self):
        self.ensure_one()
        ok = self.ok_id
        new_ok = self.env['lpj.production.ok'].create({
            'sale_order_line_id': ok.sale_order_line_id.id,
            'parent_ok_id': ok.id,
            'qty_plan': self.qty_shortage,
            'routing_id': ok.routing_id.id,
            'order_type': 'repeat',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('OK Susulan'),
            'res_model': 'lpj.production.ok',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': new_ok.id,
        }

    @api.multi
    def action_close_so(self):
        self.ensure_one()
        self.ok_id.sale_order_line_id.production_closed = True
        self.ok_id.message_post(body=_(
            "Qty Production (%s pcs) kurang dari Qty Plan (%s pcs). "
            "Supervisor memutuskan SO Line ini ditutup tanpa OK susulan."
        ) % (self.qty_production, self.qty_plan))
        return {'type': 'ir.actions.act_window_close'}
