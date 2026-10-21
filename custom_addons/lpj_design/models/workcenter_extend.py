# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    """mrp.workcenter dipakai sebagai master mesin fisik individual
    (Master Mesin), dikaitkan ke kategori proses (lpj.workcenter.group)
    lewat x_workcenter_group_ids (Many2many: satu mesin bisa
    punya banyak kategori proses, mis. mesin yang bisa Cetak sekaligus Laminasi).

    Checklist QC TIDAK menempel di sini -- ada di level kategori
    (lpj.workcenter.group), supaya tidak perlu isi ulang aktivitas QC yang
    sama untuk tiap mesin sejenis (lihat qc_item_template.py).

    Reuse model inti mrp supaya tidak bikin master mesin dari nol, TANPA
    memakai alur MRP/Manufacturing Order.
    """
    _inherit = 'mrp.workcenter'

    x_workcenter_group_ids = fields.Many2many(
        'lpj.workcenter.group', 'lpj_workcenter_group_mrp_workcenter_rel',
        'workcenter_id', 'group_id', string='Kategori Proses',
        help="Kategori proses yang bisa dikerjakan mesin ini. Satu mesin boleh "
             "punya BANYAK kategori (mis. Cetak dan Laminasi), tidak terikat "
             "ke satu kategori saja. Dipakai sebagai domain filter saat PPIC "
             "memilih mesin di OK: mesin muncul untuk setiap kategori proses "
             "yang dicentang di sini. Aktivitas QC mengikuti kategori proses "
             "baris Routing, bukan mesinnya (lihat lpj.workcenter.group).")
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
