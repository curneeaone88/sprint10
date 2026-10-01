# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    """mrp.workcenter dipakai sebagai master mesin fisik individual
    (Master Mesin), dikaitkan ke kategori tahapan (lpj.workcenter.group)
    lewat x_workcenter_group_id.

    Checklist QC TIDAK menempel di sini -- ada di level kategori
    (lpj.workcenter.group), supaya tidak perlu isi ulang aktivitas QC yang
    sama untuk tiap mesin sejenis (lihat qc_item_template.py).

    Reuse model inti mrp supaya tidak bikin master mesin dari nol, TANPA
    memakai alur MRP/Manufacturing Order.
    """
    _inherit = 'mrp.workcenter'

    x_workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Kategori Tahapan',
        help="Kategori tahapan mesin ini, mis. Mesin Cetak 1 -> kategori Cetak. "
             "Dipakai sebagai domain filter saat PPIC memilih mesin di OK, dan "
             "menentukan aktivitas QC yang berlaku (lihat lpj.workcenter.group).")
    x_code = fields.Char(string='Kode Mesin')
    x_description = fields.Text(string='Deskripsi')
    x_capacity_qty = fields.Float(string='Kapasitas')
    x_capacity_uom = fields.Selection([
        ('m2', 'M2 / Hari'),
        ('pcs', 'PCS / Hari'),
    ], string='Satuan Kapasitas', default='m2')
    x_default_priority = fields.Integer(
        string='Prioritas Default', default=10,
        help="Dipakai untuk pemilihan mesin default saat OK dibuat (Proyek 1). "
             "Angka lebih kecil = prioritas lebih tinggi. "
             "Auto-balancing berdasarkan beban kapasitas menyusul di Proyek 2.")
    x_active_production = fields.Boolean(string='Aktif untuk Produksi', default=True)
