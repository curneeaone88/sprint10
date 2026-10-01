# -*- coding: utf-8 -*-
from odoo import models, fields, api


class QcItemTemplate(models.Model):
    """Master AKTIVITAS QC per KATEGORI TAHAPAN (bukan per mesin individual,
    dan bukan produk/barang) -- supaya tidak perlu isi checklist yang sama
    berulang-ulang untuk tiap mesin dalam satu kategori. Semua mesin dengan
    kategori yang sama otomatis pakai aktivitas QC yang sama.

    Mengikuti persis form checklist kertas yang sudah berjalan (Bagian 3.4
    PRD). Contoh untuk kategori Cetak: Cek Warna, Cek Konten Desain, Cek
    Bleeding, Cek Layout, dst.

    Saat operator mengisi checklist, teks aktivitas ini di-copy (snapshot)
    ke lpj.production.qc.checklist.item.name supaya histori checklist tidak
    berubah kalau master ini diedit kemudian.
    """
    _name = 'lpj.qc.item.template'
    _description = 'Master Aktivitas QC'
    _order = 'workcenter_group_id, sequence, id'

    name = fields.Char(string='Aktivitas QC', required=True,
                        help="Nama aktivitas pengecekan, mis. 'Cek Warna', 'Cek Bleeding'.")
    workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Kategori Tahapan', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Urutan', default=10)
    active = fields.Boolean(default=True)
