from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
from .models import (
    Category, Product, Sale, SaleItem, Refund, RefundItem,
    AuditLog, ReceiptSettings,
)


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'groups')

    def get_groups(self, obj):
        return [g.name for g in obj.groups.all()]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    margin = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'barcode', 'category', 'category_name',
            'price', 'cost_price', 'tax_rate', 'stock', 'min_stock',
            'discount_percent', 'final_price', 'margin', 'unit', 'active',
        )


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_tax_rate = serializers.DecimalField(source='product.tax_rate', max_digits=5, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    available_for_refund = serializers.IntegerField(read_only=True)

    class Meta:
        model = SaleItem
        fields = (
            'id', 'product', 'product_name', 'product_barcode', 'product_unit',
            'product_tax_rate', 'quantity', 'unit_price', 'tax_amount',
            'discount_amount', 'item_discount_percent', 'line_total',
            'refunded_quantity', 'available_for_refund',
        )


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='cashier.username', read_only=True)
    cashier_full = serializers.SerializerMethodField()
    opened_by_name = serializers.CharField(source='opened_by.username', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = (
            'id', 'receipt_number', 'eo_number', 'cashier', 'cashier_name', 'cashier_full',
            'opened_by', 'opened_by_name', 'terminal_id',
            'total', 'total_tax', 'discount_amount', 'discount_percent',
            'payment_method', 'payment_splits', 'amount_paid', 'change_amount',
            'customer_name', 'customer_phone', 'note', 'status',
            'created_at', 'updated_at', 'items', 'items_count',
        )

    def get_cashier_full(self, obj):
        if not obj.cashier:
            return ''
        return f'{obj.cashier.first_name} {obj.cashier.last_name}'.strip() or obj.cashier.username

    def get_items_count(self, obj):
        return obj.items.count()


class SaleCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PaymentSplitSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=['CASH', 'CARD'])
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.00')
    )


class SaleCreateSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=['CASH', 'CARD', 'SPLIT'])
    payment_splits = PaymentSplitSerializer(many=True, required=False)
    items = SaleCreateItemSerializer(many=True, allow_empty=False)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        items_data = validated_data['items']
        quantities = {}
        for item in items_data:
            product_id = item['product_id']
            quantities[product_id] = quantities.get(product_id, 0) + item['quantity']

        products = Product.objects.select_for_update().filter(
            id__in=quantities, active=True
        ).order_by('id').in_bulk()
        if len(products) != len(quantities):
            raise serializers.ValidationError({'items': 'Jedan ili više proizvoda nisu dostupni.'})
        for product_id, quantity in quantities.items():
            product = products[product_id]
            if product.stock < quantity:
                raise serializers.ValidationError(
                    {'items': f'Nema dovoljno na stanju za {product.name}.'}
                )

        payment_method = validated_data['payment_method']
        payment_splits = validated_data.get('payment_splits', [])
        if payment_method == 'SPLIT' and not payment_splits:
            raise serializers.ValidationError({
                'payment_splits': 'Split plaćanje mora sadržavati iznose.'
            })
        if payment_method != 'SPLIT' and payment_splits:
            raise serializers.ValidationError({
                'payment_splits': 'Podjela iznosa je dozvoljena samo za split plaćanje.'
            })

        expected_total = sum(
            (products[item['product_id']].final_price * item['quantity'] for item in items_data),
            Decimal('0.00'),
        )
        split_total = sum((split['amount'] for split in payment_splits), Decimal('0.00'))
        if payment_method == 'SPLIT' and split_total != expected_total:
            raise serializers.ValidationError({
                'payment_splits': 'Zbir split plaćanja mora odgovarati ukupnom iznosu.'
            })

        sale = Sale.objects.create(
            cashier=request.user,
            opened_by=request.user,
            payment_method=payment_method,
            payment_splits=[
                {'method': split['method'], 'amount': str(split['amount'])}
                for split in payment_splits
            ] or None,
            customer_name=validated_data.get('customer_name'),
            customer_phone=validated_data.get('customer_phone'),
            status='COMPLETED',
        )

        total = Decimal('0.00')
        total_tax = Decimal('0.00')

        for item in items_data:
            product = products[item['product_id']]
            qty = item['quantity']
            unit_price = product.final_price
            line_total = unit_price * qty
            tax = (line_total * product.tax_rate / Decimal('100')).quantize(Decimal('0.01'))

            SaleItem.objects.create(
                sale=sale, product=product, quantity=qty,
                unit_price=unit_price, tax_amount=tax,
                discount_amount=(product.price - unit_price) * qty,
            )

            total += line_total
            total_tax += tax

        sale.total = total
        sale.total_tax = total_tax
        sale.save()

        for product_id, quantity in quantities.items():
            product = products[product_id]
            product.stock -= quantity
            product.save(update_fields=['stock'])

        return sale


class RefundItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='sale_item.product.name', read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RefundItem
        fields = ('id', 'sale_item', 'product_name', 'quantity', 'unit_price', 'line_total')


class RefundSerializer(serializers.ModelSerializer):
    items = RefundItemSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='cashier.username', read_only=True)
    original_receipt = serializers.CharField(source='original_sale.receipt_number', read_only=True)

    class Meta:
        model = Refund
        fields = (
            'id', 'receipt_number', 'original_sale', 'original_receipt',
            'cashier', 'cashier_name', 'total', 'reason',
            'payment_method', 'created_at', 'items',
        )


class RefundCreateItemSerializer(serializers.Serializer):
    sale_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class RefundCreateSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['CASH', 'CARD'])
    items = RefundCreateItemSerializer(many=True, allow_empty=False)

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        try:
            sale = Sale.objects.select_for_update().get(id=validated_data['sale_id'])
        except Sale.DoesNotExist:
            raise serializers.ValidationError({'sale_id': 'Prodaja nije pronađena.'})
        if sale.status not in ['COMPLETED', 'PARTIALLY_REFUNDED']:
            raise serializers.ValidationError({'sale_id': 'Refundacija nije moguća za ovaj račun.'})

        requested = {}
        for item_data in validated_data['items']:
            sale_item_id = item_data['sale_item_id']
            requested[sale_item_id] = requested.get(sale_item_id, 0) + item_data['quantity']

        sale_items = SaleItem.objects.select_for_update().filter(
            sale=sale, id__in=requested
        ).select_related('product').in_bulk()
        if len(sale_items) != len(requested):
            raise serializers.ValidationError({'items': 'Stavka ne pripada ovom računu.'})
        for sale_item_id, quantity in requested.items():
            sale_item = sale_items[sale_item_id]
            if quantity > sale_item.available_for_refund:
                raise serializers.ValidationError({
                    'items': (
                        f'Ne možeš refundirati {quantity} za {sale_item.product.name}. '
                        f'Dostupno: {sale_item.available_for_refund}'
                    )
                })

        refund = Refund.objects.create(
            original_sale=sale,
            cashier=request.user,
            reason=validated_data.get('reason', ''),
            payment_method=validated_data['payment_method'],
        )

        total = Decimal('0.00')
        for sale_item_id, qty in requested.items():
            sale_item = sale_items[sale_item_id]
            refund_item = RefundItem.objects.create(
                refund=refund, sale_item=sale_item,
                quantity=qty,
                unit_price=(
                    sale_item.unit_price
                    * (Decimal('1') - sale_item.item_discount_percent / Decimal('100'))
                    * (Decimal('1') - sale.discount_percent / Decimal('100'))
                ).quantize(Decimal('0.01')),
            )

            product = sale_item.product
            product.stock += qty
            product.save(update_fields=['stock'])

            sale_item.refunded_quantity += qty
            sale_item.save(update_fields=['refunded_quantity'])
            total += refund_item.line_total

        refund.total = total
        refund.save()

        all_items = sale.items.all()
        if all(i.available_for_refund == 0 for i in all_items):
            sale.status = 'REFUNDED'
        else:
            sale.status = 'PARTIALLY_REFUNDED'
        sale.save(update_fields=['status'])
        return refund


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_name', 'action', 'target_type',
            'target_id', 'details', 'ip_address', 'created_at',
        )


class ReceiptSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptSettings
        exclude = ('updated_at',)