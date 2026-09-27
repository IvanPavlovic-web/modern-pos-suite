from types import SimpleNamespace
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from .models import Category, Product, Refund, Sale, SaleItem
from .management.commands.seed_data import PRODUCTS
from . import reports
from .serializers import RefundCreateSerializer, SaleCreateSerializer


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class SaleFlowTests(TestCase):
	def setUp(self):
		cashier_group, _ = Group.objects.get_or_create(name='cashier')
		self.user = User.objects.create_user(username='cashier', password='test-password')
		self.user.groups.add(cashier_group)
		self.product = Product.objects.create(
			name='Test product', barcode='12345', price='10.00', stock=5,
		)

	def test_direct_sale_decrements_stock_once_for_duplicate_lines(self):
		serializer = SaleCreateSerializer(
			data={
				'payment_method': 'CASH',
				'items': [
					{'product_id': self.product.id, 'quantity': 2},
					{'product_id': self.product.id, 'quantity': 1},
				],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)
		sale = serializer.save()

		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 2)
		self.assertEqual(sale.items.count(), 2)
		self.assertEqual(sale.status, 'COMPLETED')

	def test_direct_sale_rejects_aggregate_quantity_over_stock(self):
		serializer = SaleCreateSerializer(
			data={
				'payment_method': 'CASH',
				'items': [
					{'product_id': self.product.id, 'quantity': 3},
					{'product_id': self.product.id, 'quantity': 3},
				],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

		with self.assertRaises(ValidationError):
			serializer.save()

		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 5)
		self.assertEqual(Sale.objects.count(), 0)

	def test_direct_split_sale_requires_exact_valid_payment_splits(self):
		base_data = {
			'payment_method': 'SPLIT',
			'items': [{'product_id': self.product.id, 'quantity': 1}],
		}
		invalid = SaleCreateSerializer(
			data={**base_data, 'payment_splits': [{'method': 'CASH', 'amount': '9.00'}]},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(invalid.is_valid(), invalid.errors)
		with self.assertRaises(ValidationError):
			invalid.save()

		valid = SaleCreateSerializer(
			data={
				**base_data,
				'payment_splits': [
					{'method': 'CASH', 'amount': '4.00'},
					{'method': 'CARD', 'amount': '6.00'},
				],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(valid.is_valid(), valid.errors)
		sale = valid.save()
		self.assertEqual(sale.total, 10)
		self.assertEqual(sum(Decimal(p['amount']) for p in sale.payment_splits), 10)

	def test_checkout_decrements_stock_and_cannot_be_repeated(self):
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='PENDING',
		)
		SaleItem.objects.create(
			sale=sale, product=self.product, quantity=2, unit_price='10.00',
		)
		client = APIClient()
		client.force_authenticate(self.user)

		first = client.post(f'/api/sales/{sale.id}/checkout/', {'payment_method': 'CASH'}, format='json')
		second = client.post(f'/api/sales/{sale.id}/checkout/', {'payment_method': 'CASH'}, format='json')

		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 400)
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 3)

	def test_invalid_refund_rolls_back_all_changes(self):
		second_product = Product.objects.create(
			name='Second product', barcode='54321', price='20.00', stock=0,
		)
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='COMPLETED',
		)
		first_item = SaleItem.objects.create(
			sale=sale, product=self.product, quantity=1, unit_price='10.00',
		)
		second_item = SaleItem.objects.create(
			sale=sale, product=second_product, quantity=1, unit_price='20.00',
			refunded_quantity=1,
		)
		serializer = RefundCreateSerializer(
			data={
				'sale_id': sale.id,
				'payment_method': 'CASH',
				'items': [
					{'sale_item_id': first_item.id, 'quantity': 1},
					{'sale_item_id': second_item.id, 'quantity': 1},
				],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

		with self.assertRaises(ValidationError):
			serializer.save()

		self.product.refresh_from_db()
		first_item.refresh_from_db()
		self.assertEqual(self.product.stock, 5)
		self.assertEqual(first_item.refunded_quantity, 0)
		self.assertEqual(Refund.objects.count(), 0)

	def test_seed_product_barcodes_are_unique(self):
		barcodes = [product[1] for product in PRODUCTS]
		self.assertEqual(len(barcodes), len(set(barcodes)))

	def test_reports_use_net_revenue_and_exclude_open_sales(self):
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='PARTIALLY_REFUNDED', total='30.00',
		)
		item = SaleItem.objects.create(
			sale=sale, product=self.product, quantity=3, unit_price='10.00', refunded_quantity=1,
		)
		Refund.objects.create(
			original_sale=sale, cashier=self.user, total='10.00', payment_method='CASH',
		)
		open_sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='PENDING',
		)
		SaleItem.objects.create(
			sale=open_sale, product=self.product, quantity=5, unit_price='10.00',
		)

		summary = reports.summary()
		product_report = reports.top_products()

		self.assertEqual(summary['total_revenue'], 20.0)
		self.assertEqual(summary['total_sales'], 1)
		self.assertEqual(summary['total_items'], 2)
		self.assertEqual(product_report[0]['total_sold'], 2)
		self.assertEqual(product_report[0]['total_revenue'], 20.0)

	def test_product_and_category_reports_apply_sale_discounts(self):
		category = Category.objects.create(name='Test category')
		self.product.category = category
		self.product.save(update_fields=['category'])
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='COMPLETED',
			total='16.20', discount_percent='10.00',
		)
		SaleItem.objects.create(
			sale=sale, product=self.product, quantity=2, unit_price='10.00',
			item_discount_percent='10.00',
		)

		product_report = reports.top_products()
		category_report = reports.revenue_per_category()

		self.assertEqual(product_report[0]['total_revenue'], 16.2)
		self.assertEqual(category_report[0]['total'], 16.2)

	def test_product_list_can_return_more_than_default_page(self):
		for index in range(60):
			Product.objects.create(
				name=f'Extra product {index}', barcode=f'900000000{index:04d}',
				price='1.00', stock=1,
			)
		client = APIClient()
		client.force_authenticate(self.user)

		response = client.get('/api/products/?page_size=1000')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 61)
		self.assertEqual(len(response.data['results']), 61)

	def test_cashier_cannot_checkout_invalid_quantity_or_split_total(self):
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='PENDING',
		)
		client = APIClient()
		client.force_authenticate(self.user)
		invalid_quantity = client.post(
			f'/api/sales/{sale.id}/add-item/',
			{'product_id': self.product.id, 'quantity': -1}, format='json',
		)
		self.assertEqual(invalid_quantity.status_code, 400)

		SaleItem.objects.create(
			sale=sale, product=self.product, quantity=1, unit_price='10.00',
		)
		sale.recalculate()
		invalid_split = client.post(
			f'/api/sales/{sale.id}/checkout/',
			{
				'payment_method': 'SPLIT',
				'payment_splits': [
					{'method': 'CASH', 'amount': '5.00'},
					{'method': 'CARD', 'amount': '4.00'},
				],
			},
			format='json',
		)

		self.assertEqual(invalid_split.status_code, 400)
		sale.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(sale.status, 'PENDING')
		self.assertEqual(self.product.stock, 5)

	def test_user_without_cashier_role_cannot_open_sales(self):
		unassigned_user = User.objects.create_user(username='unassigned')
		client = APIClient()
		client.force_authenticate(unassigned_user)

		response = client.post('/api/sales/open-new/', {}, format='json')

		self.assertEqual(response.status_code, 403)
		self.assertEqual(Sale.objects.count(), 0)

	def test_django_superuser_can_access_manager_endpoints_without_group(self):
		superuser = User.objects.create_superuser(
			username='root', email='root@example.com', password='test-password',
		)
		client = APIClient()
		client.force_authenticate(superuser)

		response = client.get('/api/categories/')
		profile = client.get('/api/auth/me/')

		self.assertEqual(response.status_code, 200)
		self.assertIn('admin', profile.data['groups'])

	def test_successful_refund_restores_stock_and_marks_partial(self):
		self.product.stock = 3
		self.product.save(update_fields=['stock'])
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='COMPLETED', total='20.00',
		)
		item = SaleItem.objects.create(
			sale=sale, product=self.product, quantity=2, unit_price='10.00',
		)
		serializer = RefundCreateSerializer(
			data={
				'sale_id': sale.id,
				'payment_method': 'CASH',
				'items': [{'sale_item_id': item.id, 'quantity': 1}],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

		refund = serializer.save()

		self.product.refresh_from_db()
		item.refresh_from_db()
		sale.refresh_from_db()
		self.assertEqual(refund.total, 10)
		self.assertEqual(self.product.stock, 4)
		self.assertEqual(item.refunded_quantity, 1)
		self.assertEqual(sale.status, 'PARTIALLY_REFUNDED')

	def test_refund_amount_applies_item_and_sale_discounts(self):
		sale = Sale.objects.create(
			cashier=self.user, opened_by=self.user, status='COMPLETED',
			total='16.20', discount_percent='10.00',
		)
		item = SaleItem.objects.create(
			sale=sale, product=self.product, quantity=2, unit_price='10.00',
			item_discount_percent='10.00',
		)
		serializer = RefundCreateSerializer(
			data={
				'sale_id': sale.id,
				'payment_method': 'CASH',
				'items': [{'sale_item_id': item.id, 'quantity': 1}],
			},
			context={'request': SimpleNamespace(user=self.user)},
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

		refund = serializer.save()

		self.assertEqual(refund.total, Decimal('8.10'))

	def test_periodic_report_rejects_invalid_date_ranges(self):
		manager_group, _ = Group.objects.get_or_create(name='manager')
		manager = User.objects.create_user(username='manager')
		manager.groups.add(manager_group)
		client = APIClient()
		client.force_authenticate(manager)

		bad_date = client.get('/api/reports/periodic/?from=not-a-date&to=2026-09-27')
		reversed_range = client.get('/api/reports/periodic/?from=2026-09-28&to=2026-09-27')

		self.assertEqual(bad_date.status_code, 400)
		self.assertEqual(reversed_range.status_code, 400)
