=============================
Account Invoice Tree Scenario
=============================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale_wbs::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([('name', '=', 'account_invoice_tree')])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

Set Cash journal::

    >>> Journal = Model.get('account.journal')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.consumable = True
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('8')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product1, = template.products
    >>> product2 = template.products.new()
    >>> product2.save()

    >>> template = ProductTemplate()
    >>> template.name = 'service'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.list_price = Decimal('30')
    >>> template.cost_price = Decimal('10')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> service1, = template.products
    >>> service2 = template.products.new()
    >>> service2.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta = line.relativedeltas.new(days=20)
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=40)
    >>> payment_term.save()

Create a Invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> InvoiceLine = Model.get('account.invoice.line')
    >>> invoice = Invoice()
    >>> invoice.party = customer
    >>> invoice.payment_term = payment_term
    >>> invoice_line = invoice.lines.new()
    >>> invoice_line.product = product1
    >>> invoice_line.description = 'Product Line 1'
    >>> invoice_line.quantity = 10
    >>> invoice_line.unit_price = Decimal('40')
    >>> invoice_line = invoice.lines.new()
    >>> invoice_line.type = 'title'
    >>> invoice_line.description = 'Chapter 1'
    >>> invoice_line = invoice.lines.new()
    >>> invoice_line.type = 'title'
    >>> invoice_line.description = 'Chapter 2'
    >>> invoice.save()
    >>> product1_line, chapter1_line, chapter2_line = invoice.lines
    >>> child_invoice_line = invoice.lines.new()
    >>> child_invoice_line.parent = InvoiceLine(chapter1_line.id)
    >>> child_invoice_line.product = service1
    >>> child_invoice_line.description = 'Service Line 1'
    >>> child_invoice_line.quantity = 5
    >>> child_invoice_line.unit_price = Decimal('40')
    >>> child_invoice_line = invoice.lines.new()
    >>> child_invoice_line.parent = InvoiceLine(chapter1_line.id)
    >>> child_invoice_line.product = product2
    >>> child_invoice_line.description = 'Product Line 2'
    >>> child_invoice_line.quantity = 15
    >>> child_invoice_line.unit_price = Decimal('40')
    >>> child_invoice_line = invoice.lines.new()
    >>> child_invoice_line.parent = InvoiceLine(chapter2_line.id)
    >>> child_invoice_line.product = service2
    >>> child_invoice_line.description = 'Service Line 2'
    >>> child_invoice_line.quantity = 10
    >>> child_invoice_line.unit_price = Decimal('40')
    >>> invoice.save()

Check invoice structure::

    >>> len(invoice.lines)
    6
    >>> len(invoice.lines_tree)
    3
    >>> (invoice.lines_tree[0] == product1_line,
    ...     invoice.lines_tree[1] == chapter1_line,
    ...     invoice.lines_tree[2] == chapter2_line)
    (True, True, True)
    >>> len(product1_line.childs)
    0
    >>> len(chapter1_line.childs)
    2
    >>> service1_line, product2_line = chapter1_line.childs
    >>> service1_line.product == service1
    True
    >>> product2_line.product == product2
    True
    >>> len(chapter2_line.childs)
    1
    >>> service2_line, = chapter2_line.childs
    >>> service2_line.product == service2
    True

Chapter Number must be computed correctly::

    >>> product1_line.chapter_number
    '1'
    >>> chapter1_line.chapter_number
    '2'
    >>> service1_line.chapter_number
    '2.1'
    >>> product2_line.chapter_number
    '2.2'
    >>> chapter2_line.chapter_number
    '3'
    >>> service2_line.chapter_number
    '3.1'
