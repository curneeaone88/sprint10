import subprocess
import odoo.addons.decimal_precision as dp

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError



class Config_Bentuk(models.Model):
    _name = 'x.config.bentuk'

    name = fields.Char(string="Bentuk")


class Config_Diecut(models.Model):
     _name = 'x.config_diecut'

     name = fields.Char(string="Diecut")


class Config_Finishing(models.Model):
    _name = 'x.config_finishing'

    name = fields.Char(string="Finishing")


class ConfigMaterial(models.Model):
    _name = 'x.config.material'

    name = fields.Char(string="Material")

class ConfigTypeRoll(models.Model):
    _name = 'x.config_typeroll_product'

    name = fields.Char(string="Type Roll")
