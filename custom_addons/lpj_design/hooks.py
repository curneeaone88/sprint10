# -*- coding: utf-8 -*-
"""Hook install lpj_design.

Master (kategori proses, routing, QC template, BOM, dst) dulunya milik
lpj_production. Supaya tabel/kolom/data TIDAK terhapus saat Odoo membersihkan
record milik modul lama, kepemilikannya dipindah ke lpj_design SEBELUM model
dimuat (pre_init_hook). Aman dijalankan di instalasi baru (tidak ada yang
dipindah) maupun berulang.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = 'lpj_production'
NEW = 'lpj_design'

MOVED_MODELS = [
    'lpj.workcenter.group',
    'lpj.routing',
    'lpj.routing.line',
    'lpj.qc.item.template',
    'lpj.product.bom.line',
]
# model bawaan yang di-extend (field-nya pindah milik)
EXTENDED_MODELS = ['mrp.workcenter', 'product.template', 'product.category',
                   'res.company', 'res.config.settings']


def _table_exists(cr, name):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name=%s", (name,))
    return bool(cr.fetchone())


def _column_exists(cr, table, col):
    cr.execute("SELECT 1 FROM information_schema.columns "
               "WHERE table_name=%s AND column_name=%s", (table, col))
    return bool(cr.fetchone())


def pre_init_hook(cr):
    cr.execute("SELECT id FROM ir_module_module WHERE name=%s", (OLD,))
    row = cr.fetchone()
    if not row:
        return  # instalasi baru, tidak ada yang dipindah
    old_id = row[0]
    cr.execute("SELECT id FROM ir_module_module WHERE name=%s", (NEW,))
    new_id = cr.fetchone()[0]

    # 1. ir.model + ir.model.fields milik model yang dipindah
    for model in MOVED_MODELS:
        cr.execute("SELECT id FROM ir_model WHERE model=%s", (model,))
        r = cr.fetchone()
        if not r:
            continue
        model_id = r[0]
        cr.execute("""
            UPDATE ir_model_data SET module=%s
             WHERE module=%s AND model='ir.model' AND res_id=%s
        """, (NEW, OLD, model_id))
        cr.execute("""
            UPDATE ir_model_data SET module=%s
             WHERE module=%s AND model='ir.model.fields'
               AND res_id IN (SELECT id FROM ir_model_fields WHERE model_id=%s)
        """, (NEW, OLD, model_id))

    # 2. field custom (x_...) pada model bawaan yang kini dimiliki lpj_design
    cr.execute("""
        UPDATE ir_model_data SET module=%s
         WHERE module=%s AND model='ir.model.fields'
           AND res_id IN (
               SELECT f.id FROM ir_model_fields f
                 JOIN ir_model m ON m.id=f.model_id
                WHERE m.model IN %s
                  AND (f.name LIKE 'x\\_%%' OR f.name='bom_line_ids'))
    """, (NEW, OLD, tuple(EXTENDED_MODELS)))
    # field turunan sale.order.line yang dibuat lpj_production untuk BOM/design tidak ada

    # 3. constraint SQL dan tabel relasi M2M
    cr.execute("""
        UPDATE ir_model_constraint SET module=%s
         WHERE module=%s AND model IN (
            SELECT id FROM ir_model WHERE model IN %s)
    """, (new_id, old_id, tuple(MOVED_MODELS)))
    cr.execute("""
        UPDATE ir_model_relation SET module=%s
         WHERE module=%s AND name='lpj_workcenter_group_mrp_workcenter_rel'
    """, (new_id, old_id))
    cr.execute("""
        UPDATE ir_model_relation SET module=%s
         WHERE module=%s AND model IN (
            SELECT id FROM ir_model WHERE model IN %s)
    """, (new_id, old_id, tuple(MOVED_MODELS)))
    _logger.info("lpj_design: kepemilikan master dipindah dari %s", OLD)


def post_init_hook(cr, registry):
    # A. salin relasi mesin <-> kategori proses dari kolom lama (Many2one) bila masih ada
    if _column_exists(cr, 'mrp_workcenter', 'x_workcenter_group_id') and \
            _table_exists(cr, 'lpj_workcenter_group_mrp_workcenter_rel'):
        cr.execute("""
            INSERT INTO lpj_workcenter_group_mrp_workcenter_rel (group_id, workcenter_id)
            SELECT w.x_workcenter_group_id, w.id FROM mrp_workcenter w
             WHERE w.x_workcenter_group_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM lpj_workcenter_group_mrp_workcenter_rel r
                    WHERE r.group_id = w.x_workcenter_group_id
                      AND r.workcenter_id = w.id)
        """)

    # B. status desain awal untuk item SO yang sudah ada
    if not _column_exists(cr, 'sale_order_line', 'x_design_status'):
        return
    has_ok = _table_exists(cr, 'lpj_production_ok') and \
        _column_exists(cr, 'lpj_production_ok', 'sale_order_line_id')
    ok_cond = ("EXISTS (SELECT 1 FROM lpj_production_ok ok "
               "WHERE ok.sale_order_line_id = sol.id)") if has_ok else "FALSE"
    # Item yang sudah pernah dikirim (qty_delivered terisi) dan belum punya OK
    # dianggap data lama: tidak jadi outstanding. Kalau repeat order, SO baru
    # akan muncul sebagai outstanding bila Routing/Layout belum lengkap.
    cr.execute("""
        UPDATE sale_order_line sol SET x_design_status = CASE
            WHEN %s THEN 'done'
            WHEN COALESCE(sol.qty_delivered,0) > 0 THEN 'na'
            WHEN EXISTS (
                SELECT 1 FROM product_product pp
                  JOIN product_template pt ON pt.id = pp.product_tmpl_id
                 WHERE pp.id = sol.product_id AND pt.x_can_be_production)
                THEN 'done'
            WHEN so.state IN ('sale','done') THEN 'outstanding'
            ELSE 'na' END
          FROM sale_order so
         WHERE so.id = sol.order_id
           AND sol.x_sq IS NOT NULL AND sol.x_sq <> 0
           AND sol.product_id IS NOT NULL
           AND (sol.x_design_status IS NULL OR sol.x_design_status = 'na')
    """ % ok_cond)
