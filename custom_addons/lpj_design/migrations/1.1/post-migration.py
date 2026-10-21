# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Item SO yang sudah pernah dikirim (qty_delivered terisi) dan belum punya OK
    bukan outstanding lagi (data lama)."""
    if not version:
        return
    cr.execute("""
        SELECT 1 FROM information_schema.tables WHERE table_name='lpj_production_ok'
    """)
    if cr.fetchone():
        ok_cond = ("NOT EXISTS (SELECT 1 FROM lpj_production_ok ok "
                   "WHERE ok.sale_order_line_id = sol.id)")
    else:
        ok_cond = "TRUE"
    cr.execute("""
        UPDATE sale_order_line sol SET x_design_status = 'na'
         WHERE sol.x_design_status IN ('outstanding', 'in_progress', 'done')
           AND COALESCE(sol.qty_delivered, 0) > 0
           AND %s
    """ % ok_cond)
