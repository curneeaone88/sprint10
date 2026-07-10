# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError

class Report_Custom_KodeDokumen(models.AbstractModel):
    _name = 'report.lpj_product.report_print_tds'

    def code_document(self,report_id):
        view_obj = self.env['x.kode.dokumen'].search([('x_report', '=', report_id)])
        if view_obj:
            val = view_obj.name
            return val

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('lpj_product.report_print_tds')
        docargs = {
            'code_document': self.code_document,
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'report_id': report.id
        }
        return self.env['report'].render('lpj_product.report_print_tds', docargs)