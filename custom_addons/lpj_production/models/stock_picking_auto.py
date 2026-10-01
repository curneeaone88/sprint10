# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductionOkStockPicking(models.Model):
    """Auto stock.picking saat OK divalidasi Done oleh SPV, tanpa perlu
    orang klik validasi manual -- jawaban atas pertanyaan:
    'stock picking tetap ada tapi jalan otomatis lewat trigger'.

    ADA DUA PICKING yang dibuat:
    1. picking_id -- barang jadi MASUK ke stok (Production -> Stock Utama).
    2. material_picking_id -- bahan baku KELUAR dari stok (Stock Utama ->
       Production), qty dari BOM (product.template.bom_line_ids) x jumlah
       layout (Total Meter Lari / Panjang per Layout). Cuma dibuat kalau
       produknya punya BOM.

    PENTING -- BELUM FINAL, PERLU DIKONFIRMASI BERSAMA:
    - Location source/destination masih placeholder (satu lokasi virtual
      Production & satu lokasi stock utama warehouse default dipakai
      BOLAK-BALIK untuk kedua arah picking) -- belum ada pemisahan
      sub-lokasi raw-material vs finished-goods. Perlu dicek ke konfigurasi
      Warehouse/Location riil Sprint sebelum dipakai di produksi.
    - Picking type juga masih fallback ke 'internal' milik warehouse default
      untuk KEDUA arah; idealnya dibuatkan stock.picking.type terpisah
      ("Hasil Produksi" & "Konsumsi Bahan Produksi") supaya gampang
      dibedakan dari SJK (pengiriman ke customer) yang sudah ada di
      lpj_inventory, dan dari satu sama lain di laporan.
    Jangan di-enable ke live server sebelum hal di atas dikonfirmasi.
    """
    _inherit = 'lpj.production.ok'

    def _get_production_location(self):
        return self.env.ref('stock.location_production', raise_if_not_found=False)

    def _get_finished_goods_location(self):
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.user.company_id.id)], limit=1)
        return warehouse.lot_stock_id if warehouse else False

    def _get_production_picking_type(self):
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.user.company_id.id)], limit=1)
        return warehouse.int_type_id if warehouse else False

    @api.multi
    def _trigger_auto_stock_picking(self):
        for rec in self:
            if rec.picking_id:
                continue  # sudah pernah dibuat, jangan dobel
            if not rec.qty_production:
                continue
            rec._create_and_validate_picking()

    @api.multi
    def _create_and_validate_picking(self):
        self.ensure_one()
        src_location = self._get_production_location()
        dst_location = self._get_finished_goods_location()
        picking_type = self._get_production_picking_type()

        if not (src_location and dst_location and picking_type):
            # Sengaja tidak raise error keras supaya OK tetap bisa selesai
            # dicatat meski konfigurasi lokasi/picking type belum lengkap --
            # cukup catat di notes supaya kelihatan perlu ditindaklanjuti.
            self.message_post(
                body=_("Auto stock.picking belum dibuat: konfigurasi lokasi/"
                       "picking type produksi belum lengkap. Perlu dicek manual."))
            return False

        picking_vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': src_location.id,
            'location_dest_id': dst_location.id,
            'origin': self.name,
            'move_lines': [(0, 0, {
                'name': self.product_id.display_name,
                'product_id': self.product_id.id,
                'product_uom_qty': self.qty_production,
                'product_uom': self.product_id.uom_id.id,
                'location_id': src_location.id,
                'location_dest_id': dst_location.id,
            })],
        }
        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()
        picking.action_assign()
        self._force_pack_operations_done(picking)
        # Odoo 10: do_transfer() memvalidasi picking secara langsung (tanpa
        # wizard "Immediate Transfer" yang biasanya muncul di UI manual).
        picking.do_transfer()

        self.picking_id = picking.id
        self.message_post(
            body=_("Barang jadi %s pcs otomatis masuk stok via %s.")
            % (self.qty_production, picking.name))
        return picking

    # ==== Konsumsi Bahan Baku (BOM) ====

    @api.multi
    def _get_material_consumption(self):
        """Hitung qty tiap bahan baku dari BOM produk: basis TUNGGAL per
        layout (lihat models/product_bom.py) -- qty_per_unit (per 1 layout)
        x jumlah layout OK ini (_get_jumlah_layout()).
        Return list of dict: [{'product': product.product, 'qty': float}, ...]."""
        self.ensure_one()
        result = []
        bom_lines = self.product_id.product_tmpl_id.bom_line_ids
        if not bom_lines:
            return result
        jumlah_layout = self._get_jumlah_layout()
        for line in bom_lines:
            qty = line.qty_per_unit * jumlah_layout
            if qty:
                result.append({'product': line.material_product_id, 'qty': qty})
        return result

    @api.multi
    def _trigger_auto_material_picking(self):
        for rec in self:
            if rec.material_picking_id:
                continue  # sudah pernah dibuat, jangan dobel
            consumption = rec._get_material_consumption()
            if not consumption:
                continue  # produk ini belum punya BOM -- tidak apa, dilewati saja
            rec._create_and_validate_material_picking(consumption)

    @api.multi
    def _create_and_validate_material_picking(self, consumption):
        self.ensure_one()
        # Arah kebalikan dari picking barang jadi: dari gudang bahan baku
        # KE lokasi virtual Production (bahan "hilang" dipakai produksi).
        src_location = self._get_finished_goods_location()  # gudang utama
        dst_location = self._get_production_location()  # virtual Production
        picking_type = self._get_material_picking_type()

        if not (src_location and dst_location and picking_type):
            self.message_post(
                body=_("Auto stock.picking bahan baku belum dibuat: konfigurasi "
                       "lokasi/picking type belum lengkap. Perlu dicek manual."))
            return False

        allow_negative = self.env.user.company_id.x_allow_negative_stock_production
        move_lines = []
        shortage_notes = []
        for item in consumption:
            material = item['product']
            qty_needed = item['qty']
            available = material.with_context(location=src_location.id).qty_available
            if qty_needed > available:
                if not allow_negative:
                    raise UserError(_(
                        "Stok bahan '%s' tidak cukup (tersedia %.2f, dibutuhkan %.2f) "
                        "dan pengaturan Company tidak mengizinkan stok minus. "
                        "Isi ulang stok dulu, atau aktifkan 'Izinkan Stok Minus saat "
                        "Transfer Bahan Produksi' di Settings kalau memang perlu."
                    ) % (material.display_name, available, qty_needed))
                shortage_notes.append(
                    u"- %s: tersedia %.2f, dipakai %.2f (MINUS %.2f)" % (
                        material.display_name, available, qty_needed, qty_needed - available))
            move_lines.append((0, 0, {
                'name': material.display_name,
                'product_id': material.id,
                'product_uom_qty': qty_needed,
                'product_uom': material.uom_id.id,
                'location_id': src_location.id,
                'location_dest_id': dst_location.id,
            }))

        picking = self.env['stock.picking'].create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': src_location.id,
            'location_dest_id': dst_location.id,
            'origin': self.name,
            'move_lines': move_lines,
        })
        picking.action_confirm()
        picking.action_assign()
        self._force_pack_operations_done(picking)
        picking.do_transfer()

        self.material_picking_id = picking.id
        self.message_post(
            body=_("Bahan baku otomatis keluar dari stok via %s (BOM x jumlah layout)."
                   ) % picking.name)
        if shortage_notes:
            # REMINDER sesuai pengaturan "boleh minus" -- dicatat di chatter
            # supaya kelihatan, bukan wizard/popup (biar tidak mengganggu
            # alur validasi yang sudah jalan).
            self.message_post(body=_(
                "<b>Reminder: stok bahan minus setelah transfer ini</b><br/>%s"
            ) % u'<br/>'.join(shortage_notes))
        return picking

    def _get_material_picking_type(self):
        """Sengaja BEDA dari _get_production_picking_type() (yang dipakai
        barang jadi) -- fallback ke tipe internal yang sama untuk sekarang,
        tapi kalau nanti mau dipisah jadi picking type khusus 'Konsumsi
        Bahan Produksi', cukup override method ini."""
        return self._get_production_picking_type()

    def _force_pack_operations_done(self, picking):
        """PENYEBAB 'barang jadi 0 di stock picking': do_transfer() di
        Odoo 10 memindahkan qty berdasarkan pack_operation_ids.qty_done
        (qty yang BENAR-BENAR selesai dipindah), BUKAN move_lines.
        product_uom_qty (qty rencana). action_assign() memang membuat
        pack_operation_ids, tapi qty_done-nya default 0 (menunggu user
        isi manual di UI) -- karena alur kita full-otomatis (tidak ada
        orang klik apa-apa), qty_done itu harus dipaksa terisi di sini
        SEBELUM do_transfer() dipanggil, atau picking akan 'selesai'
        tapi actual qty yang berpindah tetap 0.

        Juga jaga-jaga: kalau action_assign() tidak menghasilkan
        pack_operation_ids sama sekali (bisa terjadi untuk lokasi virtual
        seperti Production yang tidak punya quant nyata untuk
        direservasi), buat manual dari move_lines."""
        if picking.pack_operation_ids:
            for operation in picking.pack_operation_ids:
                operation.write({'qty_done': operation.product_qty})
        else:
            for move in picking.move_lines:
                self.env['stock.pack.operation'].create({
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'product_qty': move.product_uom_qty,
                    'qty_done': move.product_uom_qty,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                })
