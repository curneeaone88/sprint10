# -*- coding: utf-8 -*-
from odoo import models, fields, api

REF_FIELDS = ('x_ok_ref_days_new', 'x_ok_ref_days_repeat',
              'x_ok_ref_nominal_limit', 'x_ok_ref_days_lower',
              'x_ok_ref_days_greater')


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_ok_ref_days_new = fields.Integer(
        string='Hari Referensi - OK New', default=7)
    x_ok_ref_days_repeat = fields.Integer(
        string='Hari Referensi - OK Repeat', default=7)
    x_ok_ref_nominal_limit = fields.Float(
        string='Batas Nominal SO (juta Rp)', default=0.0)
    x_ok_ref_days_lower = fields.Integer(
        string='Hari Referensi - SO di Bawah Batas', default=0)
    x_ok_ref_days_greater = fields.Integer(
        string='Hari Referensi - SO di Atas Batas', default=0)


class ResConfigSettings(models.TransientModel):
    # Pola get_default_/set_ sama seperti di lpj_design (tanpa related company_id).
    _inherit = 'res.config.settings'

    x_ok_ref_days_new = fields.Integer(string='OK New (hari)')
    x_ok_ref_days_repeat = fields.Integer(string='OK Repeat (hari)')
    x_ok_ref_nominal_limit = fields.Float(string='Batas nominal SO (juta Rp)')
    x_ok_ref_days_lower = fields.Integer(string='SO di bawah batas (hari)')
    x_ok_ref_days_greater = fields.Integer(string='SO di atas batas (hari)')

    @api.model
    def get_default_x_ok_ref_days_new(self, fields_list):
        comp = self.env.user.company_id
        return dict((f, comp[f]) for f in REF_FIELDS)

    @api.multi
    def set_x_ok_ref_days_new(self):
        for rec in self:
            self.env.user.company_id.sudo().write(
                dict((f, max(rec[f], 0)) for f in REF_FIELDS))
