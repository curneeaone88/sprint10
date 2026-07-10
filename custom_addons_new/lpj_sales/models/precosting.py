# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, time
import odoo.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import requests
import json


class Precosting(models.Model):
    _name = 'x.sales.quotation'
    _inherit = 'mail.thread'

    # untuk memunculkan currency rupiah
    @api.multi
    def _compute_currency_id(self):
        main_company = self.env['res.company'].sudo().search([], limit=1, order="id")
        for template in self:
            template.currency_id = main_company.currency_id.id

    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id')

    name = fields.Char(string='Code SQ')
    x_product = fields.Many2one('product.product', string='Product Name', domain=[('sale_ok', '=', True)],
                                track_visibility='onchange', required=True)
    x_product_tmpl = fields.Many2one('product.template', string='Product Template', domain=[('sale_ok', '=', True)],
                                     track_visibility='onchange')
    x_quotation_id = fields.Many2one('sale.order')
    item_description = fields.Char(string='Item Name', track_visibility='onchange')
    x_repeat_order = fields.Boolean(default=False, string='Repeat Order')
    description = fields.Text(string='Description', track_visibility='onchange')
    # x_desc_sq = fields.Text(string='Description')
    x_status_cr = fields.Selection(
        [('draft', 'Draft'), ('SPV', 'Need Approval SPV'), ('approve', 'Approve'), ('done', 'Done'),
         ('reject', 'Reject')],
        default='draft', string='Status SQ', readonly=True)
    # x_sales_id = fields.Many2one('res.partner', string='Sales',
    #                              domain=[('customer', '=', False), ('supplier', '=', False)])
    x_sales_id = fields.Many2one('res.users', string='Sales', default=lambda self: self.env.user, domain=[('customer', '=', False), ('supplier', '=', False)])
    x_customer_id = fields.Many2one('res.partner', string='Customer', domain=[('customer', '=', True)])
    x_request_date = fields.Date(string='Request Date', store=True, readonly=True, default=datetime.now())
    x_duedate_drawing = fields.Datetime(string='Due Date Drawing', default=datetime.now())
    x_qty = fields.Integer('Qty (pcs)', required=True, track_visibility='onchange')

    x_length = fields.Float('Length (mm)', required=True, track_visibility='onchange')
    x_width = fields.Float('Width (mm)', required=True, track_visibility='onchange')
    x_length_m = fields.Float(store=True, digits=dp.get_precision('Payment Terms'))
    x_width_m = fields.Float(store=True, digits=dp.get_precision('Payment Terms'))
    # x_packing_category_id = fields.Many2one('x.packing.category', 'Packing Category')
    x_satuan = fields.Selection([('roll', 'Roll Standard'), ('rollc', 'Roll Custom'), ('sheet', 'Sheet - Kisscut Standard'), ('sheetfs', 'Sheet - Fullcut Standard')
                                    , ('sheetfc', 'Sheet - Fullcut Custom'), ('sheetkc', 'Sheet - Kisscut Custom')], string='Satuan',
                                Default='sheet', required=True, track_visibility='onchange')
    x_supplier_id = fields.Many2one('res.partner', string='Suplier', domain=[('supplier', '=', True)])
    x_material_type_id = fields.Many2one('product.template', 'Material Type',
                                         domain=[('categ_id.sts_bhn_utama.name', '=', 'Bahan Utama')])
    x_material_type_id2 = fields.Many2one('x.config.bahan', 'Material Type', required=True, store=True, track_visibility='onchange')
    x_numbers_of_colors = fields.Integer('Number Of Color', track_visibility='onchange')
    x_numbers_of_colors2 = fields.Many2one('x.config.tinta', 'Number Of Color', required=True, store=True, default=14)
    x_varnish = fields.Boolean('Varnish')
    x_special_color = fields.Boolean('Special Color')
    x_ink_coverage = fields.Selection([('0.0', '0.0'), ('0.25', '0.25'), ('0.5', '0.5'), ('0.75', '0.75'), ('1', '1')],
                                      string='Ink Coverage')

    # x_mrpwordkcenter_id = fields.Many2one('mrp.workcenter', 'Prime Machine', default=1)
    x_lamination = fields.Boolean('Lamination')
    x_category_foil = fields.Many2one('x.category.finishing.process', string='Category Foil')
    x_reg_cr_mkt = fields.Boolean('Request Color Range', track_visibility='onchange')
    x_jumlah_cr_mkt = fields.Integer('Request Color Range Count')

    # x_reg_cr_pde = fields.Boolean('Request Color Range', related="x_product.x_reg_cr_pde_m")
    # x_jumlah_cr_pde = fields.Integer('Request Color Range Count', related="x_product.x_jumlah_cr_pde_m")
    start_of_date = fields.Date(string='Price Start Date', readonly=True)
    end_of_date = fields.Date(string='Price End Date', compute='end_date_function')
    compute_field = fields.Boolean(string="check field", compute="get_user")
    x_is_salemanager = fields.Boolean(string="check field apakah sales manager", compute="cek_sales_manager")
    x_price_low = fields.Float('Price Low', digits=dp.get_precision('Prroduct Price'))
    x_price_high = fields.Float('Price High', digits=dp.get_precision('Prroduct Price'))
    x_price_low_digital = fields.Float('Price Low', digits=dp.get_precision('Prroduct Price'))
    x_price_high_digital = fields.Float('Price High', digits=dp.get_precision('Prroduct Price'))
    x_price_fix = fields.Float('Price Approve', digits=dp.get_precision('Prroduct Price'), track_visibility='onchange')
    x_price_fix_odoo = fields.Float('Price Approve Odoo', digits=dp.get_precision('Prroduct Price'))
    x_hpp = fields.Float('HPP', readonly=True, digits=dp.get_precision('Prroduct Price'))
    x_harga_repeat = fields.Float(readonly=True, string='Harga Repeat')
    x_req_dk = fields.Datetime(string='Request Duedate Kirim', track_visibility='onchange', required=True)
    # x_req_dk_digital = fields.Datetime(related='x_req_dk', compute='default_duedate')
    # x_req_dk_pertama = fields.Datetime(string='Request Duedate Kirim Pertama', track_visibility='onchange', required=True)
    x_req_dk_marketing = fields.Datetime(string='Request Duedate Kirim Marketing', invisible=True)
    x_tgl_request = fields.Datetime(string='Tanggal Request', readonly=True)
    x_flag_reqdk = fields.Boolean(string='Sudah Direquest dk ?', default=False)
    x_flag_appdk = fields.Boolean(string='Sudah Diapprove dk ?', default=False)
    x_is_salemanager = fields.Boolean(string="check field apakah sales manager", compute="cek_sales_manager")
    x_status_dk = fields.Selection(
        [('draft', 'Draft'), ('requested', 'Requested'), ('reject', 'Reject'), ('approve', 'Approve')],
        default='draft', string='Status Request Duedate Kirim', readonly=True, track_visibility='onchange')
    x_manufacturing_type = fields.Selection([('laprint', 'Laprint'), ('digital', 'Digital')],
                                            default='laprint', string='Manufacturing Type',
                                            track_visibility='onchange', required=True)
    x_planning_type = fields.Selection([('forward', 'Forward Planning'), ('backward', 'Backward Planning')],
                                       default='forward', string='Planning Type',
                                       track_visibility='onchange', required=True)
    x_harga_renego = fields.Float('Harga SQ', digits=dp.get_precision('Prroduct Price'), track_visibility='onchange')
    x_state_renego = fields.Selection(
        [('1', 'Draft'), ('2', 'Precost'), ('5', 'Approval SPV'), ('3', 'Approval GM'),
         ('6', 'Approve'), ('7', 'Reject'), ('8', 'Dibawah MOQ')], default='1')
    x_range_price_sq = fields.One2many('x.range.price.sq', 'x_sq')
    x_range_price_sq2 = fields.One2many('x.range.price.sq', 'x_sq')
    x_history_sq = fields.One2many('x.history.sq', 'x_sq')
    x_summary_precosting = fields.One2many('x.summary.precosting', 'x_sq', string="Summary Precosting")
    x_summary_precosting2 = fields.One2many('x.summary.precosting', 'x_sq', string="Summary Precosting")
    x_summary_precosting_low = fields.One2many('x.summary.precosting.low', 'x_sq', string="Summary Precosting Low")
    x_summary_precosting_high = fields.One2many('x.summary.precosting.high', 'x_sq', string="Summary Precosting High")
    x_cek_administrator = fields.Boolean(compute="get_id")
    x_cek_dir = fields.Boolean(compute="get_id2")
    x_product_type_precost = fields.Many2one('x.product.type.precost', string="Product Type",
                                                required=True, track_visibility='onchange', domain=[('x_is_active', '=', True)],
                                                default=2)
    x_nama_product = fields.Char(string="Product Type", related='x_product_type_precost.name', store=True,
                                 readonly=True)
    x_ids_feature = fields.Many2many('x.feature.cost.precost', string="Feature", required=True, track_visibility='onchange')

    x_tgl_plan_drawing = fields.Date('Plan Drawing')
    x_tgl_plan_layout = fields.Date('Plan Layout')
    x_tgl_plan_unlock = fields.Date('Plan Unlock')
    x_flag_quo = fields.Boolean(string='Internal Quotation', default=False)
    # akbar tambah 27/4/2021 untuk flag kalkulator
    x_flag_kalkulator = fields.Boolean('Kalkulator')
    # x_code_deals_zoho = fields.Char(string="Kode Deals Zoho")
    # x_id_deals_zoho = fields.Char(string="ID Deals Zoho")
    # x_id_contact_zoho = fields.Char(string="ID Contact Zoho")
    x_bentuk_prod = fields.Many2one('x.config.bentuk2', string="Bentuk", track_visibility='onchange')
    x_ids_feature2 = fields.Html('Deskripsi Feature', compute='_default_desc')
    x_roll_type = fields.Many2one('x.config.rolltype', string="Type Roll", required=True, track_visibility='onchange')


    @api.one
    def _default_desc(self):
        self.env.cr.execute(
            "select name, x_deskripsi from x_feature_cost_precost order by id")
        sql = self.env.cr.fetchall()
        temp = ""
        for o in sql:
            temp1 = '<b>' + str(o[0]) + '</b>' + ' : ' + str(o[1])
            temp = ''.join([temp, str(temp1), '<br>'])

        self.x_ids_feature2 = temp

    # date_invoice = fields.Date(string='Invoice Date', readonly=True, states={'draft': [('readonly', False)]},
    #                            index=True, help="Keep empty to use the current date", copy=False, default=_default_date)

    x_category_precost = fields.Integer(string='Kategori')
    x_price_level = fields.One2many('x.price.level', 'x_sq')
    x_history_win = fields.One2many('x.history.sq.win', 'x_sq', string="History Win")
    x_history_lost = fields.One2many('x.history.sq.lost', 'x_sq', string="History Lost")
    x_history_pending = fields.One2many('x.history.sq.pending', 'x_sq', string="History Pending")
    x_hpp_pcs = fields.Float('Hpp pcs', compute="get_hpp", store=True)
    x_hpp_m2 = fields.Float('Hpp m2', compute="get_hpp", store=True)
    x_qty_m2 = fields.Float('Qty m2', compute="get_hpp", store=True)
    x_area_m2_tot = fields.Float(string='Total Area m2', store=True)
    x_area_m2_tot2 = fields.Float(string='Total Area m2', related='x_area_m2_tot', readonly=True)
    x_waste_produksi = fields.Float(string='Waste Produksi (%)', store=True)
    x_waste_produksi_m2 = fields.Float(string='Waste Produksi m2', store=True)
    x_waste_config = fields.Float(string='Waste Config (%)', store=True)
    x_waste_config_m2 = fields.Float(string='Waste Config m2', store=True)
    x_total_waste_m2 = fields.Float(string='Total Waste m2', store=True)

    x_price_total = fields.Float('Harga Standart Total', compute="get_hpp", store=True)
    x_price_renego_low_digital = fields.Integer('Harga Batas Renego (0,8 * Price Low)', compute="get_hpp")
    x_profit_standart = fields.Char('Profit Standart', compute="get_hpp", store=True)
    x_profit_standart_numeric = fields.Float('Profit Standart (%)', compute="get_hpp", store=True)
    x_renego_total = fields.Float('Harga Renego Total', compute="get_hpp", store=True)
    x_profit_renego = fields.Char('Profit Renego', compute="get_hpp", store=True)
    x_profit_renego_numeric = fields.Float('Profit Renego (%)', compute="get_hpp", store=True)
    x_m2_standart = fields.Integer('Harga Std/m2', compute="get_hpp", store=True)
    x_m2_renego = fields.Integer('Harga Renego/m2', compute="get_hpp", store=True)
    x_harga_renego2 = fields.Float('Harga SQ', digits=dp.get_precision('Prroduct Price'), related="x_harga_renego",
                                   readonly=True)
    x_harga_renego_sales = fields.Float('Harga Renego Sales', digits=dp.get_precision('Prroduct Price'), readonly=True)
    x_renego_total2 = fields.Float('Harga Renego Total', related="x_renego_total", readonly=True)
    x_profit_renego2 = fields.Char('Profit Renego', related="x_profit_renego", readonly=True)
    x_hpp_total = fields.Integer('Hpp Total', compute="get_hpp", store=True)
    x_price_high2 = fields.Float('Harga Standart/pcs', digits=dp.get_precision('Prroduct Price'),
                                 related="x_price_high", readonly=True)

    x_total_cost_hpp = fields.Integer(string='Total Hpp Cost')
    x_cost_pcs_hpp = fields.Float(string='Hpp Cost (Rp/pcs)')
    x_cost_m2_hpp = fields.Float(string='Hpp Cost (Rp/m2)')

    x_total_cost_low = fields.Integer(string='Total Low Cost')
    x_cost_pcs_low = fields.Float(string='Low Cost (Rp/pcs)')
    x_cost_m2_low = fields.Float(string='Low Cost (Rp/m2)')

    x_total_cost_high = fields.Integer(string='Total High Cost')
    x_cost_pcs_high = fields.Float(string='High Cost (Rp/pcs)')
    x_cost_m2_high = fields.Float(string='High Cost (Rp/m2)')

    x_note_moq = fields.Text(string='Note MOQ',
                             default='Item ini DIBAWAH MOQ m2, cSilahkan Minta Harga Digital Ke Tim Digital')

    x_offering_digital = fields.Many2one('x.offering.cost.precost', string='Offering', required=True, track_visibility='onchange')

    # catur 2022-12-12
    x_variant_sku = fields.Many2one('x.config.multi.variant',string='Jumlah Variant (SKU)',requuired=True,default=1, track_visibility='onchange')
    x_product_list_layout = fields.Text('List Product in Layout', track_visibility='onchange')

    x_flag_onchange = fields.Boolean('flag onchange', default=False)

    x_status_quo_purchase = fields.Selection(
        [('f', 'Dibawah MOQ'), ('t', 'In Range')],
        default='', string='Purchase Status', readonly=True)
    x_quo_purchase_m2 = fields.Float(
        'Purchase Price / m2', digits=dp.get_precision('Prroduct Price'), readonly=True)
    x_quo_purchase_price_pcs = fields.Float(
        'Purchase Price / PCS', digits=dp.get_precision('Prroduct Price'), readonly=True)
    x_quo_profit_prosentase = fields.Float(
        'Prosentase Profit Beli (%)',compute='calc_prosentase_profit' , readonly=True)


    @api.one
    def calc_prosentase_profit(self):

        if self.x_quo_purchase_price_pcs != 0:
            if self.x_harga_renego != 0:
                self.x_quo_profit_prosentase = ((self.x_harga_renego - self.x_quo_purchase_price_pcs) / self.x_harga_renego) * 100

    @api.multi
    def pricing_popup(self):
        # ac = self.env['ir.model.data'].xmlid_to_res_id('lpj_sales.x_sq_popup_view_pricing_gm',
        #                                                raise_if_not_found=True)

        id_sq = self.id
        x_hrg_renego = self.x_harga_renego
        x_renego_tot = self.x_renego_total
        x_profit = self.x_profit_renego
        return {
            'name': 'My Window',
            'domain': [],
            'res_model': 'x.sales.quotation',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('lpj_sales.x_sq_popup_view_pricing_gm', False).id,
            'res_id': id_sq,
            'context': {
                'default_x_harga_renego': x_hrg_renego,
                'default_x_renego_total': x_renego_tot,
                'default_x_profit_renego': x_profit,
            },
            'target': 'new',
        }

    @api.onchange('x_product_type_precost')
    def reset_material_color(self):
        a = self._origin.x_flag_onchange
        if a == True:
            self.x_material_type_id2 = None
            self.x_numbers_of_colors2 = None
        else:
            self.x_flag_onchange = True

    @api.depends('x_harga_renego')
    def get_hpp(self):
        for row in self:
            id = row.id
            if id:
                id2 = row.id
                # if row.x_product_type_precost == 3:
                if "STC DIGITAL" in str(row.x_product_type_precost.name).upper():
                    row.x_qty_m2 = ((row.x_length / 1000) * (row.x_width / 1000) * row.x_qty) / 0.7
                else:
                    row.x_qty_m2 = ((row.x_length / 1000) * (row.x_width / 1000) * row.x_qty) / 0.8
                # row.x_qty_m2 = ((row.x_length / 1000) * (row.x_width / 1000) * row.x_qty) / 0.8
                row.x_renego_total = row.x_harga_renego * row.x_qty
                row.x_price_renego_low_digital = row.x_price_low * 0.8

                row.x_hpp_pcs = row.x_cost_pcs_hpp
                row.x_hpp_m2 = row.x_cost_m2_hpp
                row.x_hpp_total = row.x_total_cost_hpp
                if row.x_harga_renego != 0 and row.x_price_high != 0:
                    # if row.x_product_type_precost.id != 3:
                    if "STC DIGITAL" not in str(row.x_product_type_precost.name).upper():
                        x_profit = round(((row.x_harga_renego - row.x_cost_pcs_hpp) / row.x_harga_renego * 100), 2)
                        row.x_profit_renego = str(x_profit) + " %"
                        row.x_profit_renego_numeric = x_profit
                        x_profit2 = round(((row.x_price_high - row.x_cost_pcs_hpp) / row.x_price_high * 100), 2)
                        row.x_profit_standart = str(x_profit2) + " %"
                        row.x_profit_standart_numeric = x_profit2
                    else:
                        row.x_profit_renego = "-"
                        row.x_profit_renego_numeric = False
                        row.x_profit_standart = "-"
                        row.x_profit_standart_numeric = False

                    row.env.cr.execute(
                        "select round(cast(x_area_m2_tot as numeric), 2), round(cast(x_waste_produksi as numeric), 2), round(cast(x_waste_config as numeric), 2), round(cast(x_total_waste_m2 as numeric), 2) from x_history_precosting "
                        "where x_id_sq = '" + str(id2) + "'")

                    sql2 = row.env.cr.fetchone()
                    if sql2:
                        row.x_m2_renego = row.x_renego_total / sql2[0]

                    # if row.x_product_type_precost.id != 3:
                    if "STC DIGITAL" not in str(row.x_product_type_precost.name).upper():
                        row.x_price_total = row.x_total_cost_high
                        row.x_m2_standart = row.x_cost_m2_high
                    else:
                        price_total = row.x_price_high * row.x_qty
                        row.x_price_total = price_total
                        row.x_m2_standart = price_total / sql2[0]

            else:
                id2 = self._origin.id
                if "STC DIGITAL" in str(self._origin.x_product_type_precost).upper():
                    row.x_qty_m2 = ((self._origin.x_length / 1000) * (
                                self._origin.x_width / 1000) * self._origin.x_qty) / 0.7
                else:
                    row.x_qty_m2 = ((self._origin.x_length / 1000) * (
                                self._origin.x_width / 1000) * self._origin.x_qty) / 0.8
                row.x_renego_total = self.x_harga_renego * self._origin.x_qty
                row.x_price_renego_low_digital = self._origin.x_price_low * 0.8

                row.x_hpp_pcs = self._origin.x_cost_pcs_hpp
                row.x_hpp_m2 = self._origin.x_cost_m2_hpp
                row.x_hpp_total = self._origin.x_total_cost_hpp
                if row.x_harga_renego != 0 and self._origin.x_price_high != 0:
                    # if self._origin.x_product_type_precost.id != 3:
                    if "STC DIGITAL" not in str(self._origin.x_product_type_precost.name).upper():
                        x_profit = round(
                            ((self.x_harga_renego - self._origin.x_cost_pcs_hpp) / self.x_harga_renego * 100), 2)
                        row.x_profit_renego = str(x_profit) + " %"
                        row.x_profit_renego_numeric = x_profit
                        x_profit2 = round(((
                                                       self._origin.x_price_high - self._origin.x_cost_pcs_hpp) / self._origin.x_price_high * 100),
                                          2)
                        row.x_profit_standart = str(x_profit2) + " %"
                        row.x_profit_standart_numeric = x_profit2
                    else:
                        row.x_profit_renego = "-"
                        row.x_profit_renego_numeric = False
                        row.x_profit_standart = "-"
                        row.x_profit_standart_numeric = False

                    row.env.cr.execute(
                        "select round(cast(x_area_m2_tot as numeric), 2), round(cast(x_waste_produksi as numeric), 2), round(cast(x_waste_config as numeric), 2), round(cast(x_total_waste_m2 as numeric), 2) from x_history_precosting "
                        "where x_id_sq = '" + str(id2) + "'")

                    sql2 = row.env.cr.fetchone()
                    if sql2:
                        row.x_m2_renego = row.x_renego_total / sql2[0]

                    # if row.x_product_type_precost.id != 3:
                    if "STC DIGITAL" not in str(row.x_product_type_precost.name).upper():
                        row.x_price_total = self._origin.x_total_cost_high
                        row.x_m2_standart = self._origin.x_cost_m2_high
                    else:
                        price_total = self._origin.x_price_high * self._origin.x_qty
                        row.x_price_total = price_total
                        row.x_m2_standart = price_total / sql2[0]


    @api.one
    def get_id(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('base.group_system') or res_user.has_group('account.group_account_manager'):
            self.x_cek_administrator = True
        else:
            self.x_cek_administrator = False

    @api.one
    def get_id2(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if ("raymond" or "ikawati" or "fenny") in res_user.login:
            self.x_cek_dir = True
        else:
            self.x_cek_dir = False

    @api.one
    def cek_sales_manager(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('sales_team.group_sale_manager'):
            self.x_is_salemanager = True
        else:
            self.x_is_salemanager = False

    @api.multi
    def act_req_dk(self):
        x_tipe = self.x_product_type_precost.name
        x_tgl_req = self.x_req_dk
        date_format = "%Y-%m-%d %H:%M:%S"
        x_tgl_skrg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tgl_req = datetime.strptime(str(x_tgl_req), date_format)
        self.env.cr.execute(
            "select x_day from x_config_default_duedate where name = 'Workday'")
        sql4 = self.env.cr.fetchone()
        workday = sql4[0]

        if x_tipe == 'STC DIGITAL':
            x_hari_minim = 5
        else:
            x_hari_minim = 7
        batas_tgl = datetime.strptime(str(x_tgl_skrg), date_format)
        while x_hari_minim > 0:
            batas_tgl += relativedelta(days=1)
            weekday = batas_tgl.weekday()
            if weekday >= workday:  # sunday = 6
                continue
            x_hari_minim -= 1

        if tgl_req < batas_tgl:
            raise UserError((
                                'Tanggal request terlalu cepat, digital minimal 5 hari kerja dari sekarang, laprint minimal 7 hari kerja'))

        x_approval_dk = self.env['x.approval.dk']
        self.x_flag_reqdk = True
        self.x_status_dk = 'requested'
        self.x_tgl_request = datetime.now()
        self.x_req_dk_marketing = self.x_req_dk

        id = self.id
        self.env.cr.execute("select id from x_approval_dk "
                            "where name = '" + str(id) + "'")

        sql = self.env.cr.fetchone()
        if sql:
            self.x_flag_appdk = False
            x_approval_dk.update({
                'name': self.id,
                'x_sales': self.x_sales_id.id,
                'x_flag_reqdk': True,
                'x_customer': self.x_customer_id,
                'x_item': self.item_description,
                'x_qty': self.x_qty,
                'x_tgl_kirim': self.x_req_dk,
                # 'x_tgl_kirim_pertama': self.x_req_dk_pertama,
                # 'x_mesin': self.x_mrpwordkcenter_id,
                'x_manufacturing_type': self.x_manufacturing_type,
                'x_planning_type': self.x_planning_type,
            })
        else:
            x_approval_dk.create({
                'name': self.id,
                'x_sales': self.x_sales_id.id,
                'x_flag_reqdk': True,
                'x_customer': self.x_customer_id,
                'x_item': self.item_description,
                'x_qty': self.x_qty,
                'x_tgl_kirim': self.x_req_dk,
                # 'x_tgl_kirim_pertama': self.x_req_dk_pertama,
                # 'x_mesin': self.x_mrpwordkcenter_id,
                'x_manufacturing_type': self.x_manufacturing_type,
                'x_planning_type': self.x_planning_type,
            })

    @api.onchange("x_length", "x_width")
    def check_konversi(self):
        if self.x_length > 0:
            self.x_length_m = self.x_length / 1000
        if self.x_width > 0:
            self.x_width_m = self.x_width / 1000

    @api.multi
    def act_reject(self):
        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'reject'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "', '0');")

        self.x_status_cr = 'reject'
        self.x_flag_reqdk = False
        self.x_flag_appdk = False
        self.x_status_dk = 'reject'
        self.x_state_renego = '7'
        # self.state = '9'
        ac = self.env['ir.model.data'].xmlid_to_res_id('lpj_sales.reject_reason_form', raise_if_not_found=True)
        # for o in self:
        sq = self.name

        result = {
            'name': 'Reject Reason',
            'view_type': 'form',
            'res_model': 'x.reject.reason',
            'view_id': ac,
            'context': {
                'default_name': sq
            },
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
        }
        return result

    @api.one
    def cek_sales_manager(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('sales_team.group_sale_manager'):
            self.x_is_salemanager = True
        else:
            self.x_is_salemanager = False

    @api.one
    def get_user(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('account.group_account_manager'):
            self.compute_field = True
        else:
            self.compute_field = False

    @api.one
    def end_date_function(self):
        # Menambah end of date + 60 hari
        start_date = self.start_of_date

        if start_date != False:
            jumlah_hari = '90'
            date_format = '%Y-%m-%d'
            date = self.start_of_date

            start_date_var = datetime.strptime(str(date), date_format)
            end_date_var = start_date_var + relativedelta(days=int(jumlah_hari))
            self.end_of_date = str(end_date_var)

    @api.onchange('x_jumlah_cr_mkt', 'x_reg_cr_mkt', 'x_repeat_order', 'x_product')
    def _update_reg_cr(self):
        product = self.x_product
        marketing = self.x_reg_cr_mkt

        product_product = self.env['product.product'].search([('id', '=', product.id)])
        if product_product:
            if marketing == True:
                product_product.write({
                    'x_reg_cr_mkt_m': True,
                    'x_jumlah_cr_mkt_m': self.x_jumlah_cr_mkt,
                })
            else:
                product_product.write({
                    'x_reg_cr_mkt_m': False,
                    'x_jumlah_cr_mkt_m': self.x_jumlah_cr_mkt,
                })

    @api.multi
    def write(self, values):
        x_tgl_duedate = self.x_req_dk
        x_status_dk = self.x_status_dk

        res = super(Precosting, self).write(values)
        # here you can do accordingly
        # x_tgl_duedate2 = values['x_req_dk']
        x_tgl_duedate2 = self.x_req_dk
        # x_status_dk2 = values['x_status_dk']
        x_status_dk2 = self.x_status_dk
        if x_tgl_duedate != x_tgl_duedate2:
            if x_status_dk == 'approve':
                self.x_status_dk = 'draft'
                # raise UserError(_('harap klik tombol request duedate lebih dahulu setelah mengubah tgl approval duedate'))

        return res

    @api.model
    def create(self, vals):

        result = super(Precosting, self).create(vals)

        sequence = self.env['ir.sequence'].next_by_code('x.sales.quotation') or ('New')
        kalkulator = vals['x_flag_kalkulator']
        if kalkulator == True:
            result.write({'name': 'Kalkulator'})
        else:
            result.write({'name': sequence})

        result.write({'start_of_date': datetime.now()})

        x_id = result.id
        # feat_default = 12
        feat_default = self.env['x.feature.cost.precost'].search([('name', 'in', ('None', 'none', 'NONE'))]).id
        x_prod = result.x_product.id
        feat = result.x_ids_feature
        bool_feat = False

        for x in feat:
            if feat_default == x[0].id:
                bool_feat = True
        if bool_feat == False:
            result.env.cr.execute(
                "INSERT INTO x_feature_cost_precost_x_sales_quotation_rel(x_sales_quotation_id, x_feature_cost_precost_id) VALUES ('" + str(
                    x_id) + "','" + str(feat_default) + "');")

        return result


    @api.onchange("x_product")
    def check_repeat(self):
        feat_default = self.env['x.feature.cost.precost'].search([('name', 'in', ('None', 'none', 'NONE'))]).id

        feat = []
        if self.x_repeat_order == True:
            # firman tambah display name di item description
            self.item_description = self.x_product.display_name
            self.x_customer_id = self.x_product.x_customer

            # self.x_variant_sku =self.x_product.x_variant_sku_prd
            self.x_product_list_layout = self.x_product.x_product_list_layout

            if self.x_product and "NEW ITEM" not in self.x_product.name:
                self.x_length = int(self.x_product.x_length)
                self.x_width = int(self.x_product.x_width)
                # self.x_bentuk_prod = self.x_product.x_bentuk

                #CAK
                # Menyamakan name config bentuk di master product dengan name config bentuk di config precost
                config_bentuk = self.env['x.config.bentuk2'].search([('name', '=ilike', self.x_product.x_bentuk.name)])
                if config_bentuk:
                    self.x_bentuk_prod = config_bentuk

                # Menyamakan name config product type di master product dengan name config product type di config precost
                config_product_type = self.env['x.product.type.precost'].search([('name', '=ilike', self.x_product.categ_id.name)])
                if config_product_type:
                    self.x_product_type_precost = config_product_type


                # Menyamakan name config bahan di master product dengan name config bahan di config precost
                config_bahan = self.env['x.config.bahan'].search([('name', '=ilike', self.x_product.x_bahan.name)])
                if config_bahan:
                    self.x_material_type_id2 = config_bahan

                #CAK
                config_roll_type = self.env['x.config.rolltype'].search([('name','=ilike',self.x_product.x_type_roll.name)])
                if config_roll_type:
                    self.x_roll_type = config_roll_type
                else:
                    self.x_roll_type = ""

                # Menyamakan name config offering digital di master product dengan name config offering digital di config precost
                config_offering = self.env['x.offering.cost.precost'].search([('name', '=like', self.x_product.x_offering.name)])
                if "STC DIGITAL" in str(config_product_type.name) and config_offering:
                    self.x_offering_digital = config_offering

                # Menyamakan config feature di master product dengan config feature di config precost
                self.env.cr.execute(
                    "select * from product_template_x_feature_cost_precost_rel "
                    "where product_template_id = " + str(self.x_product.product_tmpl_id.id)
                )
                sql = self.env.cr.fetchall()
                if sql:
                    for row in sql:
                        feat.append((row[1]))
                else:
                    feat.append((feat_default))
                self.x_ids_feature = feat

    @api.model
    def inactive_bahan(self):
        # Ammar ubah ini 30/07/2021, query sql dari pak catur
        self.env.cr.execute(
            "select id, name , x_active active from x_config_bahan "
            "where id not in ("
            "select distinct bhn2.id "
            "from sale_order so "
            "join sale_order_line sol2 on sol2.order_id = so.id "
            "join x_sales_quotation quot2 on quot2.name = sol2.x_customer_requirement "
            "join x_config_bahan bhn2 on bhn2.id = quot2.x_material_type_id2 "
            "where so.confirmation_date > now() - interval '2 months' "
            "and bhn2.x_active = 't') "
            "and x_active = 't'; "
        )
        sql = self.env.cr.fetchall()
        for o in sql:
            bhn_id = o[0]
            bhn_obj = self.env['x.config.bahan'].search([('id', '=', bhn_id)])
            if bhn_obj:
                bhn_obj.write({
                    'x_active': False
                })

    @api.multi
    def action_precosting(self):
        self.color = 3
        x_nama = self.name
        x_id = self.id
        x_panjang = self.x_length
        x_lebar = self.x_width
        x_kuantitas = self.x_qty
        x_product_tipe = self.x_product_type_precost.name
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        x_m2_pcs = (x_panjang / 1000) * (x_lebar / 1000)
        x_variant_sku = self.x_variant_sku.x_variant_multiplier

        self.env.cr.execute("select x_batas_bawah from x_waste_table_precost where x_product_type_id = '" + str(
            self.x_product_type_precost.id) + "' order by x_batas_bawah limit 1;")
        x_wst = self.env.cr.fetchone()
        if x_wst:
            if x_m2_pcs < x_wst[0] and x_product_tipe != 'STC DIGITAL' :
                raise UserError(('Ukuran m2 per pcs lebih kecil batas terbawah yaitu ' + str(x_wst[0]) + ' m2'))

        # Calculation Button Non Digital
        if x_product_tipe != 'STC DIGITAL':
            sql = self.env.cr.execute("select history_precosting('" + str(res_user.id) + "','" + str(x_nama) +
                                      "','" + str(x_id) + "','" + str(x_panjang) + "','" + str(x_lebar) + "','" + str(
                x_kuantitas) + "');")
            history_precost_obj = self.env['x.history.precosting'].search([('x_id_sq', '=', x_id)])
            x_m2 = history_precost_obj.x_area_m2_tot
            self.cek_moq()

            self.env.cr.execute(
                "select round(cast(x_area_m2_tot as numeric), 2), round(cast(x_waste_produksi as numeric), 2), round(cast(x_waste_config as numeric), 2), round(cast(x_total_waste_m2 as numeric), 2) from x_history_precosting "
                "where x_id_sq = '" + str(x_id) + "'")

            sql2 = self.env.cr.fetchone()
            if sql2:
                self.x_area_m2_tot = sql2[0]
                self.x_waste_produksi = sql2[1]
                self.x_waste_produksi_m2 = sql2[1] * sql2[0] / 100
                self.x_waste_config = sql2[2]
                self.x_waste_config_m2 = sql2[2] * sql2[0] / 100
                self.x_total_waste_m2 = sql2[3]
            else:
                self.x_area_m2_tot = 0
                self.x_waste_produksi = 0
                self.x_waste_produksi_m2 = 0
                self.x_waste_config = 0
                self.x_waste_config_m2 = 0
                self.x_total_waste_m2 = 0

        # Calculation Button Precost Digital
        else:
            sql = self.env.cr.execute("select history_precosting_digital('" + str(res_user.id) + "','" + str(x_nama) +
                                      "','" + str(x_id) + "','" + str(x_panjang) + "','" + str(x_lebar) + "','" + str(
                x_kuantitas) + "','" + str(x_variant_sku) + "');")
            history_precost_obj2 = self.env['x.history.precosting'].search([('x_id_sq', '=', x_id)])
            x_m2 = history_precost_obj2.x_area_m2_tot

            sql2 = self.env.cr.execute("SELECT * FROM history_precosting_pembelian_digital('" + str(res_user.id) + "','" + str(x_nama) +
                                       "','" + str(x_id) + "','" + str(x_panjang) + "','" + str(x_lebar) + "','" + str(x_kuantitas) + "');")

    @api.multi
    def action_renego(self):
        self.x_flag_quo = False
        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        self.x_harga_renego_sales = x_renego
        self.x_renego_total = self.x_harga_renego * self.x_qty
        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'renego'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "', '0');")

    @api.multi
    def action_open_block_moq(self):
        self.x_state_renego = '2'
        x_id = self.id
        hist_obj = self.env['x.history.sq'].create({
            'name': 'Open Block MOQ',
            'x_quantity': self.x_qty,
            'x_sq': x_id,
            'x_price': self.x_harga_renego,
            'x_description': 'Open Block MOQ',
        })

    @api.multi
    def action_confirm_dir(self):
        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        self.x_harga_renego_sales = x_renego
        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'confirm_dir'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "', '0');")

    @api.multi
    def action_confirm_spv(self):

        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        self.x_harga_renego_sales = x_renego

        x_price_purchase = self.x_quo_purchase_price_pcs
        pros_profit = (x_renego - x_price_purchase) / x_renego * 100

        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'confirm_spv'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "','" + str(pros_profit) + "');")

    @api.multi
    def action_reject(self):
        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'reject'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "', '0');")

        self.x_status_cr = 'reject'
        self.x_flag_reqdk = False
        self.x_flag_appdk = False
        self.x_status_dk = 'reject'
        self.x_state_renego = '7'
        # self.state = '9'
        reject_reason = self.env['x.master.reason'].search([('name', '=ilike', 'Expired')]).id

        reject_reason_obj = self.env['x.reject.reason'].create({
            'name': self.name,
            'x_desc': '(Reject by System)',
            'x_reject_reason': reject_reason
        })

    @api.multi
    def reset_precosting(self):
        self.x_flag_quo = False
        x_kuantitas = self.x_qty
        x_renego = self.x_harga_renego
        self.x_harga_renego_sales = 0
        x_id = self.id
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        action = 'reset'

        sql = self.env.cr.execute("select renego_precost('" + str(res_user.id) +
                                  "','" + str(x_id) + "','" + str(x_kuantitas) + "','" + str(x_renego) + "','" + str(
            action) + "' , '0');")
        self.x_status_quo_purchase = ''
        self.x_quo_purchase_price_pcs = 0.00
        self.x_quo_purchase_m2 = 0.00

    # Fungsi cek moq
    @api.multi
    def cek_moq(self):
        state_renego = self.x_state_renego
        if state_renego == 8:
            raise UserError(_('Item ini DIBAWAH MOQ m2, Silahkan Minta Harga Digital Ke Tim Digital'))

    # akbar tambah 23/04/2021 untuk reset dan reject SQ pada scheduled action
    @api.model
    def reset_precost_expired(self):
        state_renego = self.x_state_renego
        self.env.cr.execute(
            "select quot.id sq_id, quot.name, hist_desc.create_date + interval '7 hours' tgl_acc, hist_desc.x_description, sol.id sol_id, x_status_dk "
            "from x_sales_quotation quot "
            "left join "
            "(select quot.id sq_id, max(hist.id) hist_id "
            "from x_sales_quotation quot "
            "join x_history_sq hist on hist.x_sq = quot.id "
            "where x_description in ('SPV Approved', 'GM Approved') "
            "group by quot.id "
            "order by quot.id) hist on hist.sq_id = quot.id "
            "join x_history_sq hist_desc on hist_desc.x_sq = quot.id and hist_desc.id = hist.hist_id "
            "left join sale_order_line sol on sol.x_sq_id = quot.id "
            "where "
            "quot.x_state_renego = '6' "
            "and sol.id is null "
            "and hist_desc.create_date + interval '7 hours' < now() - interval '1 months' "
            "order by sq_id ")

        sql = self.env.cr.fetchall()

        if sql:
            for row in sql:
                id_sq = row[0]
                sq = self.env['x.sales.quotation'].search([('id', '=', id_sq)])
                sq.reset_precosting()

    # akbar tambah 23/04/2021 untuk reset dan reject SQ pada scheduled action
    @api.model
    def reject_precost_expired(self):
        state_renego = self.x_state_renego
        self.env.cr.execute(
            "select quot.id sq_id, quot.name, quot.create_date + interval '7 hours' "
            "from x_sales_quotation quot "
            "left join sale_order_line sol on sol.x_sq_id = quot.id "
            "where sol.id is null "
            "and quot.create_date + interval '7 hours' < now() - interval '3 months' "
            "and quot.x_status_cr <> 'reject' "
            "order by sq_id ")

        sql2 = self.env.cr.fetchall()

        if sql2:
            for row in sql2:
                id_sq = row[0]
                sq = self.env['x.sales.quotation'].search([('id', '=', id_sq)])
                sq.action_reject()

    @api.model
    def delete_kalkulator(self):
        self.env.cr.execute("delete from x_sales_quotation where name = 'Kalkulator'")


