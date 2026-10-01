# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductionOk(models.Model):
    """OK (Order Kerja) -- unit kerja utama, dibuat PPIC per SO Line.
    Non-MRP: tidak memakai mrp.production / Manufacturing Order.

    Routing OK Line (ok_line_ids) adalah SNAPSHOT dari master routing saat OK
    dibuat -- perubahan pada master routing (lpj.routing) tidak mengubah OK
    yang sudah ada, sama seperti pola sale.order.line yang copy dari
    product.template saat SO dibuat.
    """
    _name = 'lpj.production.ok'
    _description = 'Order Kerja (OK)'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Nomor OK', required=True, copy=False,
                        readonly=True, default=lambda self: _('New'))

    # ==== Relasi ke SO ====
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='SO Line', required=True, ondelete='restrict',
        help="Baris pesanan yang menjadi dasar OK ini.")
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        related='sale_order_line_id.order_id', store=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='sale_order_id.partner_id', store=True, readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Product',
        related='sale_order_line_id.product_id', store=True, readonly=True)
    source = fields.Char(
        string='Source', related='sale_order_line_id.x_customer_requirement',
        readonly=True, help="No. SQ (precosting) asal pesanan ini.")

    order_type = fields.Selection([
        ('new', 'New'),
        ('repeat', 'Repeat'),
    ], string='Order Type', default='new', required=True,
       help="New = artwork perlu ACC customer dulu (lihat Bagian 3.1 PRD). "
            "Repeat = artwork & ACC sebelumnya masih berlaku.")

    # ==== OK Susulan (shortage follow-up, lihat action_validate_done) ====
    parent_ok_id = fields.Many2one(
        'lpj.production.ok', string='OK Induk', readonly=True, copy=False,
        help="Diisi otomatis kalau OK ini dibuat sebagai OK susulan dari "
             "kekurangan qty OK sebelumnya.")
    followup_ok_ids = fields.One2many(
        'lpj.production.ok', 'parent_ok_id', string='OK Susulan')
    followup_ok_count = fields.Integer(compute='_compute_followup_ok_count')

    # ==== Qty & Routing ====
    # qty_plan SENGAJA bukan related field lagi (dulu related ke
    # sale_order_line_id.product_uom_qty) -- supaya OK susulan bisa punya
    # target qty sendiri (sisa kekurangan), bukan ikut qty total SO Line.
    # Default tetap diambil dari SO Line saat create() kalau tidak diisi manual.
    qty_plan = fields.Float(string='Qty Plan (pcs)')
    qty_production = fields.Float(string='Qty Production (pcs)')
    m2_plan = fields.Float(
        string='M2 Plan', related='sale_order_line_id.x_sq.x_qty_m2',
        store=True, readonly=True,
        help="Diambil dari precosting (x.sales.quotation.x_qty_m2) -- "
             "single source of truth untuk target m2 pesanan asal.")
    m2_production = fields.Float(
        string='M2 Production', compute='_compute_m2_production', store=True,
        help="Dihitung otomatis dari Lebar Kertas (Master Product) x Total Meter Lari "
             "(dijumlah dari OK Line berkategori 'Sumber Konsumsi Bahan') -- "
             "BUKAN dari Length x Width x Qty, supaya mencerminkan pemakaian "
             "bahan yang riil (termasuk waste/nesting), bukan teori.")
    total_meter_lari = fields.Float(
        string='Total Meter Lari', compute='_compute_m2_production', store=True,
        help="Jumlah Meter Lari dari semua OK Line berkategori tahapan yang "
             "ditandai 'Sumber Konsumsi Bahan' (biasanya Cetak).")
    waste_bahan = fields.Float(
        string='Waste Bahan (M2)', compute='_compute_m2_production', store=True,
        help="M2 Production dikurangi total M2 sticker teoretis (Length x Width x "
             "Qty per Layout) dalam Total Meter Lari yang sama. Ini waste akibat "
             "nesting/layout (margin, celah antar-sticker) -- BUKAN reject/defect.")
    waste_percentage = fields.Float(
        string='Waste (%)', compute='_compute_m2_production', store=True,
        help="Waste Bahan dibagi M2 Production, dalam persen.")

    routing_id = fields.Many2one(
        'lpj.routing', string='Master Routing',
        help="Referensi routing master yang dipakai untuk generate OK Line "
             "saat tombol Confirm ditekan. Bisa kosong kalau OK Line diisi manual.")
    routing_display = fields.Char(
        string='Routing', compute='_compute_routing_display', store=True,
        help='Contoh: "Cetak + Plong + Packing" -- ringkasan tahapan OK Line.')

    ok_line_ids = fields.One2many(
        'lpj.production.ok.line', 'ok_id', string='Routing (OK Line)')

    # ==== Data Form (spesifikasi teknis job) ====
    x_length = fields.Float(string='Length (mm)')
    x_width = fields.Float(string='Width (mm)')
    x_material_id = fields.Many2one('x.config.bahan', string='Material')
    x_satuan = fields.Selection([
        ('sheet', 'Sheet'),
        ('roll', 'Roll'),
        ('fanfold', 'Fan Fold'),
    ], string='Satuan')
    x_type_roll_id = fields.Many2one('x.config_typeroll_product', string='Type Roll')
    x_diecut_id = fields.Many2one('x.config_diecut', string='Diecut')
    x_diecut_code = fields.Char(string='Diecut Code')
    x_hotprint_code = fields.Char(string='Hotprint Code')
    x_feature_ids = fields.Many2many(
        'x.feature.cost.precost', string='Feature',
        help="Default diambil dari Feature di master product, bisa "
             "ditambah/dikurangi manual per OK kalau diperlukan.")

    # Layout -- LIVE related ke Master Product (bukan snapshot/copy), karena
    # Layout memang konstan per produk (tidak berubah per order, sudah
    # dikonfirmasi). Read-only di sini, cuma buat informasi -- ubahnya lewat
    # form Master Product.
    x_layout_qty_pcs = fields.Integer(
        related='product_id.product_tmpl_id.x_layout_qty_pcs',
        string='Qty per Layout', readonly=True)
    x_layout_width = fields.Float(
        related='product_id.product_tmpl_id.x_layout_width',
        string='Lebar Kertas (cm)', readonly=True)
    x_layout_length = fields.Float(
        related='product_id.product_tmpl_id.x_layout_length',
        string='Panjang per Layout (cm)', readonly=True)

    # ==== Jadwal & Penanggung Jawab ====
    plan_ok = fields.Date(
        string='Plan OK',
        help="Rencana tanggal mulai produksi. WAJIB diisi sebelum OK di-Confirm.")
    duedate_kirim = fields.Datetime(
        string='Duedate Kirim', related='sale_order_line_id.x_duedate_kirim',
        store=True, readonly=True)
    responsible_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')

    # ==== Status ====
    # to_validate: semua baris Routing sudah Done, TAPI belum otomatis jadi
    # Done -- perlu divalidasi manual oleh Supervisor/Manager Produksi
    # (action_validate_done) sebelum benar-benar Done & stock.picking dibuat.
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('to_validate', 'Menunggu Validasi SPV'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False, index=True)

    status_terakhir = fields.Char(
        string='Status Terakhir', compute='_compute_status_terakhir', store=True,
        help="Gabungan tahap/mesin yang sedang aktif + status baris itu, "
             "mis. \"Cetak - Konika (In Progress)\" -- dihitung otomatis dari "
             "ok_line_ids, supaya kelihatan tanpa buka tab Routing.")

    # ==== Stock (barang jadi) ====
    picking_id = fields.Many2one(
        'stock.picking', string='Stock Picking (Barang Jadi)', readonly=True, copy=False,
        help="Dibuat & divalidasi otomatis saat OK divalidasi Done oleh SPV "
             "(lihat models/stock_picking_auto.py). Qty mengikuti Qty "
             "Production. Tidak perlu input manual.")
    material_picking_id = fields.Many2one(
        'stock.picking', string='Stock Picking (Bahan Baku)', readonly=True, copy=False,
        help="Dibuat & divalidasi otomatis saat OK divalidasi Done, berdasarkan "
             "BOM produk (product.template.bom_line_ids) x M2/Qty Production.")

    # ==== Smart buttons ====
    qc_checklist_ids = fields.One2many(
        'lpj.production.qc.checklist', 'ok_id', string='Checklist QC')
    qc_checklist_count = fields.Integer(compute='_compute_qc_checklist_count')
    qc_checklist_pending_count = fields.Integer(compute='_compute_qc_checklist_count')

    @api.multi
    @api.depends('ok_line_ids', 'ok_line_ids.workcenter_group_id', 'ok_line_ids.sequence')
    def _compute_routing_display(self):
        for rec in self:
            names = rec.ok_line_ids.sorted(key=lambda l: l.sequence).mapped(
                'workcenter_group_id.name')
            rec.routing_display = u' + '.join([n for n in names if n])

    @api.multi
    @api.depends('ok_line_ids.state', 'ok_line_ids.workcenter_group_id',
                 'ok_line_ids.workcenter_id', 'ok_line_ids.sequence')
    def _compute_status_terakhir(self):
        state_labels = dict(self.env['lpj.production.ok.line'].fields_get(
            ['state'])['state']['selection'])
        for rec in self:
            lines = rec.ok_line_ids.sorted(key=lambda l: l.sequence)
            if not lines:
                rec.status_terakhir = False
                continue
            pending = lines.filtered(lambda l: l.state != 'done')
            target = pending[0] if pending else lines[-1]
            stage_name = target.workcenter_group_id.name or ''
            machine_name = target.workcenter_id.name if target.workcenter_id else ''
            state_label = state_labels.get(target.state, target.state)
            if machine_name:
                rec.status_terakhir = u"%s - %s (%s)" % (stage_name, machine_name, state_label)
            else:
                rec.status_terakhir = u"%s (%s)" % (stage_name, state_label)

    @api.multi
    @api.depends('product_id', 'x_length', 'x_width', 'ok_line_ids.meter_lari',
                 'ok_line_ids.workcenter_group_id',
                 'ok_line_ids.workcenter_group_id.is_material_consumption_stage')
    def _compute_m2_production(self):
        for rec in self:
            material_lines = rec.ok_line_ids.filtered(
                lambda l: l.workcenter_group_id.is_material_consumption_stage)
            total_ml = sum(material_lines.mapped('meter_lari'))
            rec.total_meter_lari = total_ml

            tmpl = rec.product_id.product_tmpl_id
            lebar_cm = tmpl.x_layout_width or 0.0
            rec.m2_production = (lebar_cm / 100.0) * total_ml

            # Waste bahan: M2 Production (riil, dari Meter Lari) dikurangi
            # luas sticker TEORETIS yang seharusnya muat dalam Meter Lari
            # yang sama, dihitung via rasio 1 layout (m2 sticker per layout
            # dibagi panjang 1 layout, dikali total meter lari).
            panjang_layout_m = (tmpl.x_layout_length or 0.0) / 100.0
            qty_per_layout = tmpl.x_layout_qty_pcs or 0
            if panjang_layout_m and qty_per_layout and rec.x_length and rec.x_width:
                m2_sticker_per_layout = (rec.x_length / 1000.0) * (rec.x_width / 1000.0) * qty_per_layout
                m2_sticker_total = (m2_sticker_per_layout / panjang_layout_m) * total_ml
                rec.waste_bahan = rec.m2_production - m2_sticker_total
                rec.waste_percentage = (
                    (rec.waste_bahan / rec.m2_production) * 100.0 if rec.m2_production else 0.0)
            else:
                rec.waste_bahan = 0.0
                rec.waste_percentage = 0.0

    @api.multi
    def _get_jumlah_layout(self):
        """Jumlah layout = Total Meter Lari OK / Panjang per Layout produk.
        Dipakai sebagai basis tunggal perhitungan konsumsi BOM (lihat
        stock_picking_auto.py::_get_material_consumption()) -- semua bahan
        di BOM dihitung qty_per_unit (per 1 layout) x jumlah layout ini."""
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        panjang_layout_m = (tmpl.x_layout_length or 0.0) / 100.0
        if not panjang_layout_m:
            return 0.0
        return self.total_meter_lari / panjang_layout_m

    @api.multi
    def _compute_qc_checklist_count(self):
        for rec in self:
            rec.qc_checklist_count = len(rec.qc_checklist_ids)
            rec.qc_checklist_pending_count = len(
                rec.qc_checklist_ids.filtered(lambda c: c.state != 'done'))

    @api.multi
    def _compute_followup_ok_count(self):
        for rec in self:
            rec.followup_ok_count = len(rec.followup_ok_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lpj.production.ok') or _('New')

        # Default-populate tab "Data Forms" dari master product (Length,
        # Width, Material, Satuan, Type Roll, Diecut, Diecut Code, Hotprint
        # Code, Feature) -- tetap bisa di-override manual di vals kalau
        # memang perlu beda dari master untuk job tertentu.
        if vals.get('sale_order_line_id'):
            sol = self.env['sale.order.line'].browse(vals['sale_order_line_id'])
            product_tmpl = sol.product_id.product_tmpl_id
            if product_tmpl:
                defaults = product_tmpl.get_ok_dataform_defaults()
                for field_name, value in defaults.items():
                    if not vals.get(field_name):
                        vals[field_name] = value

            # Order Type default dari precosting (x.sales.quotation.x_repeat_order)
            # via SO Line -- tetap bisa diubah manual di OK kalau diperlukan.
            if not vals.get('order_type') and sol.x_sq:
                vals['order_type'] = 'repeat' if sol.x_sq.x_repeat_order else 'new'

            # Qty Plan default dari SO Line -- bukan related lagi, jadi harus
            # di-default manual di sini supaya OK "normal" (bukan susulan)
            # tetap otomatis terisi seperti sebelumnya.
            if not vals.get('qty_plan'):
                vals['qty_plan'] = sol.product_uom_qty

        record = super(ProductionOk, self).create(vals)
        return record

    # ==== Actions ====

    @api.multi
    def action_confirm(self):
        """Draft -> Confirmed. Plan OK WAJIB sudah diisi, dan Routing WAJIB
        ada isinya (baik dari Master Routing yang di-generate, atau diisi
        manual) sebelum bisa Confirm -- OK tanpa Routing tidak ada gunanya
        karena tidak ada tahap yang bisa dikerjakan/dipantau."""
        for rec in self:
            if not rec.plan_ok:
                raise UserError(_(
                    "Plan OK (rencana tanggal mulai produksi) wajib diisi "
                    "sebelum OK ini bisa di-Confirm."))
            if not rec.ok_line_ids:
                rec._generate_ok_lines_from_routing()
            if not rec.ok_line_ids:
                raise UserError(_(
                    "Routing belum diisi -- pilih Master Routing, atau isi "
                    "tabel Routing secara manual, sebelum OK ini bisa di-Confirm."))
            rec.state = 'confirmed'
        return True

    @api.multi
    def _generate_ok_lines_from_routing(self):
        """Generate OK Line dari Master Routing -- cuma copy KATEGORI
        tahapan (workcenter_group_id) dari tiap baris routing. Mesin
        spesifik (workcenter_id) sengaja dikosongkan di sini, supaya
        PPIC/operator yang memilih sendiri -- pilihannya otomatis
        terbatas ke mesin yang kategorinya sesuai (lihat domain
        workcenter_id di ProductionOkLine)."""
        self.ensure_one()
        if not self.routing_id:
            return
        Line = self.env['lpj.production.ok.line']
        for line in self.routing_id.line_ids.sorted(key=lambda l: l.sequence):
            Line.create({
                'ok_id': self.id,
                'sequence': line.sequence,
                'workcenter_group_id': line.workcenter_group_id.id,
                'workcenter_id': False,
            })

    @api.multi
    def action_start(self):
        """Confirmed -> In Progress. Bisa diklik manual, atau dipanggil
        otomatis dari ProductionOkLine.action_start_line() saat baris
        pertama mulai dikerjakan."""
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'in_progress'})
        return True

    @api.multi
    def action_request_validation(self):
        """In Progress -> Menunggu Validasi SPV. Dipanggil otomatis dari
        ProductionOkLine.write() begitu semua baris Routing sudah Done, ATAU
        bisa diklik manual kalau SPV mau menutup lebih awal meski belum
        semua baris Done. TIDAK langsung Done -- itu keputusan sengaja
        (butuh validasi SPV Produksi, lihat action_validate_done)."""
        self.filtered(lambda r: r.state == 'in_progress').write({'state': 'to_validate'})
        return True

    @api.multi
    def action_validate_done(self):
        """Menunggu Validasi SPV -> Done. Cuma Supervisor/Manager Produksi
        yang boleh menjalankan ini. Aturan:
        - Qty Production WAJIB > 0.
        - M2 Production sudah otomatis kehitung (computed field, dari Total
          Meter Lari x Lebar Kertas) -- tidak perlu dihitung ulang di sini.
        - stock.picking barang jadi otomatis dibuat, qty ikut Qty Production.
        - stock.picking bahan baku (BOM) otomatis dibuat, qty ikut BOM
          (qty per layout) x jumlah layout (Total Meter Lari / Panjang
          per Layout).
        - Kalau Qty Production < Qty Plan, buka wizard tanya mau bikin OK
          susulan untuk sisa qty, atau SO Line ini dianggap selesai (ditutup)
          meski kurang."""
        for rec in self:
            if not self.env.user.has_group('lpj_product.group_produksi_supervisor'):
                raise UserError(_(
                    "Hanya Supervisor/Manager Produksi yang boleh memvalidasi "
                    "penyelesaian OK."))
            if rec.state != 'to_validate':
                raise UserError(_(
                    "OK ini belum di tahap 'Menunggu Validasi SPV'."))
            if not rec.qty_production:
                raise UserError(_(
                    "Qty Production wajib diisi sebelum OK bisa divalidasi selesai."))

            rec.state = 'done'
            rec._trigger_auto_stock_picking()
            rec._trigger_auto_material_picking()

        # Cek shortage SETELAH semua record di-Done-kan (biar konsisten kalau
        # dipanggil untuk banyak record sekaligus) -- wizard cuma dibuka
        # kalau action ini dipanggil untuk SATU record (dari tombol form).
        if len(self) == 1 and self.qty_production < self.qty_plan:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Qty Production Kurang dari Plan'),
                'res_model': 'lpj.production.ok.shortage.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_ok_id': self.id},
            }
        return True

    @api.multi
    def action_done(self):
        """Selesaikan OK secara manual, LANGSUNG dari status apa pun yang
        masih aktif (bypass tahap Menunggu Validasi) -- dipakai kalau SPV
        perlu menutup OK dengan cepat tanpa lewat alur normal. Tetap
        menjalankan aturan qty/m2 yang sama seperti action_validate_done."""
        for rec in self:
            if not self.env.user.has_group('lpj_product.group_produksi_supervisor'):
                raise UserError(_(
                    "Hanya Supervisor/Manager Produksi yang boleh menyelesaikan OK."))
            if not rec.qty_production:
                raise UserError(_(
                    "Qty Production wajib diisi sebelum OK bisa diselesaikan."))
            rec.state = 'done'
            rec._trigger_auto_stock_picking()
            rec._trigger_auto_material_picking()
        if len(self) == 1 and self.qty_production < self.qty_plan:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Qty Production Kurang dari Plan'),
                'res_model': 'lpj.production.ok.shortage.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_ok_id': self.id},
            }
        return True

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_set_to_draft(self):
        """Kembalikan OK yang terlanjur di-Cancel ke Draft, supaya bisa
        diproses ulang. OK Line lama TIDAK dihapus (biar histori tetap
        ada) -- kalau routing_id masih ada dan mau digenerate ulang,
        cukup hapus manual OK Line yang lama dulu sebelum Confirm lagi."""
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_view_qc_checklists(self):
        self.ensure_one()
        action = self.env.ref('lpj_production.action_production_qc_checklist').read()[0]
        action['domain'] = [('ok_id', '=', self.id)]
        action['context'] = {'default_ok_id': self.id}
        return action

    @api.multi
    def action_view_followup_ok(self):
        self.ensure_one()
        action = self.env.ref('lpj_production.action_production_ok').read()[0]
        action['domain'] = [('parent_ok_id', '=', self.id)]
        action['context'] = {'default_parent_ok_id': self.id}
        return action


