# -*- coding: utf-8 -*-
{
    'name': "lpj_design",

    'summary': """
        Modul Tim Desain Sprint: kelengkapan master produk (Routing, Layout)
        per item SO ber-SQ, Kanban status desain, serta semua master produksi.""",

    'description': """
        Modul Tim Desain Sprint.

        Fitur utama:

        - Status Desain di SO Line (khusus item yang punya SQ):
          Outstanding, Sedang Dikerjakan, Selesai
        - Kanban Desain sederhana untuk tim Desain
        - Kelengkapan data produk (Routing, Layout) dicek saat SO confirm
          dan saat Tandai Data Lengkap
        - Item yang belum selesai di Desain tidak bisa dibuatkan OK (dijaga di lpj_production)
        - Master Produk, Kategori Produk, Satuan (UoM)
        - Semua master produksi ada di sini: Kategori Proses, Mesin, Routing,
          Aktivitas QC, dan Pengaturan Produksi
    """,

    'author': "Catur / Sprint IT",
    'website': "https://sprint.co.id",

    'category': 'Manufacturing',
    'version': '1.3.2',

    'depends': ['base', 'sale', 'product', 'stock', 'mrp', 'lpj_sales', 'lpj_product'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/acl_foreign.xml',
        'views/qc_item_template_view.xml',
        'views/workcenter_group_view.xml',
        'views/workcenter_extend_view.xml',
        'views/routing_view.xml',
        'views/product_view.xml',
        'views/production_settings_view.xml',
        'views/design_kanban_view.xml',
        'views/menu.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
