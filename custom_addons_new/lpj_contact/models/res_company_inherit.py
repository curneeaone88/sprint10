# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, time, date


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_phone2 = fields.Char(string="Phone 2")
    x_whatsapp = fields.Char(string="Whatsapp")
    x_whatsapp2 = fields.Char(string="Whatsapp 2")