class ProductionOkLine(models.Model):
    """Baris tahap (Routing) pada satu OK -- persis tabel 'Routing' di
    mockup: Operation, Machine, Operator, Plan Date, Start/End, Meter Lari,
    Qty Pcs, Notes, dan tombol QC di ujung kanan.

    Satu baris = satu instance tahap yang dikerjakan mesin tertentu untuk OK
    tertentu -- ini snapshot, tidak terikat ke master routing setelah dibuat.
    """
    _name = 'lpj.production.ok.line'
    _description = 'OK Line (Routing per OK)'
    _order = 'ok_id, sequence, id'

    ok_id = fields.Many2one(
        'lpj.production.ok', string='Order Kerja', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Urutan', default=10)

    workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Operation', required=True,
        help="Tahapan yang dikerjakan pada baris ini, mis. Cetak, Plong, Packing.")
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Machine',
        domain="[('x_workcenter_group_id', '=', workcenter_group_id)]")
    operator_id = fields.Many2one('res.users', string='Operator')

    plan_date = fields.Date(string='Plan Date')
    date_start = fields.Datetime(string='Start (date & hours)')
    date_end = fields.Datetime(string='End (date & hours)')

    meter_lari = fields.Float(
        string='Meter Lari',
        help="Diisi kalau tahap ini bermode input 'Meter Lari' (lihat Master "
             "Tahapan) -- Qty Pcs otomatis tersaran begitu Meter Lari diisi, "
             "masih bisa dikoreksi manual kalau perlu.")
    qty_pcs = fields.Float(
        string='Qty Pcs',
        help="Kalau tahap ini bermode 'Qty Pcs' (mis. Packing), isi manual. "
             "Kalau bermode 'Meter Lari' (mis. Cetak), otomatis tersaran dari "
             "Meter Lari x Layout produk -- tetap bisa dikoreksi manual.")
    notes = fields.Char(string='Notes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', default='draft')

    # ==== QC ====
    qc_checklist_ids = fields.One2many(
        'lpj.production.qc.checklist', 'ok_line_id', string='Checklist QC')
    qc_status = fields.Selection([
        ('none', 'Belum Diisi'),
        ('pending', 'Belum Lengkap'),
        ('ok', 'Sesuai'),
        ('not_ok', 'Ada Tidak Sesuai'),
    ], string='Status QC', compute='_compute_qc_status', store=True)

    @api.onchange('meter_lari', 'workcenter_group_id')
    def _onchange_meter_lari_suggest_qty_pcs(self):
        """Cuma menyaran nilai Qty Pcs (operator masih bisa timpa manual) --
        BUKAN compute keras, karena tidak semua tahap berbasis Meter Lari
        (mis. Packing hasilnya emang dihitung per pcs langsung, tidak lewat
        Meter Lari sama sekali). Cek Master Tahapan.x_input_mode dulu."""
        if self.workcenter_group_id and self.workcenter_group_id.x_input_mode == 'meter_lari':
            tmpl = self.ok_id.product_id.product_tmpl_id if self.ok_id else False
            if tmpl and tmpl.x_layout_length and tmpl.x_layout_qty_pcs:
                panjang_layout_m = tmpl.x_layout_length / 100.0
                self.qty_pcs = (self.meter_lari / panjang_layout_m) * tmpl.x_layout_qty_pcs

    @api.multi
    @api.depends('qc_checklist_ids', 'qc_checklist_ids.result_summary', 'qc_checklist_ids.state')
    def _compute_qc_status(self):
        for rec in self:
            checklist = rec.qc_checklist_ids[:1]
            if not checklist:
                rec.qc_status = 'none'
            elif checklist.state != 'done':
                rec.qc_status = 'pending'
            else:
                rec.qc_status = checklist.result_summary or 'pending'

    @api.multi
    def _qc_required_and_cleared(self):
        """True kalau baris ini boleh ditandai Done ditinjau dari sisi QC:
        - Kalau kategori tahapannya tidak punya aktivitas QC terdaftar sama sekali -> True (tidak berlaku).
        - Kalau punya -> True hanya kalau ada checklist yang sudah dikonfirmasi (state='done')."""
        self.ensure_one()
        if not self.workcenter_group_id or not self.workcenter_group_id.qc_item_template_ids:
            return True
        return bool(self.qc_checklist_ids.filtered(lambda c: c.state == 'done'))

    @api.multi
    def action_start_line(self):
        """Operator mulai kerjakan tahap ini. Baris pertama yang dimulai
        otomatis memindahkan OK header dari Confirmed ke In Progress."""
        for rec in self:
            if rec.state == 'draft':
                rec.write({'state': 'in_progress'})
                if not rec.date_start:
                    rec.date_start = fields.Datetime.now()
            if rec.ok_id.state == 'confirmed':
                rec.ok_id.action_start()
        return True

    @api.multi
    def action_done_line(self):
        """Operator tandai tahap ini selesai -- lewat write() supaya gating
        QC (lihat write() override di bawah) dan permintaan validasi SPV
        (kalau ini baris terakhir yang belum Done) sama-sama berjalan."""
        for rec in self:
            rec.write({'state': 'done'})
            if not rec.date_end:
                rec.date_end = fields.Datetime.now()
        return True

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'done':
            for rec in self:
                if not rec._qc_required_and_cleared():
                    raise UserError(_(
                        "Tidak bisa menandai tahap '%s' selesai -- checklist QC "
                        "untuk kategori tahapan ini masih ada aktivitas yang "
                        "belum dikonfirmasi. Isi & konfirmasi checklist-nya dulu."
                    ) % (rec.workcenter_group_id.name or '-'))
        res = super(ProductionOkLine, self).write(vals)
        if vals.get('state') == 'done':
            for rec in self:
                remaining = rec.ok_id.ok_line_ids.filtered(lambda l: l.state != 'done')
                # PENTING: begitu semua baris Done, OK pindah ke "Menunggu
                # Validasi SPV" -- BUKAN langsung Done. Supervisor/Manager
                # harus klik "Validasi & Selesaikan" (action_validate_done)
                # dulu sebelum stock.picking dibuat.
                if not remaining and rec.ok_id.state == 'in_progress':
                    rec.ok_id.action_request_validation()
        return res

    @api.multi
    def action_open_qc_checklist(self):
        """Tombol 'Isi Checklist' -- kalau sudah ada checklist yang selesai
        (done), buka checklist ITU (mode lihat), JANGAN buat baru. Kalau
        ada draft yang belum selesai, lanjutkan draft itu. Cuma kalau
        benar-benar belum pernah ada checklist sama sekali, baru dibuatkan
        baru (auto-populate aktivitas dari master lpj.qc.item.template
        sesuai KATEGORI tahapan baris ini). Tidak perlu menunggu mesin
        dipilih dulu -- aktivitas QC bersumber dari kategori
        (workcenter_group_id), yang sudah pasti terisi sejak baris ini
        dibuat dari Master Routing."""
        self.ensure_one()
        checklist = self.qc_checklist_ids.filtered(lambda c: c.state == 'done')[:1]
        if not checklist:
            checklist = self.qc_checklist_ids.filtered(lambda c: c.state != 'done')[:1]
        if not checklist:
            templates = self.env['lpj.qc.item.template'].search(
                [('workcenter_group_id', '=', self.workcenter_group_id.id)])
            checklist = self.env['lpj.production.qc.checklist'].create({
                'ok_line_id': self.id,
                'item_ids': [(0, 0, {
                    'item_template_id': t.id,
                    'name': t.name,
                    'sequence': t.sequence,
                }) for t in templates],
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Checklist QC'),
            'res_model': 'lpj.production.qc.checklist',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': checklist.id,
            'target': 'new',
        }
