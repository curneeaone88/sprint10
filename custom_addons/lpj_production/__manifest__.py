# -*- coding: utf-8 -*-
{
    'name': "lpj_production",

    'summary': """
        Digitalisasi proses produksi Sprint: Order Kerja (OK), Routing & Work Center,
        Checklist Kualitas (QC) digital per tahap, dan Papan Kanban status produksi.""",

    'description': """
        Digitalisasi proses produksi Sprint (Proyek 1): Order Kerja (OK), Master Routing,
        Master Mesin, Checklist Kualitas (QC) digital per mesin, dan Papan Kanban status produksi.

        Fitur utama:

        - Order Kerja (OK) sebagai unit kerja utama, dibuat per SO Line
        - Master Routing (custom) -- tiap Operation cukup menunjuk kategori proses,
          mesin spesifik dipilih PPIC/operator saat OK dibuat
        - Master (Kategori Proses, Mesin, Routing, QC) sekarang di modul lpj_design
        - Snapshot routing per OK (OK Line) supaya histori tidak berubah saat master routing diedit
        - Checklist Kualitas (QC) digital per mesin, terhubung ke OK Line via tombol "Isi Checklist"
        - Papan Kanban status produksi (Draft, Confirmed, Cetak, Finishing, Packing, Done)
        - Smart button Order Kerja di form Sales Order
        - Auto stock.picking barang jadi & bahan baku (BOM sederhana per produk, berbasis
          M2 Production riil dari Meter Lari) saat OK divalidasi Done oleh Supervisor

        Bukan berbasis MRP/Manufacturing Order, non-MRP dan ringan, sesuai keputusan arsitektur
        yang sudah disepakati (lihat PRD Sistem Digitalisasi Proses Produksi).
    """,

    'author': "Catur / Sprint IT",
    'website': "https://sprint.co.id",

    'category': 'Manufacturing',
    'version': '2.1',

    # mrp: reuse mrp.workcenter sebagai Master Mesin (bukan pakai alur MRP/MO,
    # dan bukan pakai mrp.routing -- Master Routing custom, lihat models/routing.py)
    'depends': ['base', 'sale', 'product', 'stock', 'mrp', 'lpj_sales', 'lpj_product', 'lpj_design'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/qc_checklist_view.xml',
        'views/production_ok_view.xml',
        'views/sale_order_view.xml',
        'views/planning_view.xml',
        'views/ok_shortage_wizard_view.xml',
        'report/ok_report.xml',
        'views/report_view.xml',
        'views/assets.xml',
        'views/operator_board_view.xml',
        'views/settings_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
