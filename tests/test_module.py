# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from decimal import Decimal

from trytond.modules.company.tests import CompanyTestMixin
from trytond.modules.product import round_price
from trytond.modules.product.exceptions import UOMAccessError
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction


class ProductTestCase(CompanyTestMixin, ModuleTestCase):
    'Test Product module'
    module = 'product'

    @with_transaction()
    def test_uom_non_zero_rate_factor(self):
        'Test uom non_zero_rate_factor constraint'
        pool = Pool()
        UomCategory = pool.get('product.uom.category')
        Uom = pool.get('product.uom')
        transaction = Transaction()
        category, = UomCategory.create([{'name': 'Test'}])

        self.assertRaises(Exception, Uom.create, [{
                'name': 'Test',
                'symbol': 'T',
                'category': category.id,
                'rate': 0,
                'factor': 0,
                }])
        transaction.rollback()

        def create():
            category, = UomCategory.create([{'name': 'Test'}])
            return Uom.create([{
                        'name': 'Test',
                        'symbol': 'T',
                        'category': category.id,
                        'rate': 1.0,
                        'factor': 1.0,
                        }])[0]

        uom = create()
        self.assertRaises(Exception, Uom.write, [uom], {
                'rate': 0.0,
                })
        transaction.rollback()

        uom = create()
        self.assertRaises(Exception, Uom.write, [uom], {
                'factor': 0.0,
                })
        transaction.rollback()

        uom = create()
        self.assertRaises(Exception, Uom.write, [uom], {
                'rate': 0.0,
                'factor': 0.0,
                })
        transaction.rollback()

    @with_transaction()
    def test_uom_check_factor_and_rate(self):
        'Test uom check_factor_and_rate constraint'
        pool = Pool()
        UomCategory = pool.get('product.uom.category')
        Uom = pool.get('product.uom')
        transaction = Transaction()
        category, = UomCategory.create([{'name': 'Test'}])

        self.assertRaises(Exception, Uom.create, [{
                'name': 'Test',
                'symbol': 'T',
                'category': category.id,
                'rate': 2,
                'factor': 2,
                }])
        transaction.rollback()

        def create():
            category, = UomCategory.create([{'name': 'Test'}])
            return Uom.create([{
                        'name': 'Test',
                        'symbol': 'T',
                        'category': category.id,
                        'rate': 1.0,
                        'factor': 1.0,
                        }])[0]

        uom = create()
        self.assertRaises(Exception, Uom.write, [uom], {
                'rate': 2.0,
                })
        transaction.rollback()

        uom = create()
        self.assertRaises(Exception, Uom.write, [uom], {
                'factor': 2.0,
                })
        transaction.rollback()

    @with_transaction()
    def test_uom_select_accurate_field(self):
        'Test uom select_accurate_field function'
        pool = Pool()
        Uom = pool.get('product.uom')
        tests = [
            ('Meter', 'factor'),
            ('Kilometer', 'factor'),
            ('Centimeter', 'rate'),
            ('Foot', 'factor'),
            ]
        for name, result in tests:
            uom, = Uom.search([
                    ('name', '=', name),
                    ], limit=1)
            self.assertEqual(result, uom.accurate_field)

    @with_transaction()
    def test_uom_compute_qty(self):
        'Test uom compute_qty function'
        pool = Pool()
        Uom = pool.get('product.uom')
        tests = [
            ('Kilogram', 100, 'Gram', 100000, 100000),
            ('Gram', 1, 'Pound', 0.0022046226218487759, 0.0),
            ('Second', 5, 'Minute', 0.083333333333333343, 0.08),
            ('Second', 25, 'Hour', 0.0069444444444444441, 0.01),
            ('Millimeter', 3, 'Inch', 0.11811023622047245, 0.12),
            ('Millimeter', 0, 'Inch', 0, 0),
            ('Millimeter', None, 'Inch', None, None),
            ]
        for from_name, qty, to_name, result, rounded_result in tests:
            from_uom, = Uom.search([
                    ('name', '=', from_name),
                    ], limit=1)
            to_uom, = Uom.search([
                    ('name', '=', to_name),
                    ], limit=1)
            self.assertEqual(result, Uom.compute_qty(
                    from_uom, qty, to_uom, False))
            self.assertEqual(rounded_result, Uom.compute_qty(
                    from_uom, qty, to_uom, True))
        self.assertEqual(0.2, Uom.compute_qty(None, 0.2, None, False))
        self.assertEqual(0.2, Uom.compute_qty(None, 0.2, None, True))

        tests_exceptions = [
            ('Millimeter', 3, 'Pound', ValueError),
            ('Kilogram', 'not a number', 'Pound', TypeError),
            ]
        for from_name, qty, to_name, exception in tests_exceptions:
            from_uom, = Uom.search([
                    ('name', '=', from_name),
                    ], limit=1)
            to_uom, = Uom.search([
                    ('name', '=', to_name),
                    ], limit=1)
            self.assertRaises(exception, Uom.compute_qty,
                from_uom, qty, to_uom, False)
            self.assertRaises(exception, Uom.compute_qty,
                from_uom, qty, to_uom, True)
        self.assertRaises(ValueError, Uom.compute_qty,
            None, qty, to_uom, True)
        self.assertRaises(ValueError, Uom.compute_qty,
            from_uom, qty, None, True)

    @with_transaction()
    def test_uom_compute_qty_category(self):
        "Test uom compute_qty with different category"
        pool = Pool()
        Uom = pool.get('product.uom')

        g, = Uom.search([
                ('name', '=', "Gram"),
                ], limit=1)
        m3, = Uom.search([
                ('name', '=', "Cubic meter"),
                ], limit=1)

        for quantity, result, keys in [
                (10000, 0.02, dict(factor=2)),
                (20000, 0.01, dict(rate=2)),
                (30000, 0.01, dict(rate=3, factor=0.333333, round=False)),
                ]:
            msg = 'quantity: %r, keys: %r' % (quantity, keys)
            self.assertEqual(
                Uom.compute_qty(g, quantity, m3, **keys), result,
                msg=msg)

    @with_transaction()
    def test_uom_compute_price(self):
        'Test uom compute_price function'
        pool = Pool()
        Uom = pool.get('product.uom')
        tests = [
            ('Kilogram', Decimal('100'), 'Gram', Decimal('0.1')),
            ('Gram', Decimal('1'), 'Pound', Decimal('453.59237')),
            ('Second', Decimal('5'), 'Minute', Decimal('300')),
            ('Second', Decimal('25'), 'Hour', Decimal('90000')),
            ('Millimeter', Decimal('3'), 'Inch', Decimal('76.2')),
            ('Millimeter', Decimal('0'), 'Inch', Decimal('0')),
            ('Millimeter', None, 'Inch', None),
            ]
        for from_name, price, to_name, result in tests:
            from_uom, = Uom.search([
                    ('name', '=', from_name),
                    ], limit=1)
            to_uom, = Uom.search([
                    ('name', '=', to_name),
                    ], limit=1)
            self.assertEqual(result, Uom.compute_price(
                    from_uom, price, to_uom))
        self.assertEqual(Decimal('0.2'), Uom.compute_price(
                None, Decimal('0.2'), None))

        tests_exceptions = [
            ('Millimeter', Decimal('3'), 'Pound', ValueError),
            ('Kilogram', 'not a number', 'Pound', TypeError),
            ]
        for from_name, price, to_name, exception in tests_exceptions:
            from_uom, = Uom.search([
                    ('name', '=', from_name),
                    ], limit=1)
            to_uom, = Uom.search([
                    ('name', '=', to_name),
                    ], limit=1)
            self.assertRaises(exception, Uom.compute_price,
                from_uom, price, to_uom)
        self.assertRaises(ValueError, Uom.compute_price,
            None, price, to_uom)
        self.assertRaises(ValueError, Uom.compute_price,
            from_uom, price, None)

    @with_transaction()
    def test_uom_compute_price_category(self):
        "Test uom compute_price with different category"
        pool = Pool()
        Uom = pool.get('product.uom')

        g, = Uom.search([
                ('name', '=', "Gram"),
                ], limit=1)
        m3, = Uom.search([
                ('name', '=', "Cubic meter"),
                ], limit=1)

        for price, result, keys in [
                (Decimal('0.001'), Decimal('500'), dict(factor=2)),
                (Decimal('0.002'), Decimal('4000'), dict(rate=2)),
                (Decimal('0.003'), Decimal('9000'), dict(
                        rate=3, factor=0.333333)),
                ]:
            msg = 'price: %r, keys: %r' % (price, keys)
            self.assertEqual(
                Uom.compute_price(g, price, m3, **keys), result,
                msg=msg)

    @with_transaction()
    def test_uom_modify_factor_rate(self):
        "Test can not modify factor or rate of uom"
        pool = Pool()
        Uom = pool.get('product.uom')
        g, = Uom.search([('name', '=', "Gram")])

        g.factor = 1
        g.rate = 1

        with self.assertRaises(UOMAccessError):
            g.save()

    @with_transaction()
    def test_uom_modify_category(self):
        "Test can not modify category of uom"
        pool = Pool()
        Uom = pool.get('product.uom')
        Category = pool.get('product.uom.category')
        g, = Uom.search([('name', '=', "Gram")])
        units, = Category.search([('name', '=', "Units")])

        g.category = units

        with self.assertRaises(UOMAccessError):
            g.save()

    @with_transaction()
    def test_uom_increase_digits(self):
        "Test can increase digits of uom"
        pool = Pool()
        Uom = pool.get('product.uom')
        g, = Uom.search([('name', '=', "Gram")])

        g.digits += 1

        g.save()

    @with_transaction()
    def test_uom_decrease_digits(self):
        "Test can not decrease digits of uom"
        pool = Pool()
        Uom = pool.get('product.uom')
        g, = Uom.search([('name', '=', "Gram")])

        g.digits -= 1
        g.rounding = 1

        with self.assertRaises(UOMAccessError):
            g.save()

    @with_transaction()
    def test_product_search_domain(self):
        'Test product.product search_domain function'
        pool = Pool()
        Uom = pool.get('product.uom')
        Template = pool.get('product.template')
        Product = pool.get('product.product')

        kilogram, = Uom.search([
                ('name', '=', 'Kilogram'),
                ], limit=1)
        millimeter, = Uom.search([
                ('name', '=', 'Millimeter'),
                ])
        pt1, pt2 = Template.create([{
                    'name': 'P1',
                    'type': 'goods',
                    'default_uom': kilogram.id,
                    'products': [('create', [{
                                    'code': '1',
                                    }])]
                    }, {
                    'name': 'P2',
                    'type': 'goods',
                    'default_uom': millimeter.id,
                    'products': [('create', [{
                                    'code': '2',
                                    }])]
                    }])
        p, = Product.search([
                ('default_uom.name', '=', 'Kilogram'),
                ])
        self.assertEqual(p, pt1.products[0])
        p, = Product.search([
                ('default_uom.name', '=', 'Millimeter'),
                ])
        self.assertEqual(p, pt2.products[0])

    @with_transaction()
    def test_search_domain_conversion(self):
        'Test the search domain conversion'
        pool = Pool()
        Category = pool.get('product.category')
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        category1, = Category.create([{'name': 'Category1'}])
        category2, = Category.create([{'name': 'Category2'}])
        uom, = Uom.search([], limit=1)
        values1 = {
            'name': 'Some product-1',
            'categories': [('add', [category1.id])],
            'type': 'goods',
            'default_uom': uom.id,
            'products': [('create', [{}])],
            }
        values2 = {
            'name': 'Some product-2',
            'categories': [('add', [category2.id])],
            'type': 'goods',
            'default_uom': uom.id,
            'products': [('create', [{}])],
            }

        # This is a false positive as there is 1 product with the
        # template 1 and the same product with category 1. If you do not
        # create two categories (or any other relation on the template
        # model) you wont be able to check as in most cases the
        # id of the template and the related model would be same (1).
        # So two products have been created with same category. So that
        # domain ('template.categories', '=', 1) will return 2 records which
        # it supposed to be.
        template1, template2, template3, template4 = Template.create(
            [values1, values1.copy(), values2, values2.copy()]
            )
        self.assertEqual(Product.search([], count=True), 4)
        self.assertEqual(
            Product.search([
                    ('categories', '=', category1.id),
                    ], count=True), 2)

        self.assertEqual(
            Product.search([
                    ('template.categories', '=', category1.id),
                    ], count=True), 2)

        self.assertEqual(
            Product.search([
                    ('categories', '=', category2.id),
                    ], count=True), 2)
        self.assertEqual(
            Product.search([
                    ('template.categories', '=', category2.id),
                    ], count=True), 2)

    @with_transaction()
    def test_uom_rounding(self):
        'Test uom rounding functions'
        pool = Pool()
        Uom = pool.get('product.uom')
        tests = [
            (2.53, .1, 2.5, 2.6, 2.5),
            (3.8, .1, 3.8, 3.8, 3.8),
            (3.7, .1, 3.7, 3.7, 3.7),
            (1.3, .5, 1.5, 1.5, 1.0),
            (1.1, .3, 1.2, 1.2, 0.9),
            (17, 10, 20, 20, 10),
            (7, 10, 10, 10, 0),
            (4, 10, 0, 10, 0),
            (17, 15, 15, 30, 15),
            (2.5, 1.4, 2.8, 2.8, 1.4),
            ]
        for number, precision, round, ceil, floor in tests:
            uom = Uom(rounding=precision)
            self.assertEqual(uom.round(number), round)
            self.assertEqual(uom.ceil(number), ceil)
            self.assertEqual(uom.floor(number), floor)

    @with_transaction()
    def test_product_order(self):
        'Test product field order'
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        uom, = Uom.search([], limit=1)
        values1 = {
            'name': 'Product A',
            'type': 'assets',
            'default_uom': uom.id,
            'products': [('create', [{'suffix_code': 'AA'}])],
            }
        values2 = {
            'name': 'Product B',
            'type': 'goods',
            'default_uom': uom.id,
            'products': [('create', [{'suffix_code': 'BB'}])],
            }

        template1, template2 = Template.create([values1, values2])
        product1, product2 = Product.search([])

        # Non-inherited field.
        self.assertEqual(
            Product.search([], order=[('code', 'ASC')]), [product1, product2])
        self.assertEqual(
            Product.search([], order=[('code', 'DESC')]), [product2, product1])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('code', 'ASC')]),
                [product1, product2])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('code', 'DESC')]),
                [product2, product1])

        # Inherited field with custom order.
        self.assertEqual(
            Product.search([], order=[('name', 'ASC')]), [product1, product2])
        self.assertEqual(
            Product.search([], order=[('name', 'DESC')]), [product2, product1])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('name', 'ASC')]),
                [product1, product2])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('name', 'DESC')]),
                [product2, product1])

        # Inherited field without custom order.
        self.assertEqual(
            Product.search([], order=[('type', 'ASC')]), [product1, product2])
        self.assertEqual(
            Product.search([], order=[('type', 'DESC')]), [product2, product1])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('type', 'ASC')]),
                [product1, product2])
        self.assertEqual(Product.search(
                [('name', 'like', '%')], order=[('type', 'DESC')]),
                [product2, product1])

    def test_round_price(self):
        for value, result in [
                (Decimal('1'), Decimal('1.0000')),
                (Decimal('1.12345'), Decimal('1.1234')),
                (1, Decimal('1')),
                ]:
            with self.subTest(value=value):
                self.assertEqual(round_price(value), result)

    @with_transaction()
    def test_product_identifier_get_single_type(self):
        "Test identifier get with a single type"
        pool = Pool()
        Identifier = pool.get('product.identifier')
        Product = pool.get('product.product')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')

        uom, = Uom.search([], limit=1)
        template = Template(name="Product", default_uom=uom)
        template.save()
        product = Product(template=template)
        product.identifiers = [
            Identifier(code='FOO'),
            Identifier(type='ean', code='978-0-471-11709-4'),
            ]
        product.save()

        self.assertEqual(
            product.identifier_get('ean').code,
            '978-0-471-11709-4')

    @with_transaction()
    def test_product_identifier_get_many_types(self):
        "Test identifier get with many types"
        pool = Pool()
        Identifier = pool.get('product.identifier')
        Product = pool.get('product.product')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')

        uom, = Uom.search([], limit=1)
        template = Template(name="Product", default_uom=uom)
        template.save()
        product = Product(template=template)
        product.identifiers = [
            Identifier(code='FOO'),
            Identifier(type='isbn', code='0-6332-4980-7'),
            Identifier(type='ean', code='978-0-471-11709-4'),
            ]
        product.save()

        self.assertEqual(
            product.identifier_get({'ean', 'isbn'}).code,
            '0-6332-4980-7')

    @with_transaction()
    def test_product_identifier_get_any(self):
        "Test identifier get for any type"
        pool = Pool()
        Identifier = pool.get('product.identifier')
        Product = pool.get('product.product')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')

        uom, = Uom.search([], limit=1)
        template = Template(name="Product", default_uom=uom)
        template.save()
        product = Product(template=template)
        product.identifiers = [
            Identifier(code='FOO'),
            ]
        product.save()

        self.assertEqual(product.identifier_get(None).code, 'FOO')

    @with_transaction()
    def test_product_identifier_get_unknown_type(self):
        "Test identifier get with a unknown type"
        pool = Pool()
        Identifier = pool.get('product.identifier')
        Product = pool.get('product.product')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')

        uom, = Uom.search([], limit=1)
        template = Template(name="Product", default_uom=uom)
        template.save()
        product = Product(template=template)
        product.identifiers = [
            Identifier(code='FOO'),
            ]
        product.save()

        self.assertEqual(product.identifier_get('ean'), None)


del ModuleTestCase
