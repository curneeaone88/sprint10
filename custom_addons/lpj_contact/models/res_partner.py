# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, time, date


class res_partner(models.Model):
    _inherit = 'res.partner'

    x_block_customer = fields.Selection([('no', 'Block'), ('yes', 'Open')], default='no', string="Block Customer", track_visibility="onchange")
    x_toleransi_pengiriman = fields.Float(string="Toleransi Pengiriman %")
    is_mkt = fields.Boolean(string="check mkt", compute="is_mkt_act")
    is_administrator = fields.Boolean(string="Check Admin", compute='is_admin_act')
    x_company_size = fields.Selection([('s', 'Small (0-50 person)'), ('m', 'Medium (50-250 person)'), ('l', 'Large (>250 person)')], string='Company Size')
    x_avg_kebutuhan = fields.Selection(
        [('n', 'none'),('s', 'Small (< Rp.100jt/th)'), ('m', 'Medium (Rp.100jt-Rp.500jt/th)'), ('l', 'Large (Rp.500jt-Rp.2M/th)')
            , ('xl', 'X-Large (>Rp.2M/th)')],
        string='Avg Kebutuhan Label', required = True)
    x_priority = fields.Selection([
        ('0', 'Very Low'),
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Very High'),
        ('5', 'Superuser')],
        string='Priority')
    x_status = fields.Selection([
        ('New', 'New'),
        ('Existing', 'Existing')],
        string='Status Customer', default = 'New')
    x_industry = fields.Selection([
        ('food', 'Food and Beverage'),
        ('healthy', 'Farmasi and Healthcare'),
        ('goverment', 'Goverment / Military / Education'),
        ('pariwisata', 'Pariwisata'),
        ('garment', 'Garment'),
        ('huseware', 'Huseware'),
        ('personalcare', 'Personal Care'),
        ('tambang', 'Tambang / Chemical'),
        ('manufacturing', 'Manufacturing / Export Import'),
        ('technology', 'Technology'),
        ('cargo', 'Cargo / Pengiriman')], default='food', string="Bidang Industri", required=True)
    x_jumlah_karyawan = fields.Selection([
        ('less', '< 100 Karyawan'),
        ('small', '100 - 300 Karyawan'),
        ('medium', '301 - 500 Karyawan'),
        ('large', '501 - 1000 Karyawan'),
        ('too_much', '> 1000 Karyawan')], default='less', string="Jumlah Karyawan")
    jalan = fields.Char(string="Jalan")
    x_block_pengiriman = fields.Selection([('block', 'Block'), ('open', 'Open')], default='open', string="Block Pengiriman", track_visibility="onchange")
    x_kebutuhan_pengiriman_ids = fields.Many2many('x.kebutuhan.pengiriman', string="Kebutuhan Pengiriman", readonly=True)
    is_berikat = fields.Char('berikat')
    x_kebutuhan_pengiriman = fields.Text(string="Informasi Detail Pengiriman")
    x_target = fields.One2many('x.target.monthly', 'x_contact')

    # uswa-tambah ini 23/10/2020
    x_detail_penagihan  = fields.Text(string="Detail Penagihan")
    x_detail_product_quality = fields.Text(string="Kualitas Produk")

    # akbar tambah 11/08/2021
    x_estimasi_total_penjualan = fields.Integer(string="Estimasi Total Penjualan (pcs)", required=True)
    x_foto_produk_utama = fields.Binary(string="Produk Utama Customer")
    x_estimasi_length = fields.Float(string="Estimasi Length Produk Utama (mm)")
    x_estimasi_width = fields.Float(string="Estimasi Width Produk Utama (mm)")
    x_analisa_kompetitor = fields.Text(string="Analisa Kompetitor")

    # akbar tambah 05/04/2021
    x_block_OK = fields.Selection([('block', 'Block'), ('open', 'Open')],
                                  default='block', string="Block OK", track_visibility="onchange")
    # akbar tambah 30/04/2021
    x_id_cus_zoho = fields.Char('ID Zoho CRM')

    # Ammar tambah ini 10/06/2021
    x_block_customer_date = fields.Date(string="Last Update Block Customer", compute="insert_date_block_cust", store=True)
    x_block_pengiriman_date = fields.Date(string="Last Update Block Pengiriman", compute="insert_date_block_pengiriman", store=True)
    x_block_OK_date = fields.Date(string="Last Update Block OK", compute="insert_date_block_ok", store=True)
    x_name_jurnal = fields.Char(string="Customer In JurnalID", store=True)

    # Cek apakah user login adalah marketing
    @api.one
    def is_mkt_act(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user:
            id = res_user.id
            # Jika yg login pak fahrur atau ikawati
            # if id == 20 or id == 124:
            if res_user.has_group('account.group_account_manager'):
                self.is_mkt = False

            elif res_user.has_group('sales_team.group_sale_salesman') or \
                    res_user.has_group('sales_team.group_sale_salesman_all_leads'):  # or \
                    # id == 8:
                self.is_mkt = True

            else:
                self.is_mkt = False

    # Cek apakah user login adalah administrator
    @api.one
    def is_admin_act(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('base.group_system'):
            self.is_administrator = True
        else:
            self.is_administrator = False


    # Function for update x_block_customer untuk SO
    @api.multi
    def write(self, vals):
        res = super(res_partner, self).write(vals)

        for partner in self:
            partner_name = partner.name
            sale_order = self.env['sale.order'].search(
                [('state', 'in', ['draft', 'sent']), ('partner_id', '=', partner_name)])
            if sale_order:
                for sale_order_new in sale_order:
                    block_customer = partner.x_block_customer
                    if block_customer == 'no':
                        sale_order_new.update({'is_block': 'no'})
                    if block_customer == 'yes':
                        sale_order_new.update({'is_block': 'yes'})
                return res

            else:
                return res

	# Ammar tambah ini 10/06/2021
	# Function Onchange block Customer, block Pengiriman, dan block OK
    @api.depends('x_block_customer')
    def insert_date_block_cust(self):
        for row in self:
	        today = date.today()
	        row.x_block_customer_date = today

    @api.depends('x_block_pengiriman')
    def insert_date_block_pengiriman(self):
        for row in self:
            today = date.today()
            row.x_block_pengiriman_date = today

    # @api.depends('x_block_OK')
    # def insert_date_block_ok(self):
    #     for row in self:
	#         today = date.today()
	#         row.x_block_OK_date = today


class KebutuhanPengiriman(models.Model):
    _name = 'x.kebutuhan.pengiriman'

    name = fields.Char('Kebutuhan Pengiriman')


class target_perbulan(models.Model):
    _name = 'x.target.monthly'
    x_contact = fields.Many2one('res.partner', string='Target Sales')
    name = fields.Char(string = 'Bulan', compute='bulan_tahun', store=True)
    x_tgl = fields.Datetime(string = 'Target Deadline')
    x_target_m2 = fields.Float(string='Target M2')
    x_target = fields.Float(string = 'Target Nominal')
    x_description = fields.Char(string = 'Keterangan')

    @api.depends("x_tgl")
    def bulan_tahun(self):
        if self.x_tgl:
            date_format = "%Y-%m-%d %H:%M:%S"
            tgl_default = datetime.strptime(str(self.x_tgl), date_format)
            self.name = tgl_default.strftime('%B-%Y')