class reject_reason(models.Model):
    _name = 'x.reject.reason'

    name = fields.Char(string = 'SQ', readonly = True)
    x_reject_reason = fields.Many2one('x.master.reason',string='Reason')
    x_desc = fields.Text(string='Description')


class reject(models.Model):
    _name = 'x.master.reason'

    name = fields.Text(string='Reason')


class range_price_sq(models.Model):
    _name = 'x.range.price.sq'
    name = fields.Char(string = 'Nama')
    x_sq = fields.Many2one('x.sales.quotation', string='Range Price SQ')
    x_quantity = fields.Integer(string = 'Quantity')
    x_quantity_range = fields.Char(compute='gabung', string='Quantity Range')
    x_quantity_roundup = fields.Integer(string='Quantity Roundup')
    x_quantity_m2 = fields.Integer(string='Quantity m2')
    x_price_pcs = fields.Float(string = 'Price per pcs')
    x_price_pcs_range = fields.Char(string='Price per pcs range', default='0')
    x_price_pcs_range2 = fields.Char(compute='gabung', string='Price per pcs range')
    x_price_m2 = fields.Float(string = 'Price per m2')
    x_price_total = fields.Float(string='Price Total')
    x_price_total_low = fields.Float(string='Price Total Low', default=0.0)
    x_price_total_range = fields.Char(compute='gabung', string='Price Total')
    x_hpp_pcs = fields.Float(string='HPP per pcs')
    x_hpp_m2 = fields.Float(string='HPP per m2')
    x_hpp_total = fields.Float(string='HPP Total')
    x_hpp_total_range = fields.Char(compute='gabung', string='HPP Total')
    x_prosentase_profit = fields.Float(string = 'Prosentase Profit')
    x_prosentase_profit_low = fields.Float(string = 'Prosentase Profit Low', default=0.0)
    x_prosentase_profit_range = fields.Char(compute='gabung', string = 'Prosentase Profit (%)')
    x_hpp_total2 = fields.Float(string='HPP Total Up')
    x_price_total2 = fields.Float(string='Price Total Up')
    x_quantity_roundup2 = fields.Integer(string='Quantity Roundup Up')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')

    @api.one
    def gabung(self):
        x_id_r = self.id
        self.env.cr.execute("select x_sq from x_range_price_sq where id = '" + str(x_id_r) + "'")
        sql = self.env.cr.fetchone()
        id = sql[0]
        self.env.cr.execute("select max(id) from x_range_price_sq where x_sq = '"+ str(id)+"'")
        sql = self.env.cr.fetchone()
        id_range = self.id
        if sql:
            if id_range == sql[0]:
                self.x_price_total_range = 'Rp ' + "{:,.0f}".format(self.x_price_total).replace(",",
                                                                                                     ".") + ' -- ...'
                self.x_hpp_total_range = 'Rp ' + "{:,.0f}".format(self.x_hpp_total).replace(",",
                                                                                             ".") + ' -- ...'
                self.x_quantity_range = "{:,.0f}".format(self.x_quantity_roundup).replace(",",
                                                                                          ".") + ' -- ...'
                self.x_prosentase_profit_range = "{:,.2f}".format(self.x_prosentase_profit_low).replace(".",
                                                                                                     ",") + ' -- ' + "{:,.2f}".format(
                    self.x_prosentase_profit).replace(".", ",")
                self.x_price_pcs_range2 = self.x_price_pcs_range.replace(".",",")
            else:
                if self.x_price_total == 0:
                    self.x_price_total_range = 'Dibawah MOQ'
                    self.x_hpp_total_range = 'Dibawah MOQ'
                    self.x_quantity_range = "{:,.0f}".format(self.x_quantity_roundup).replace(",",
                                                                                              ".") + ' -- ' + "{:,.0f}".format(
                        self.x_quantity_roundup2).replace(",", ".")
                    self.x_prosentase_profit_range='Dibawah MOQ'
                    self.x_price_pcs_range2 ='Dibawah MOQ'
                else:
                    self.x_price_total_range = 'Rp ' + "{:,.0f}".format(self.x_price_total).replace(",",
                                                                                                     ".") + ' -- ' + 'Rp ' + "{:,.0f}".format(
                        self.x_price_total2).replace(",", ".")
                    self.x_hpp_total_range = 'Rp ' + "{:,.0f}".format(self.x_hpp_total).replace(",",
                                                                                                     ".") + ' -- ' + 'Rp ' + "{:,.0f}".format(
                        self.x_hpp_total2).replace(",", ".")
                    self.x_quantity_range = "{:,.0f}".format(self.x_quantity_roundup).replace(",",
                                                                                                 ".") + ' -- ' + "{:,.0f}".format(
                        self.x_quantity_roundup2).replace(",", ".")
                    self.x_prosentase_profit_range = "{:,.2f}".format(self.x_prosentase_profit_low).replace(".",
                                                                                                         ",") + ' -- ' + "{:,.2f}".format(
                        self.x_prosentase_profit).replace(".", ",")
                    self.x_price_pcs_range2 = self.x_price_pcs_range.replace(".", ",")


