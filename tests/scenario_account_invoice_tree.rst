=============================
Account Invoice Tree Scenario
=============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale_wbs::

    >>> Module = Model.get('ir.module.module')
    >>> module, = Module.find([('name', '=', 'account_invoice_tree')])
    >>> module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
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
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
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
    >>> child_invoice_line = invoice.lines.new()
    >>> child_invoice_line.parent = InvoiceLine(chapter1_line.id)
    >>> child_invoice_line.product = product2
    >>> child_invoice_line.description = 'Product Line 2'
    >>> child_invoice_line.quantity = 15
    >>> child_invoice_line = invoice.lines.new()
    >>> child_invoice_line.parent = InvoiceLine(chapter2_line.id)
    >>> child_invoice_line.product = service2
    >>> child_invoice_line.description = 'Service Line 2'
    >>> child_invoice_line.quantity = 10
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
