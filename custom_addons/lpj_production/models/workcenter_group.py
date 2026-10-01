# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WorkcenterGroup(models.Model):
    """Kategori/tag tahapan produksi. Dua fungsi:
    1. Dipasang di tiap Master Mesin (mrp.workcenter.x_workcenter_group_id),
       dipakai sebagai domain filter saat PPIC memilih mesin di OK.
    2. Tempat master aktivitas QC (lpj.qc.item.template) -- satu set aktivitas
       QC per kategori, dipakai bersama oleh semua mesin dengan kategori itu,
       supaya tidak perlu isi ulang checklist yang sama per mesin.
    """
    _name = 'lpj.workcenter.group'
    _description = 'Kategori Tahapan Produksi'
    _order = 'sequence, id'

    name = fields.Char(string='Nama Tahapan', required=True)
    code = fields.Char(string='Kode')
    sequence = fields.Integer(string='Urutan', default=10)
    active = fields.Boolean(default=True)
    is_material_consumption_stage = fields.Boolean(
        string='Sumber Konsumsi Bahan (Meter Lari)', default=False,
        help="Tandai untuk tahap yang Meter Lari-nya dipakai sebagai dasar "
             "hitung M2 Production riil & konsumsi bahan baku (biasanya "
             "tahap Cetak). OK Line dengan kategori ini dijumlah "
             "meter_lari-nya jadi Total Meter Lari OK.")
    x_input_mode = fields.Selection([
        ('qty_pcs', 'Qty Pcs (input langsung)'),
        ('meter_lari', 'Meter Lari (Qty Pcs dihitung otomatis dari Layout)'),
    ], string='Cara Input Hasil', default='qty_pcs', required=True,
       help="Menentukan cara operator mengisi hasil di baris Routing tahap ini. "
            "'Meter Lari' cocok untuk tahap berbasis roll (mis. Cetak) -- Qty "
            "Pcs otomatis tersaran dari Meter Lari x Layout produk. 'Qty Pcs' "
            "cocok untuk tahap yang hasilnya memang dihitung per pcs langsung "
            "(mis. Packing) -- operator isi Qty Pcs manual, tidak lewat Meter Lari.")

    workcenter_ids = fields.One2many(
        'mrp.workcenter', 'x_workcenter_group_id', string='Mesin',
        help="Mesin fisik (mrp.workcenter) dengan kategori ini -- inilah "
             "daftar yang muncul saat PPIC memilih mesin untuk Operation "
             "berkategori ini di OK.")
    workcenter_count = fields.Integer(compute='_compute_workcenter_count', string='Jumlah Mesin')

    qc_item_template_ids = fields.One2many(
        'lpj.qc.item.template', 'workcenter_group_id', string='Aktivitas QC',
        help="Aktivitas QC yang berlaku untuk SEMUA mesin di kategori ini.")
    qc_item_count = fields.Integer(compute='_compute_qc_item_count', string='Jumlah Aktivitas QC')

    @api.multi
    def _compute_workcenter_count(self):
        for rec in self:
            rec.workcenter_count = len(rec.workcenter_ids)

    @api.multi
    def _compute_qc_item_count(self):
        for rec in self:
            rec.qc_item_count = len(rec.qc_item_template_ids)

    @api.multi
    def action_view_workcenters(self):
        self.ensure_one()
        action = self.env.ref('lpj_production.action_mrp_workcenter_production').read()[0]
        action['domain'] = [('x_workcenter_group_id', '=', self.id)]
        action['context'] = {'default_x_workcenter_group_id': self.id}
        return action

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Kode tahapan sudah dipakai.'),
    ]