class history_sq(models.Model):
    _name = 'x.history.sq'
    x_sq = fields.Many2one('x.sales.quotation', string='History SQ')
    name = fields.Char(string = 'Action')
    x_quantity = fields.Integer(string = 'Quantity')
    x_price = fields.Float(string = 'Price')
    x_description = fields.Char(string = 'Keterangan')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')


class summary_precosting(models.Model):
    _name = 'x.summary.precosting'
    x_sq = fields.Many2one('x.sales.quotation', string='Summary Precosting')
    name = fields.Char(string = 'Cost Factor')
    x_total_cost = fields.Integer(string = 'Total Cost')
    x_cost_pcs = fields.Float(string = 'Cost/pcs')
    x_cost_m2 = fields.Float(string = 'Cost/m2')
    # x_profit = fields.Float(string='Profit')
    x_cost_margin_hpp = fields.Float(string='Cost Margin to HPP')
    x_cost_margin_low = fields.Float(string='Cost Margin to Price Low')
    x_cost_margin_hpp2 = fields.Char(string='Cost Margin to HPP', compute='persentase')
    x_cost_margin_low2 = fields.Char(string='Cost Margin to Price Low', compute='persentase')
    x_cost_margin_hpp3 = fields.Float(string='Cost Margin to HPP (%)', compute='persentase')
    x_cost_margin_low3 = fields.Float(string='Cost Margin to Price Low (%)', compute='persentase')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')

    @api.one
    def persentase(self):
        self.x_cost_margin_hpp2 = str(round((self.x_cost_margin_hpp * 100),1)) + " %"
        self.x_cost_margin_low2 = str(round((self.x_cost_margin_low * 100),1)) + " %"
        self.x_cost_margin_hpp3 = (round((self.x_cost_margin_hpp * 100), 1))
        self.x_cost_margin_low3 = (round((self.x_cost_margin_low * 100), 1))


