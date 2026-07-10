
from odoo import models, fields, api
# import odoo.addons.decimal_precision as dp


class inherit_contact_partner(models.Model):

     _inherit = 'res.partner'

     x_rt = fields.Char(string = 'RT')
     x_rw = fields.Char(string='RW')
     x_npwp = fields.Char(string = 'NPWP', readonly=True)
     x_pkp = fields.Boolean(string = 'PKP')
     x_kode_customer = fields.Char(string ='kode customer')
     x_status_cust = fields.Char(string='Customer Potential', readonly=True)
     x_customer_service = fields.Many2one('res.users', string='Customer Services')

     # fields untuk ambil data history

     x_date_action = fields.Datetime('Next Activity Date', track_visibility='always')
     x_propose = fields.Char(track_visibility='always', string = 'Next Activity Purpose')
     x_summary = fields.Char(string='Summary', track_visibility='always')
     x_expected_revenue = fields.Float(string='Expected Revenue', track_visibility='always')
     x_expected_closing = fields.Datetime(string='Expected Closing', track_visibility='always')
     x_description = fields.Html('Note(s)', track_visibility='always')

class termin_line(models.Model):
     _name = 'x.termin'

     name = fields.Char(string = 'Nama Termin')
     Description = fields.Text(string = 'Description')

