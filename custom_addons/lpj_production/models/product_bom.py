# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductBomLine(models.Model):
    """BOM SEDERHANA -- sengaja bukan reuse mrp.bom (sama seperti keputusan
    lpj.routing vs mrp.routing): mrp.bom bawaan penuh field yang cuma
    relevan buat alur Manufacturing Order (tipe BOM, keterkaitan Routing,
    By-product, Phantom, dst.) yang tidak kita pakai sama sekali di sini.

    Ditempel LANGSUNG ke product.template (bukan model header terpisah)
    supaya tim desain cukup isi tabel ini di form product yang sudah mereka
    buka -- tidak perlu belajar layar/konsep baru.

    Satu baris = satu bahan baku + qty yang dipakai per 1 LAYOUT (bukan lagi
    per Meter Lari/M2/Pcs terpisah -- sempat dicoba basis per-baris, tapi
    ujung-ujungnya SEMUA bahan pada satu produk memang selalu proporsional
    ke jumlah layout yang naik cetak, jadi disederhanakan jadi satu basis
    saja supaya tim desain tidak perlu mikir pilih basis per bahan).

    Jumlah layout dihitung dari Total Meter Lari OK dibagi Panjang per
    Layout produk (lihat lpj.production.ok._get_jumlah_layout()), lalu
    qty tiap bahan = qty_per_unit x jumlah layout tersebut.
    """
    _name = 'lpj.product.bom.line'
    _description = 'BOM Sederhana per Produk'
    _order = 'product_tmpl_id, sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template', string='Produk', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Urutan', default=10)
    material_product_id = fields.Many2one(
        'product.product', string='Bahan Baku', required=True)
    qty_per_unit = fields.Float(
        string='Qty per Layout', required=True, digits=(16, 4),
        help="Qty bahan ini yang dipakai untuk MEMPRODUKSI 1 LAYOUT. "
             "Total qty yang keluar dari stok saat OK selesai = angka ini "
             "x jumlah layout (Total Meter Lari OK / Panjang per Layout "
             "produk).")