class summary_precosting_low(models.Model):
    _name = 'x.summary.precosting.low'
    x_sq = fields.Many2one('x.sales.quotation', string='Summary Precosting Low')
    name = fields.Char(string = 'Cost Factor')
    x_total_cost = fields.Integer(string = 'Total Cost')
    x_cost_pcs = fields.Float(string = 'Cost/pcs')
    x_cost_m2 = fields.Float(string = 'Cost/m2')
    # x_profit = fields.Float(string='Profit')
    x_cost_margin_hpp = fields.Float(string='Cost Margin to HPP')
    x_cost_margin_low = fields.Float(string='Cost Margin to Price Low')
    x_cost_margin_hpp2 = fields.Char(string='Cost Margin to HPP', compute='persentase')
    x_cost_margin_low2 = fields.Char(string='Cost Margin to Price Low', compute='persentase')
    x_cost_margin_hpp3 = fields.Float(string='Cost Margin to HPP (%)', compute='persentase')
    x_cost_margin_low3 = fields.Float(string='Cost Margin to Price Low (%)', compute='persentase')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')

    @api.one
    def persentase(self):
        self.x_cost_margin_hpp2 = str(round((self.x_cost_margin_hpp * 100), 1)) + " %"
        self.x_cost_margin_low2 = str(round((self.x_cost_margin_low * 100), 1)) + " %"
        self.x_cost_margin_hpp3 = (round((self.x_cost_margin_hpp * 100), 1))
        self.x_cost_margin_low3 = (round((self.x_cost_margin_low * 100), 1))


