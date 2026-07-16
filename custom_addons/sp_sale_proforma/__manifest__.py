# -*- coding: utf-8 -*-
{
    'name': 'SP Sale Proforma Invoice',
    'version': '1.0.0',
    'summary': 'Cetak Proforma Invoice (PI) dari Sales Order dengan input DP fix amount & PPN master',
    'description': """
Menambahkan tombol "Cetak Proforma Invoice" pada form Sales Order.
Saat diklik, muncul popup untuk input:
  - Nomor PI
  - Nilai DP (fix amount)
  - PPN (diambil dari master account.tax)

Hasil cetak berupa PDF Proforma Invoice berisi seluruh item SO,
Sub Total, DP, PPN atas DP, dan Total Pembayaran DP.
    """,
    'author': 'Catur Kurniawan',
    'category': 'Sales',
    # Sesuaikan dengan nama module custom sale order Anda yang berisi models.py
    # (module yang menambahkan field x_po_cust, x_sq, dll pada sale.order / sale.order.line)
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_proforma_wizard_view.xml',
        'views/sale_order_view.xml',
        'report/report_proforma_invoice.xml',
    ],
    'installable': True,
    'application': False,
}
