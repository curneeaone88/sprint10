# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Hitung ulang x_ok_status (stored) setelah ada nilai baru + x_design_status."""
    if not version:
        return
    cr.execute("""
        UPDATE sale_order_line sol SET x_ok_status = CASE
            WHEN EXISTS (SELECT 1 FROM lpj_production_ok ok WHERE ok.sale_order_line_id = sol.id)
                THEN 'has_ok'
            WHEN sol.product_uom_qty > 0 AND COALESCE(sol.qty_delivered,0) >= sol.product_uom_qty
                THEN 'fully_delivered'
            WHEN sol.x_design_status IS NULL OR sol.x_design_status = 'na' THEN 'no_sq'
            WHEN sol.x_design_status <> 'done' THEN 'waiting_design'
            ELSE 'need_ok' END
    """)