class summary_precosting_high(models.Model):
    _name = 'x.summary.precosting.high'
    x_sq = fields.Many2one('x.sales.quotation', string='Summary Precosting High')
    name = fields.Char(string = 'Cost Factor')
    x_total_cost = fields.Integer(string = 'Total Cost')
    x_cost_pcs = fields.Float(string = 'Cost/pcs')
    x_cost_m2 = fields.Float(string = 'Cost/m2')
    # x_profit = fields.Float(string='Profit')
    x_cost_margin_hpp = fields.Float(string='Cost Margin to HPP')
    x_cost_margin_low = fields.Float(string='Cost Margin to Price Low')
    x_cost_margin_hpp2 = fields.Char(string='Cost Margin to HPP', compute='persentase')
    x_cost_margin_low2 = fields.Char(string='Cost Margin to Price Low', compute='persentase')
    x_cost_margin_hpp3 = fields.Float(string='Cost Margin to HPP (%)', compute='persentase')
    x_cost_margin_low3 = fields.Float(string='Cost Margin to Price Low (%)', compute='persentase')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')

    @api.one
    def persentase(self):
        self.x_cost_margin_hpp2 = str(round((self.x_cost_margin_hpp * 100), 1)) + " %"
        self.x_cost_margin_low2 = str(round((self.x_cost_margin_low * 100), 1)) + " %"
        self.x_cost_margin_hpp3 = (round((self.x_cost_margin_hpp * 100), 1))
        self.x_cost_margin_low3 = (round((self.x_cost_margin_low * 100), 1))


