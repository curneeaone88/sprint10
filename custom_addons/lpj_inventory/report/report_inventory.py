# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError

class ReportWizardPrintIntTransfer(models.AbstractModel):
    _name = 'report.lpj_inventory.report_internaltransfer'

    def code_document(self,vals):
        view_obj = self.env['x.kode.dokumen'].search([('x_report', '=', vals)])
        if view_obj:
            val = view_obj.name
            return val

    @api.model
    def render_html(self, docids, data=None):

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('lpj_inventory.report_internaltransfer')
        docargs = {
            'code_document': self.code_document,
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'report_id':report.id
        }
        return self.env['report'].render('lpj_inventory.report_internaltransfer', docargs)

class ReportWizardPrintLotSupplier(models.AbstractModel):
    _name = 'report.lpj_inventory.report_lotsupplier'

    def code_document(self,vals):
        view_obj = self.env['x.kode.dokumen'].search([('x_report', '=', vals)])
        if view_obj:
            val = view_obj.name
            return val

    @api.model
    def render_html(self, docids, data=None):

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('lpj_inventory.report_lotsupplier')
        docargs = {
            'code_document': self.code_document,
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'report_id':report.id
        }
        return self.env['report'].render('lpj_inventory.report_lotsupplier', docargs)
