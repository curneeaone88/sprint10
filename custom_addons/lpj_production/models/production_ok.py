# -*- coding: utf-8 -*-
from datetime import timedelta

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
        help="Jumlah Meter Lari dari semua OK Line berkategori proses yang "
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
        string='Lebar Kertas (mm)', readonly=True)
    x_layout_length = fields.Float(
        related='product_id.product_tmpl_id.x_layout_length',
        string='Panjang per Layout (mm)', readonly=True)

    # ==== Jadwal & Penanggung Jawab ====
    plan_ok = fields.Date(
        string='Plan OK',
        help="Rencana tanggal mulai produksi. WAJIB diisi sebelum OK di-Confirm.")
    x_ref_kirim = fields.Date(
        string='Tanggal Referensi Kirim', readonly=True, copy=False,
        help="Tanggal SO di-confirm + jumlah hari standar (Pengaturan "
             "Produksi). Dihitung sekali saat OK dibuat, tidak berubah kalau "
             "setting hari diubah belakangan. Jadi acuan awal Duedate Kirim.")
    duedate_kirim = fields.Datetime(
        string='Duedate Kirim', copy=False,
        help="Default = Tanggal Referensi Kirim. Hanya PPIC / Supervisor / "
             "Manager yang boleh mengubah.")
    x_can_edit_duedate = fields.Boolean(
        string='Boleh Edit Duedate', compute='_compute_can_edit_duedate')
    responsible_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')
    x_folder_cetak = fields.Char(
        string='Folder File Cetak',
        help="Lokasi folder file cetak/artwork untuk job ini, diisi tim "
             "Desain atau PPIC. Ikut tercetak di lembar Perintah Kerja. "
             "Contoh: \\\\SERVER-CETAK\\Produksi\\2026\\10\\NAMA CUSTOMER\\nama job")

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

    date_done = fields.Datetime(
        string='Tanggal Selesai (Done)', readonly=True, copy=False,
        help="Terisi otomatis saat OK menjadi Done. Dipakai untuk laporan "
             "Produksi (Waste Bahan, Ketepatan Waktu).")
    delay_days = fields.Float(
        string='Telat (Hari)', compute='_compute_delay', store=True,
        group_operator='avg',
        help="Selisih hari tanggal Done terhadap Duedate Kirim. 0 kalau tepat "
             "waktu. Hanya untuk laporan Ketepatan Waktu.")
    ontime_status = fields.Selection([
        ('on_time', 'Tepat Waktu'),
        ('late', 'Telat'),
    ], string='Ketepatan Waktu', compute='_compute_delay', store=True)

    status_terakhir = fields.Char(
        string='Status Terakhir', compute='_compute_status_terakhir', store=True,
        help="Gabungan tahap/mesin yang sedang aktif + status baris itu, "
             "mis. \"Cetak - Konika (In Progress)\" -- dihitung otomatis dari "
             "ok_line_ids, supaya kelihatan tanpa buka tab Routing.")
    all_lines_done = fields.Boolean(
        string='Semua Routing Selesai', compute='_compute_all_lines_done', store=True,
        help="True hanya kalau OK Line ada isinya DAN semua baris sudah "
             "state Done. Dipakai supaya tombol 'Ajukan Validasi' di header "
             "cuma muncul SETELAH seluruh tahapan Routing benar-benar "
             "selesai dikerjakan -- bukan bisa diklik kapan saja selama "
             "status In Progress.")

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
    @api.depends('ok_line_ids.state')
    def _compute_all_lines_done(self):
        for rec in self:
            lines = rec.ok_line_ids
            rec.all_lines_done = bool(lines) and all(l.state == 'done' for l in lines)

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
            lebar_mm = tmpl.x_layout_width or 0.0
            rec.m2_production = (lebar_mm / 1000.0) * total_ml

            # Waste bahan: M2 Production (riil, dari Meter Lari) dikurangi
            # luas sticker TEORETIS yang seharusnya muat dalam Meter Lari
            # yang sama, dihitung via rasio 1 layout (m2 sticker per layout
            # dibagi panjang 1 layout, dikali total meter lari).
            # Semua ukuran fisik di modul ini konsisten pakai MM supaya tidak
            # ada campur cm/mm yang bikin bingung konversi -- MM/1000 = Meter.
            panjang_layout_m = (tmpl.x_layout_length or 0.0) / 1000.0
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
    @api.depends('date_done', 'duedate_kirim')
    def _compute_delay(self):
        for rec in self:
            if rec.date_done and rec.duedate_kirim:
                done_day = fields.Date.from_string(
                    fields.Date.context_today(rec, fields.Datetime.from_string(rec.date_done)))
                due_day = fields.Date.from_string(
                    fields.Date.context_today(rec, fields.Datetime.from_string(rec.duedate_kirim)))
                diff = (done_day - due_day).days
                rec.delay_days = max(diff, 0)
                rec.ontime_status = 'late' if diff > 0 else 'on_time'
            else:
                rec.delay_days = 0.0
                rec.ontime_status = False

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        """Kolom Kanban OK berurutan sesuai alur: Draft, Confirmed,
        In Progress, Menunggu Validasi, Done, Cancelled (bukan abjad), dan
        semua kolom selalu tampil walau kosong."""
        res = super(ProductionOk, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy)
        first = groupby[0] if isinstance(groupby, (list, tuple)) and groupby else groupby
        if first == 'state':
            states = [k for k, _l in self._fields['state'].selection]
            labels = dict(self._fields['state'].selection)
            present = set(g.get('state') for g in res)
            if lazy or len(groupby) == 1:
                for key in states:
                    if key not in present:
                        res.append({
                            'state': key,
                            'state_count': 0,
                            '__domain': [('state', '=', key)] + list(domain),
                            '__context': {'group_by': list(groupby[1:])},
                        })
            res = sorted(res, key=lambda g: states.index(g.get('state'))
                         if g.get('state') in states else len(states))
        return res

    @api.multi
    def _compute_can_edit_duedate(self):
        ok = self._user_can_edit_duedate()
        for rec in self:
            rec.x_can_edit_duedate = ok

    @api.model
    def _user_can_edit_duedate(self):
        u = self.env.user
        return bool(self.env.uid == 1 or
                    u.has_group('lpj_production.group_ppic') or
                    u.has_group('lpj_product.group_produksi_supervisor') or
                    u.has_group('lpj_product.group_produksi_manager'))

    @api.model
    def _calc_ref_kirim(self, sale_order):
        """SO confirm date + hari standar (res.company.x_ok_ref_days)."""
        days = self.env.user.company_id.x_ok_ref_days or 0
        base = None
        conf = getattr(sale_order, 'confirmation_date', False) or \
            (sale_order and sale_order.date_order)
        if conf:
            base = fields.Datetime.from_string(conf)
            base = fields.Datetime.context_timestamp(self, base).date()
        else:
            base = fields.Date.from_string(fields.Date.context_today(self))
        return fields.Date.to_string(base + timedelta(days=days))

    @api.multi
    def write(self, vals):
        if 'duedate_kirim' in vals and not self._user_can_edit_duedate():
            raise UserError(_(
                "Duedate Kirim hanya boleh diubah oleh PPIC, Supervisor atau Manager."))
        if vals.get('state') == 'done':
            vals = dict(vals, date_done=fields.Datetime.now())
        elif vals.get('state') and vals['state'] != 'done':
            vals = dict(vals, date_done=False)
        return super(ProductionOk, self).write(vals)

    @api.multi
    def _get_jumlah_layout(self):
        """Jumlah layout = Total Meter Lari OK / Panjang per Layout produk.
        Dipakai sebagai basis tunggal perhitungan konsumsi BOM (lihat
        stock_picking_auto.py::_get_material_consumption()) -- semua bahan
        di BOM dihitung qty_per_unit (per 1 layout) x jumlah layout ini."""
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        panjang_layout_m = (tmpl.x_layout_length or 0.0) / 1000.0
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

            # Tanggal Referensi Kirim & default Duedate Kirim
            if not vals.get('x_ref_kirim'):
                vals['x_ref_kirim'] = self._calc_ref_kirim(sol.order_id)
            if not vals.get('duedate_kirim'):
                vals['duedate_kirim'] = vals['x_ref_kirim'] + ' 00:00:00'

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
            # Plan Date tiap baris routing default = Plan OK (yang sudah
            # diisi manual per baris tidak ditimpa).
            rec.ok_line_ids.filtered(lambda l: not l.plan_date).write(
                {'plan_date': rec.plan_ok})
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
        """In Progress -> Menunggu Validasi SPV. Tombol ini di header SENGAJA
        disembunyikan (lihat all_lines_done & views/production_ok_view.xml)
        sampai SEMUA baris Routing (ok_line_ids) sudah Done -- tidak lagi
        bisa diklik lebih awal/prematur. Guard di sini cuma jaga-jaga kalau
        dipanggil lewat jalur lain (mis. automation/API), bukan cuma andalkan
        UI. TIDAK langsung Done -- itu keputusan sengaja (butuh validasi SPV
        Produksi, lihat action_validate_done)."""
        for rec in self:
            if rec.state != 'in_progress':
                continue
            if not rec.all_lines_done:
                raise UserError(_(
                    "Belum bisa mengajukan validasi -- masih ada baris Routing "
                    "yang belum Done."))
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

    # ==== Cetak Perintah Kerja (A4 landscape, lihat report/ok_report.xml) ====
    @api.model
    def _fmt_num(self, val, dec=0):
        """Angka format Indonesia: titik ribuan, koma desimal."""
        val = val or 0.0
        txt = ('{:,.%df}' % dec).format(val)
        return txt.replace(',', '#').replace('.', ',').replace('#', '.')

    @api.model
    def _fmt_trim(self, val):
        """Angka tanpa nol di belakang koma (40.0 -> 40, 2.5 -> 2,5)."""
        val = val or 0.0
        if abs(val - round(val)) < 0.00001:
            return self._fmt_num(val, 0)
        return self._fmt_num(val, 2).rstrip('0').rstrip(',')

    @api.model
    def _fmt_date(self, value, with_time=False):
        if not value:
            return ''
        if with_time:
            dt = fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(value))
            return dt.strftime('%d-%m-%Y %H:%M')
        return fields.Date.from_string(value).strftime('%d-%m-%Y')

    @api.multi
    def get_print_data(self):
        """Semua data lembar Perintah Kerja dalam satu dict supaya template
        QWeb tetap sederhana."""
        self.ensure_one()
        from datetime import datetime
        satuan = dict(self._fields['x_satuan'].selection).get(self.x_satuan, '') \
            if self.x_satuan else ''
        order_type = dict(self._fields['order_type'].selection).get(self.order_type, '')
        features = u', '.join([f.display_name for f in self.x_feature_ids])
        layout = ''
        if self.x_layout_qty_pcs or self.x_layout_width or self.x_layout_length:
            layout = u'%s pcs/layout | Lebar %s mm | Panjang %s mm' % (
                self._fmt_trim(self.x_layout_qty_pcs),
                self._fmt_trim(self.x_layout_width),
                self._fmt_trim(self.x_layout_length))
        info = {
            'printed_at': fields.Datetime.context_timestamp(
                self, datetime.now()).strftime('%d-%m-%Y %H:%M'),
            'so': self.sale_order_id.name or '',
            'customer': self.partner_id.name or '',
            'source': self.source or '',
            'order_type': order_type,
            'plan_ok': self._fmt_date(self.plan_ok),
            'duedate': self._fmt_date(self.duedate_kirim, True),
            'responsible': self.responsible_id.name or '',
            'product': self.product_id.display_name or '',
            'qty_plan': (self._fmt_trim(self.qty_plan) + ' pcs') if self.qty_plan else '',
            'm2_plan': (self._fmt_num(self.m2_plan, 2) + ' m2') if self.m2_plan else '',
            'length': self._fmt_trim(self.x_length) if self.x_length else '',
            'width': self._fmt_trim(self.x_width) if self.x_width else '',
            'material': self.x_material_id.display_name or '',
            'satuan': satuan,
            'type_roll': self.x_type_roll_id.display_name or '',
            'diecut': self.x_diecut_id.display_name or '',
            'diecut_code': self.x_diecut_code or '',
            'hotprint_code': self.x_hotprint_code or '',
            'features': features,
            'layout': layout,
            'folder': self.x_folder_cetak or '',
            'routing_rows': [],
            'qc_rows': [],
        }
        lines = self.ok_line_ids.sorted(key=lambda l: (l.sequence, l.id))
        seen_groups = set()
        if lines:
            for i, l in enumerate(lines, 1):
                group = l.workcenter_group_id
                meter_mode = (group.x_input_mode == 'meter_lari')
                info['routing_rows'].append({
                    'no': i, 'name': group.name or '',
                    'hint': u'Input: Meter Lari -> Pcs otomatis' if meter_mode else u'Input: Qty Pcs',
                    'machine': l.workcenter_id.name or '',
                    'operator': l.operator_id.name or '',
                    'plan_date': self._fmt_date(l.plan_date),
                    'meter_mode': meter_mode,
                    'qc': bool(group.qc_item_template_ids),
                })
                if group.id not in seen_groups:
                    seen_groups.add(group.id)
                    for t in group.qc_item_template_ids.sorted(key=lambda t: (t.sequence, t.id)):
                        info['qc_rows'].append({'group': group.name or '', 'name': t.name})
        elif self.routing_id:
            # OK masih Draft: baris routing belum dibuat, pakai master routing
            for i, rl in enumerate(self.routing_id.line_ids.sorted(key=lambda l: (l.sequence, l.id)), 1):
                group = rl.workcenter_group_id
                meter_mode = (group.x_input_mode == 'meter_lari')
                info['routing_rows'].append({
                    'no': i, 'name': group.name or '',
                    'hint': u'Input: Meter Lari -> Pcs otomatis' if meter_mode else u'Input: Qty Pcs',
                    'machine': '', 'operator': '', 'plan_date': '',
                    'meter_mode': meter_mode, 'qc': bool(group.qc_item_template_ids),
                })
                if group.id not in seen_groups:
                    seen_groups.add(group.id)
                    for t in group.qc_item_template_ids.sorted(key=lambda t: (t.sequence, t.id)):
                        info['qc_rows'].append({'group': group.name or '', 'name': t.name})
        return info

    @api.multi
    def action_print_perintah_kerja(self):
        """Cetak lembar Perintah Kerja (A4 landscape, 1 halaman per OK)."""
        return self.env['report'].get_action(
            self, 'lpj_production.report_perintah_kerja')

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

    input_mode = fields.Selection(
        related='workcenter_group_id.x_input_mode', string='Mode Input', readonly=True)
    can_start = fields.Boolean(
        string='Boleh Dimulai', compute='_compute_can_start',
        help="True kalau semua baris Routing SEBELUM baris ini (urutan "
             "sequence) sudah Done -- tahapan harus berurutan sesuai Master "
             "Routing, tidak boleh lompat.")

    workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Operation', required=True,
        help="Tahapan yang dikerjakan pada baris ini, mis. Cetak, Plong, Packing.")
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Machine',
        domain="[('x_workcenter_group_ids', 'in', [workcenter_group_id])]")
    operator_id = fields.Many2one('res.users', string='Operator')

    plan_date = fields.Date(string='Plan Date')
    date_start = fields.Datetime(string='Start (date & hours)')
    date_end = fields.Datetime(string='End (date & hours)')
    ok_partner_id = fields.Many2one(
        'res.partner', related='ok_id.partner_id', string='Customer', readonly=True)
    ok_product_id = fields.Many2one(
        'product.product', related='ok_id.product_id', string='Product', readonly=True)
    ok_qty_plan = fields.Float(related='ok_id.qty_plan', string='Qty Plan', readonly=True)
    ok_duedate = fields.Datetime(related='ok_id.duedate_kirim', string='Duedate Kirim', readonly=True)
    ok_order_type = fields.Selection(related='ok_id.order_type', string='Order Type', readonly=True)
    x_can_edit_times = fields.Boolean(
        string='Boleh Edit Start/End', compute='_compute_can_edit_times')

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        """Kolom Kanban Papan Operator berurutan Draft, In Progress, Done
        dan selalu tampil walau kosong."""
        res = super(ProductionOkLine, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy)
        first = groupby[0] if isinstance(groupby, (list, tuple)) and groupby else groupby
        if first == 'state' and self.env.context.get('operator_board'):
            states = [k for k, _l in self._fields['state'].selection]
            present = set(g.get('state') for g in res)
            if lazy or len(groupby) == 1:
                for key in states:
                    if key not in present:
                        res.append({
                            'state': key,
                            'state_count': 0,
                            '__domain': [('state', '=', key)] + list(domain),
                            '__context': {'group_by': list(groupby[1:])},
                        })
            res = sorted(res, key=lambda g: states.index(g.get('state'))
                         if g.get('state') in states else len(states))
        return res

    @api.multi
    def _compute_can_edit_times(self):
        ok = self._user_can_edit_times()
        for rec in self:
            rec.x_can_edit_times = ok

    @api.model
    def _user_can_edit_times(self):
        """Start/End manual hanya PPIC, Supervisor, Manager Produksi.
        Operator tetap bisa lewat tombol Mulai/Selesai (otomatis)."""
        u = self.env.user
        return bool(self.env.uid == 1 or
                    u.has_group('lpj_production.group_ppic') or
                    u.has_group('lpj_product.group_produksi_supervisor') or
                    u.has_group('lpj_product.group_produksi_manager'))

    @api.constrains('date_start', 'date_end')
    def _check_end_after_start(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end <= rec.date_start:
                raise UserError(_(
                    "Tahap '%s': End harus lebih besar dari Start. "
                    "Periksa kembali tanggal & jam yang diisi.")
                    % (rec.workcenter_group_id.name or '-'))

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
    qc_required = fields.Boolean(
        string='Tahap ini Butuh QC', compute='_compute_qc_required', store=True,
        help="True kalau kategori proses (workcenter_group_id) baris ini "
             "punya minimal 1 Aktivitas QC terdaftar di Master. Dipakai "
             "khusus untuk tombol di tree OK (Mulai/Isi Checklist/Selesai) "
             "supaya tombol 'Isi Checklist' hanya muncul kalau memang "
             "relevan -- beda dari qc_status yang baru berubah dari 'none' "
             "SETELAH checklist-nya dibuat (checklist dibuat lazily saat "
             "tombol diklik, jadi tidak bisa dipakai sendirian untuk "
             "menentukan apakah tombolnya perlu ditampilkan).")

    # ==== Field khusus laporan Produksi (tidak ditampilkan di form OK) ====
    date_done_day = fields.Date(
        string='Tanggal Selesai', compute='_compute_report_fields', store=True,
        help="Tanggal (zona waktu user) dari End. Untuk laporan output harian.")
    m2_bahan = fields.Float(
        string='M2 Bahan', compute='_compute_report_fields', store=True,
        help="Lebar Kertas layout x Meter Lari baris ini (pemakaian bahan riil).")
    m2_product = fields.Float(
        string='M2 Produk', compute='_compute_report_fields', store=True,
        help="Panjang x Lebar produk (OK) x Qty Pcs baris ini (luas produk jadi).")
    duration_hours = fields.Float(
        string='Durasi (Jam)', compute='_compute_report_fields', store=True)
    duration_hours_avg = fields.Float(
        string='Rata-rata Durasi (Jam)', compute='_compute_report_fields',
        store=True, group_operator='avg')
    wait_hours = fields.Float(
        string='Antrean Sebelum Mulai (Jam)', compute='_compute_report_fields',
        store=True, group_operator='avg',
        help="Jeda dari baris sebelumnya selesai sampai baris ini dimulai.")
    m2_per_hour = fields.Float(
        string='M2 Bahan per Jam', compute='_compute_report_fields',
        store=True, group_operator='avg')
    report_month = fields.Char(
        string='Bulan', compute='_compute_report_fields', store=True)

    @api.multi
    @api.depends('date_start', 'date_end', 'meter_lari', 'qty_pcs',
                 'ok_id.x_length', 'ok_id.x_width',
                 'ok_id.product_id.product_tmpl_id.x_layout_width',
                 'ok_id.ok_line_ids.date_end', 'ok_id.ok_line_ids.sequence')
    def _compute_report_fields(self):
        for rec in self:
            ok = rec.ok_id
            tmpl = ok.product_id.product_tmpl_id
            lebar_m = (tmpl.x_layout_width or 0.0) / 1000.0
            rec.m2_bahan = lebar_m * (rec.meter_lari or 0.0)
            rec.m2_product = ((ok.x_length or 0.0) / 1000.0) * \
                ((ok.x_width or 0.0) / 1000.0) * (rec.qty_pcs or 0.0)

            start = fields.Datetime.from_string(rec.date_start) if rec.date_start else False
            end = fields.Datetime.from_string(rec.date_end) if rec.date_end else False
            if end:
                rec.date_done_day = fields.Date.context_today(rec, end)
                rec.report_month = rec.date_done_day[:7]
            else:
                rec.date_done_day = False
                rec.report_month = False
            hours = 0.0
            if start and end and end > start:
                hours = (end - start).total_seconds() / 3600.0
            rec.duration_hours = hours
            rec.duration_hours_avg = hours
            rec.m2_per_hour = rec.m2_bahan / hours if hours else 0.0

            wait = 0.0
            if start:
                prev = ok.ok_line_ids.filtered(
                    lambda l: l.id != rec.id and l.date_end and
                    (l.sequence, l.id) < (rec.sequence, rec.id)).sorted(
                        key=lambda l: (l.sequence, l.id))
                if prev:
                    prev_end = fields.Datetime.from_string(prev[-1].date_end)
                    if start > prev_end:
                        wait = (start - prev_end).total_seconds() / 3600.0
            rec.wait_hours = wait

    @api.onchange('meter_lari', 'workcenter_group_id')
    def _onchange_meter_lari_suggest_qty_pcs(self):
        """Dua kriteria tahapan (lihat Master Kategori Proses.x_input_mode):
        - 'meter_lari' (mis. Cetak): operator input Meter Lari, Qty Pcs
          disaranin otomatis = (Meter Lari / Panjang per Layout) x Qty per
          Layout. Masih bisa dikoreksi manual.
        - 'qty_pcs' (mis. Packing): operator input Qty Pcs langsung, Meter
          Lari tidak dipakai, dan TIDAK ADA hitung-hitungan sama sekali.
        Kalau data Layout produk belum lengkap, saran dilewati (tidak error)
        dan Qty Pcs diisi manual."""
        qty = self._calc_qty_pcs_from_meter()
        if qty:
            self.qty_pcs = qty

    @api.multi
    def _calc_qty_pcs_from_meter(self):
        """(Meter Lari / Panjang per Layout) x Qty per Layout, khusus tahap
        mode 'meter_lari'. Return 0.0 kalau bukan mode itu, Meter Lari
        kosong, atau data Layout produk belum lengkap. Dipakai oleh onchange
        DAN fallback di server (create/write/Done), karena onchange tidak
        selalu punya ok_id (mis. popup Input Hasil / baris tree baru) dan
        saat itu saran Qty Pcs tidak terisi."""
        self.ensure_one()
        group = self.workcenter_group_id
        if not group or group.x_input_mode != 'meter_lari' or not self.meter_lari:
            return 0.0
        tmpl = self.ok_id.product_id.product_tmpl_id if self.ok_id else False
        if not (tmpl and tmpl.x_layout_length and tmpl.x_layout_qty_pcs):
            return 0.0
        panjang_layout_m = tmpl.x_layout_length / 1000.0
        return (self.meter_lari / panjang_layout_m) * tmpl.x_layout_qty_pcs

    @api.multi
    def _check_result_filled(self):
        """Hasil output wajib terisi sesuai mode tahapan sebelum Done:
        mode 'meter_lari' -> Meter Lari dan Qty Pcs; mode 'qty_pcs' -> cukup
        Qty Pcs (Meter Lari tidak diminta)."""
        for rec in self:
            mode = rec.workcenter_group_id.x_input_mode
            name = rec.workcenter_group_id.name or '-'
            if mode == 'meter_lari' and rec.meter_lari and not rec.qty_pcs:
                rec.qty_pcs = rec._calc_qty_pcs_from_meter()
            if mode == 'meter_lari' and not rec.meter_lari:
                raise UserError(_(
                    "Tahap '%s' belum bisa diselesaikan: isi Meter Lari dulu "
                    "(Qty Pcs akan terhitung otomatis dari Layout).") % name)
            if not rec.qty_pcs:
                raise UserError(_(
                    "Tahap '%s' belum bisa diselesaikan: Qty Pcs hasil tahap "
                    "ini belum diisi.") % name)

    @api.multi
    @api.depends('workcenter_group_id', 'workcenter_group_id.qc_item_template_ids')
    def _compute_qc_required(self):
        for rec in self:
            rec.qc_required = bool(
                rec.workcenter_group_id and rec.workcenter_group_id.qc_item_template_ids)

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
        - Kalau kategori prosesnya tidak punya aktivitas QC terdaftar sama sekali -> True (tidak berlaku).
        - Kalau punya -> True hanya kalau ada checklist yang sudah dikonfirmasi (state='done')."""
        self.ensure_one()
        if not self.workcenter_group_id or not self.workcenter_group_id.qc_item_template_ids:
            return True
        return bool(self.qc_checklist_ids.filtered(lambda c: c.state == 'done'))

    @api.multi
    @api.depends('state', 'sequence', 'ok_id.ok_line_ids.state', 'ok_id.ok_line_ids.sequence')
    def _compute_can_start(self):
        for rec in self:
            prev = rec.ok_id.ok_line_ids.filtered(
                lambda l: l.id != rec.id and (l.sequence, l.id) < (rec.sequence, rec.id))
            rec.can_start = all(l.state == 'done' for l in prev)

    @api.multi
    def _check_ready_to_start(self, vals=None):
        """Sebelum tahap di-Start, Machine, Operator, dan Plan Date WAJIB
        sudah diisi -- supaya data siapa/di mana/kapan tidak kosong di OK.
        vals (opsional) = nilai yang sedang ditulis bersamaan dengan
        perubahan state, dipakai kalau field itu diisi di write yang sama."""
        vals = vals or {}
        labels = (
            ('workcenter_id', _('Machine')),
            ('operator_id', _('Operator')),
            ('plan_date', _('Plan Date')),
        )
        for rec in self:
            missing = [label for fname, label in labels
                       if not (vals[fname] if fname in vals else rec[fname])]
            if missing:
                raise UserError(_(
                    "Tahap '%s' belum bisa dimulai. Field berikut wajib "
                    "diisi dulu: %s."
                ) % (rec.workcenter_group_id.name or '-', ', '.join(missing)))
        return True

    @api.multi
    def action_start_line(self):
        """Operator mulai kerjakan tahap ini. Baris pertama yang dimulai
        otomatis memindahkan OK header dari Confirmed ke In Progress."""
        for rec in self:
            if rec.state == 'draft' and not rec.can_start:
                raise UserError(_(
                    "Tahap '%s' belum bisa dimulai -- selesaikan dulu tahap "
                    "sebelumnya sesuai urutan Routing.") % (rec.workcenter_group_id.name or '-'))
            if rec.state == 'draft':
                rec._check_ready_to_start()
                rec.with_context(line_internal=True).write({'state': 'in_progress'})
                if not rec.date_start:
                    rec.with_context(line_times_internal=True).write(
                        {'date_start': fields.Datetime.now()})
            if rec.ok_id.state == 'confirmed':
                rec.ok_id.action_start()
        return True

    @api.multi
    def action_open_result_form(self):
        """Popup kecil untuk mengisi hasil output tahap ini (Meter Lari /
        Qty Pcs) dari tampilan kartu mobile, karena field di kartu Kanban
        tidak bisa diedit langsung."""
        self.ensure_one()
        view = self.env.ref('lpj_production.view_production_ok_line_result_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Input Hasil Tahap'),
            'res_model': 'lpj.production.ok.line',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_id': self.id,
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def action_view_ok_popup(self):
        """Operator lihat seluruh OK (view only) dalam popup."""
        self.ensure_one()
        view = self.env.ref('lpj_production.view_production_ok_form_viewonly')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Kerja'),
            'res_model': 'lpj.production.ok',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_id': self.ok_id.id,
            'target': 'new',
            'flags': {'form': {'action_buttons': False}},
        }

    @api.multi
    def action_save_and_done(self):
        """Tombol 'Simpan & Selesai' di popup Input Hasil -- operator cukup
        satu ketukan. Validasi hasil/QC tetap dijalankan oleh action_done_line."""
        self.ensure_one()
        return self.action_done_line()

    @api.multi
    def action_save_result(self):
        """Tombol Simpan di popup Input Hasil. Odoo 10 tidak mengenal
        special="save" (tombol tanpa type dianggap workflow, jadi error
        exec_workflow), jadi pakai tombol object biasa: record sudah
        otomatis tersimpan sebelum method ini dipanggil, tinggal tutup popup."""
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_done_line(self):
        """Operator tandai tahap ini selesai -- lewat write() supaya gating
        QC (lihat write() override di bawah) dan permintaan validasi SPV
        (kalau ini baris terakhir yang belum Done) sama-sama berjalan."""
        for rec in self:
            rec.with_context(line_internal=True).write({'state': 'done'})
            if not rec.date_end:
                rec.with_context(line_times_internal=True).write(
                    {'date_end': fields.Datetime.now()})
        # Begitu satu tahap Done, tombol Mulai di tahap berikutnya (can_start)
        # dan tombol Ajukan Validasi di header OK perlu ikut berubah. Klien
        # Odoo 10 cuma me-refresh baris yang diklik, bukan baris lain / header,
        # jadi form OK dibuka ulang supaya langsung ter-update tanpa F5.
        if self.env.context.get('operator_board'):
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        if len(self.mapped('ok_id')) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'lpj.production.ok',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.mapped('ok_id').id,
                'target': 'current',
            }
        return True

    @api.multi
    def write(self, vals):
        if self.env.context.get('operator_board') and len(vals) == 1 and \
                not self.env.context.get('line_internal') and \
                ('workcenter_id' in vals or 'state' in vals):
            raise UserError(_(
                "Kartu tidak bisa dipindah dengan digeser. Gunakan tombol "
                "Mulai / Selesai di kartu."))
        if vals.get('state') not in ('in_progress', 'done') and any(
                f in vals for f in ('date_start', 'date_end', 'meter_lari', 'qty_pcs')):
            for rec in self:
                if rec.state == 'draft':
                    raise UserError(_(
                        "Tahap '%s' belum dimulai -- Start, End, Meter Lari dan "
                        "Qty Pcs baru bisa diisi setelah tombol Mulai diklik.")
                        % (rec.workcenter_group_id.name or '-'))
        if ('date_start' in vals or 'date_end' in vals) and \
                not self.env.context.get('line_times_internal') and \
                not self._user_can_edit_times():
            raise UserError(_(
                "Start / End hanya boleh diubah manual oleh PPIC, "
                "Supervisor atau Manager Produksi."))
        if vals.get('state') == 'in_progress':
            self.filtered(lambda r: r.state != 'in_progress')._check_ready_to_start(vals)
        if vals.get('state') == 'done':
            self._check_result_filled()
            for rec in self:
                if not rec._qc_required_and_cleared():
                    raise UserError(_(
                        "Tidak bisa menandai tahap '%s' selesai -- checklist QC "
                        "untuk kategori proses ini masih ada aktivitas yang "
                        "belum dikonfirmasi. Isi & konfirmasi checklist-nya dulu."
                    ) % (rec.workcenter_group_id.name or '-'))
        res = super(ProductionOkLine, self).write(vals)
        if 'meter_lari' in vals:
            for rec in self:
                if not rec.qty_pcs:
                    qty = rec._calc_qty_pcs_from_meter()
                    if qty:
                        rec.qty_pcs = qty
        # PENTING -- SENGAJA TIDAK auto-pindah ke "Menunggu Validasi SPV" di
        # sini lagi begitu baris terakhir Done. OK header tetap di
        # 'in_progress'; tombol 'Ajukan Validasi' di header (lihat
        # all_lines_done & action_request_validation) yang baru MUNCUL
        # setelah semua baris Done, dan PIC/SPV yang klik tombol itu secara
        # sadar -- bukan auto-skip tanpa ada yang lihat/konfirmasi dulu.
        return res

    @api.multi
    def action_open_qc_checklist(self):
        """Tombol 'Isi Checklist' -- kalau sudah ada checklist yang selesai
        (done), buka checklist ITU (mode lihat), JANGAN buat baru. Kalau
        ada draft yang belum selesai, lanjutkan draft itu. Cuma kalau
        benar-benar belum pernah ada checklist sama sekali, baru dibuatkan
        baru (auto-populate aktivitas dari master lpj.qc.item.template
        sesuai KATEGORI proses baris ini). Tidak perlu menunggu mesin
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
