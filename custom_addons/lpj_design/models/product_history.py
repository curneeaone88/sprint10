# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from cgi import escape as html_escape

_logger = logging.getLogger(__name__)

# Field yang tidak berguna dicatat di history (teknis / gambar / bawaan mail).
_SKIP_PREFIX = ('message_', 'activity_', 'image', '__last', 'website_')
_SKIP_FIELDS = set([
    'write_date', 'write_uid', 'create_date', 'create_uid', 'id',
    'product_variant_ids', 'product_variant_id', 'product_variant_count',
])


def _fmt(record, fname, value_record=None):
    """Nilai field jadi teks yang enak dibaca di history."""
    field = record._fields[fname]
    rec = value_record if value_record is not None else record
    val = rec[fname]
    if field.type == 'many2one':
        return val.display_name or u'-'
    if field.type in ('many2many', 'one2many'):
        return u', '.join(val.mapped('display_name')) or u'-'
    if field.type == 'selection':
        return dict(field._description_selection(record.env)).get(val) or u'-'
    if field.type == 'boolean':
        return _('Ya') if val else _('Tidak')
    if val is False or val is None or val == '':
        return u'-'
    return u'%s' % val


class ProductTemplateHistory(models.Model):
    """Setiap perubahan field di Master Produk dicatat di chatter (history):
    siapa, kapan, field apa, nilai lama -> baru."""
    _inherit = 'product.template'

    @api.model
    def _history_fields(self, vals):
        res = []
        for f in vals:
            field = self._fields.get(f)
            if not field or f in _SKIP_FIELDS or f.startswith(_SKIP_PREFIX):
                continue
            if field.type in ('binary', 'one2many', 'html'):
                continue
            if not field.store and field.type != 'many2many':
                continue
            res.append(f)
        return res

    @api.multi
    def _post_history(self, lines):
        body = u'<ul>%s</ul>' % u''.join(
            u'<li><b>%s</b>: %s &rarr; %s</li>' % (
                html_escape(l[0]), html_escape(l[1]), html_escape(l[2]))
            for l in lines)
        try:
            with self.env.cr.savepoint():
                self.message_post(body=body, subtype='mail.mt_note')
        except Exception:
            _logger.exception("Gagal mencatat history Master Produk")

    @api.multi
    def write(self, vals):
        fnames = self._history_fields(vals)
        old = {}
        if fnames:
            for rec in self:
                old[rec.id] = dict((f, _fmt(rec, f)) for f in fnames)
        res = super(ProductTemplateHistory, self).write(vals)
        if fnames:
            for rec in self:
                lines = []
                for f in fnames:
                    before = old.get(rec.id, {}).get(f)
                    after = _fmt(rec, f)
                    if before != after:
                        lines.append((rec._fields[f].string or f, before, after))
                if lines:
                    rec._post_history(lines)
        return res
