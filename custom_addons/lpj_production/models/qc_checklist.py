# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductionQcChecklist(models.Model):
    """Checklist QC terpisah per tahap (per OK Line), bukan tab statis di
    form OK -- lihat diskusi desain: aktivitas QC beda-beda tiap mesin,
    dan satu tahap bisa diulang (reject -> reproses) sehingga butuh record
    tersendiri, bukan field yang menempel langsung ke OK.

    Diakses dari dua arah:
    - Kontekstual: tombol "Isi Checklist" per baris di tab Routing pada OK
      (muncul sebagai popup, lihat production_ok.py: action_open_qc_checklist).
    - Overview: smart button "Checklist QC" di header OK (lihat production_ok.py).
    """
    _name = 'lpj.production.qc.checklist'
    _description = 'Checklist Kualitas (QC) per Tahap'
    _order = 'id desc'
    _rec_name = 'display_name'

    ok_line_id = fields.Many2one(
        'lpj.production.ok.line', string='OK Line', required=True,
        ondelete='cascade', index=True)
    ok_id = fields.Many2one(
        'lpj.production.ok', string='Order Kerja',
        related='ok_line_id.ok_id', store=True, readonly=True)
    workcenter_group_id = fields.Many2one(
        'lpj.workcenter.group', string='Kategori Tahapan',
        related='ok_line_id.workcenter_group_id', store=True, readonly=True)
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Mesin',
        related='ok_line_id.workcenter_id', store=True, readonly=True,
        help="Mesin fisik yang mengerjakan tahap ini (informasi saja, bukan "
             "sumber aktivitas QC -- aktivitas QC berasal dari kategori "
             "tahapan/workcenter_group_id, dipakai bersama semua mesin "
             "sejenis).")
    display_name = fields.Char(compute='_compute_display_name', store=False)

    qc_inspector_id = fields.Many2one(
        'res.users', string='QC Inspector', default=lambda self: self.env.user,
        help="Orang yang melakukan pengecekan QC -- BUKAN operator mesin "
             "(lihat lpj.production.ok.line.operator_id yang terpisah). "
             "Hanya user di grup QC Inspector/Supervisor/Manager yang bisa "
             "mengisi & mengonfirmasi checklist ini (lihat security.xml).")
    date_check = fields.Datetime(string='Tanggal Pengecekan', default=fields.Datetime.now)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Selesai'),
    ], string='Status', default='draft', readonly=True, copy=False)

    item_ids = fields.One2many(
        'lpj.production.qc.checklist.item', 'checklist_id', string='Aktivitas QC')

    result_summary = fields.Selection([
        ('pending', 'Belum Lengkap'),
        ('ok', 'Sesuai (atau Tidak Berlaku)'),
        ('not_ok', 'Ada yang Tidak Sesuai'),
    ], string='Ringkasan Hasil', compute='_compute_result_summary', store=True)

    notes = fields.Text(string='Catatan')

    @api.multi
    @api.depends('ok_line_id', 'ok_line_id.workcenter_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = u"%s - %s" % (
                rec.ok_line_id.ok_id.name or '',
                rec.workcenter_id.name or rec.workcenter_group_id.name or '')

    @api.multi
    @api.depends('item_ids.result')
    def _compute_result_summary(self):
        """'none' (tidak berlaku untuk job ini) dihitung sebagai 'sudah
        diisi' dan tidak mempengaruhi hasil akhir -- cuma 'not_ok' yang
        bikin ringkasan jadi gagal. Yang masih kosong (belum dipilih sama
        sekali) baru dianggap 'pending'."""
        for rec in self:
            results = rec.item_ids.mapped('result')
            if not results or any(r == False for r in results):
                rec.result_summary = 'pending'
            elif any(r == 'not_ok' for r in results):
                rec.result_summary = 'not_ok'
            else:
                rec.result_summary = 'ok'

    @api.multi
    def action_confirm_checklist(self):
        """Operator konfirmasi checklist selesai diisi -- ini yang berfungsi
        sebagai pengganti tanda tangan kertas (Bagian 3.4 PRD). Semua
        aktivitas wajib dipilih statusnya dulu -- termasuk yang 'None' kalau
        memang tidak berlaku, tidak boleh dibiarkan kosong."""
        for rec in self:
            if any(not item.result for item in rec.item_ids):
                from odoo.exceptions import UserError
                raise UserError(u"Masih ada aktivitas QC yang belum diisi hasilnya "
                                 u"(pilih OK, Not OK, atau None kalau tidak berlaku).")
            rec.write({
                'state': 'done',
                'qc_inspector_id': self.env.user.id,
                'date_check': fields.Datetime.now(),
            })
        return True


class ProductionQcChecklistItem(models.Model):
    """Satu baris = satu AKTIVITAS pengecekan (bukan produk/barang), mis.
    'Cek Warna', 'Cek Bleeding'. Hasilnya salah satu dari 3 opsi:
    - OK: aktivitas dicek dan sesuai.
    - Not OK: aktivitas dicek dan tidak sesuai.
    - None: aktivitas ini tidak berlaku untuk job/produk ini (mis. produk
      tertentu yang lewat mesin ini memang tidak perlu dicek hal tersebut).
    """
    _name = 'lpj.production.qc.checklist.item'
    _description = 'Aktivitas QC'
    _order = 'sequence, id'

    checklist_id = fields.Many2one(
        'lpj.production.qc.checklist', string='Checklist', required=True, ondelete='cascade')
    item_template_id = fields.Many2one('lpj.qc.item.template', string='Referensi Aktivitas QC')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Aktivitas QC', required=True)
    result = fields.Selection([
        ('ok', 'OK (QC Pass)'),
        ('not_ok', 'Not OK'),
        ('none', 'None (Tidak Berlaku)'),
    ], string='Hasil')
    note = fields.Char(string='Catatan')