class price_level(models.Model):
    _name = 'x.price.level'
    x_sq = fields.Many2one('x.sales.quotation', string='Price Level')
    name = fields.Char(string = 'Cost Factor')
    x_total_cost = fields.Integer(string = 'Total Price')
    x_cost_pcs = fields.Float(string = 'Price/pcs')
    x_cost_m2 = fields.Float(string = 'Price/m2')
    x_profit = fields.Many2one('x.profit.margin.product.type', string='Profit Margin')
    x_percentage = fields.Float('Profit Margin (%)', related='x_profit.x_percentage')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')
# x.profit.margin.product.type


class history_sq_win(models.Model):
    _name = 'x.history.sq.win'
    x_sq = fields.Many2one('x.sales.quotation', string='SQ')
    name = fields.Many2one('product.product', string='Product Name', domain=[('sale_ok', '=', True)])
    x_quantity = fields.Integer(string='Quantity')
    x_date = fields.Date(string='Date')
    x_total_cost = fields.Integer(string = 'Total Price')
    x_cost_pcs = fields.Float(string = 'Price/pcs')
    x_cost_m2 = fields.Float(string = 'Price/m2')
    x_profit = fields.Float(string='Profit Harga')
    x_sq_win = fields.Many2one('x.sales.quotation', string='SQ WIN')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')


