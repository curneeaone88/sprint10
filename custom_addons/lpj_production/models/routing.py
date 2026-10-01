# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LpjRouting(models.Model):
    """Master Routing Produksi -- CUSTOM, tidak reuse mrp.routing.

    Kenapa custom: di mrp.routing.workcenter (bawaan Odoo) field
    workcenter_id WAJIB diisi mesin spesifik. Padahal yang kita mau di
    level Master Routing cukup KATEGORI tahapan (lpj.workcenter.group) --
    mesin spesifiknya baru dipilih PPIC/operator belakangan saat OK
    dibuat/dikonfirmasi, difilter sesuai kategori itu.
    """
    _name = 'lpj.routing'
    _description = 'Master Routing Produksi'
    _order = 'name'

    name = fields.Char(string='Nama Routing', required=True)
    code = fields.Char(string='Kode')
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('lpj.routing.line', 'routing_id', string='Tahapan')
    line_count = fields.Integer(compute='_compute_line_count', string='Jumlah Tahapan')
    routing_display = fields.Char(compute='_compute_line_count', string='Ringkasan')

    @api.multi
    def _compute_line_count(self):
        for rec in self:
            lines = rec.line_ids.sorted(key=lambda l: l.sequence)
            rec.line_count = len(lines)
            rec.routing_display = u' \u2192 '.join(lines.mapped('workcenter_group_id.name'))

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Kode routing sudah dipakai.'),
    ]


class LpjRoutingLine(models.Model):
    """Satu baris Operation pada Master Routing -- cuma nunjuk ke KATEGORI
    tahapan (lpj.workcenter.group), bukan mesin spesifik."""
    _name = 'lpj.routing.line'
    _description = 'Tahapan pada Master Routing'
    _order = 'routing_id, sequence, id'

    routing_id = fields.Many2one(
        'lpj.routing', string='Master Routing', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Urutan', default=10)
    workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Kategori Tahapan', required=True,
        help="Kategori mesin untuk Operation ini, mis. Cetak. Mesin spesifik "
             "(Master Mesin) dipilih PPIC/operator saat OK dibuat, difilter "
             "otomatis sesuai kategori ini.")
