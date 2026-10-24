# -*- coding: utf-8 -*-
def migrate(cr, version):
    """OK lama: isi Tanggal Referensi Kirim = tanggal SO confirm + hari standar
    (default 7). Duedate Kirim OK lama tidak diubah."""
    cr.execute("""
        UPDATE lpj_production_ok ok
           SET x_ref_kirim = (COALESCE(so.confirmation_date, so.date_order)::date + 7)
          FROM sale_order so
         WHERE so.id = ok.sale_order_id AND ok.x_ref_kirim IS NULL
    """)
