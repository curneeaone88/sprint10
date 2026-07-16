# -*- coding: utf-8 -*-

from odoo import models, api, _


class SaleOrderProforma(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_open_proforma_wizard(self):
        """Buka popup wizard untuk input DP & PPN sebelum cetak Proforma Invoice."""
        self.ensure_one()
        return {
            'name': _('Cetak Proforma Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.proforma.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }

