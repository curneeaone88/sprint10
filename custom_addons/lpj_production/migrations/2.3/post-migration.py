# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Angka tunggal lama res_company.x_ok_ref_days -> OK New dan OK Repeat.
    Aturan nominal dibiarkan 0 (nonaktif) supaya perilaku tidak berubah."""
    cr.execute("""SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'res_company' AND column_name = 'x_ok_ref_days'""")
    if cr.fetchone():
        cr.execute("""UPDATE res_company
                         SET x_ok_ref_days_new = COALESCE(x_ok_ref_days, 7),
                             x_ok_ref_days_repeat = COALESCE(x_ok_ref_days, 7)""")
