# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Invoice', 'InvoiceLine']


class ChapterMixin(object):
    chapter_number = fields.Function(fields.Char('Chapter Number'),
        'get_chapter_number')

    @classmethod
    def get_1st_level_chapters(cls, records):
        """Return iterator over list of first records' ancestors children"""
        raise NotImplementedError

    @classmethod
    def get_chapter_number(cls, records, name):
        result = dict.fromkeys((r.id for r in records), None)
        # Calculate full sale to get the order correctly
        for children in cls.get_1st_level_chapters(records):
            values = cls._compute_chapter_number(children)
            for child_id, value in values.iteritems():
                if child_id not in result:
                    continue
                result[child_id] = value
        return result

    @classmethod
    def _compute_chapter_number(cls, children, prefix=None):
        if prefix is None:
            prefix = ''
        result = {}
        for i, child in enumerate(children, 1):
            result[child.id] = '%s%s' % (prefix, i)
            if child.childs:
                result.update(cls._compute_chapter_number(
                        child.childs, prefix=result[child.id] + '.'))
        return result


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'
    lines_tree = fields.Function(fields.One2Many('account.invoice.line',
            None, 'Lines',
            domain=[
                ('parent', '=', None),
                ]),
        'get_lines_tree', setter='set_lines_tree')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        if cls.lines.domain:
            cls.lines_tree._field.domain.extend(cls.lines.domain)
        cls.lines_tree._field.states = cls.lines.states
        cls.lines_tree._field.context = cls.lines.context
        cls.lines_tree._field.depends = cls.lines.depends

    def get_lines_tree(self, name):
        return [x.id for x in self.lines if not x.parent]

    @classmethod
    def set_lines_tree(cls, lines, name, value):
        cls.write(lines, {
                'lines': value,
                })

    @fields.depends('lines', 'lines_tree', methods=['lines'])
    def on_change_lines_tree(self, name=None):
        lines = self.lines
        self.lines = self.lines_tree
        self.on_change_lines()
        self.lines_tree = self.lines
        self.lines = lines

    @classmethod
    def copy(cls, invoices, default=None):
        pool = Pool()
        InvoiceLine = pool.get('invoice.line')
        if default is None:
            default = {}
        default['lines'] = []
        new_invoices = super(Invoice, cls).copy(invoices, default=default)
        for invoice, new_invoice in zip(invoices, new_invoices):
            new_default = default.copy()
            new_default['invoice'] = new_invoice.id
            InvoiceLine.copy(invoice.lines_tree, default=new_default)
        return new_invoices


class InvoiceLine(ChapterMixin):
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice.line'

    parent = fields.Many2One('account.invoice.line', 'Parent', select=True,
        ondelete='CASCADE',
        domain=[
            ('invoice', '=', Eval('invoice')),
            ('type', '=', 'title'),
            ],
        depends=['invoice'])
    childs = fields.One2Many('account.invoice.line', 'parent', 'Childs',
        domain=[
            ('invoice', '=', Eval('invoice')),
            ],
        depends=['invoice'])


    def get_amount(self, name):
        if self.parent and (self.type == 'subtotal'
                and self.parent.type == 'title'):
            def get_amount_rec(parent):
                subtotal = Decimal(0)
                for line2 in parent.childs:
                    if line2.childs:
                        subtotal += get_amount_rec(line2)
                    if line2.type == 'line':
                        subtotal += line2.sale.currency.round(
                            Decimal(str(line2.quantity)) * line2.unit_price)
                    elif line2.type == self.type:
                        if self == line2:
                            return subtotal
                        subtotal = Decimal(0)
                return subtotal

            return get_amount_rec(self.parent)
        return super(InvoiceLine, self).get_amount(name)

    @classmethod
    def get_1st_level_chapters(cls, records):
        for invoice in {l.invoice for l in records}:
            yield invoice.lines_tree

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default['wbs'] = None
        default['childs'] = []
        new_lines = []
        for line in lines:
            new_line, = super(InvoiceLine, cls).copy([line], default)
            new_lines.append(new_line)
            new_default = default.copy()
            new_default['parent'] = new_line.id
            cls.copy(line.childs, default=new_default)
        return new_lines