class history_sq_lost(models.Model):
    _name = 'x.history.sq.lost'
    x_sq = fields.Many2one('x.sales.quotation', string='SQ')
    name = fields.Many2one('product.product', string='Product Name', domain=[('sale_ok', '=', True)])
    x_quantity = fields.Integer(string='Quantity')
    x_date = fields.Date(string='Date')
    x_total_cost = fields.Integer(string = 'Total Price')
    x_cost_pcs = fields.Float(string = 'Price/pcs')
    x_cost_m2 = fields.Float(string = 'Price/m2')
    x_profit = fields.Float(string='Profit Harga')
    x_sq_lost = fields.Many2one('x.sales.quotation', string='SQ LOST')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')


class history_sq_pending(models.Model):
    _name = 'x.history.sq.pending'
    x_sq = fields.Many2one('x.sales.quotation', string='SQ')
    name = fields.Many2one('product.product', string='Product Name', domain=[('sale_ok', '=', True)])
    x_quantity = fields.Integer(string='Quantity')
    x_date = fields.Date(string='Date')
    x_total_cost = fields.Float(string = 'Total Price')
    x_cost_pcs = fields.Float(string = 'Price/pcs')
    x_cost_m2 = fields.Float(string = 'Price/m2')
    x_profit = fields.Float(string='Profit Harga')
    x_sq_pending = fields.Many2one('x.sales.quotation', string='SQ PENDING')
    currency_id = fields.Many2one('res.currency', 'Currency', related='x_sq.currency_id')
