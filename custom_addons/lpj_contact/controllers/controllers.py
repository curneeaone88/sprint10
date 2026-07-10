# -*- coding: utf-8 -*-
from odoo import http

# class LpjContact(http.Controller):
#     @http.route('/lpj_contact/lpj_contact/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lpj_contact/lpj_contact/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('lpj_contact.listing', {
#             'root': '/lpj_contact/lpj_contact',
#             'objects': http.request.env['lpj_contact.lpj_contact'].search([]),
#         })

#     @http.route('/lpj_contact/lpj_contact/objects/<model("lpj_contact.lpj_contact"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lpj_contact.object', {
#             'object': obj
#         })