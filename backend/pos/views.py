from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.db.models.functions import TruncDate, TruncHour
from decimal import Decimal

from .models import Category, Product, Sale, SaleItem, Refund, RefundItem, AuditLog
from .serializers import (
    CategorySerializer, ProductSerializer,
    SaleSerializer, SaleCreateSerializer, UserSerializer,
    RefundSerializer, RefundCreateSerializer, AuditLogSerializer,
)
from .permissions import IsManagerOrAdmin, IsCashierOrHigher
from .pdf import generate_receipt, generate_refund_receipt
from . import reports as rpt
from .audit import log_action


class ProductPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrAdmin]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsCashierOrHigher]
    pagination_class = ProductPagination

    def get_queryset(self):
        qs = Product.objects.filter(active=True)
        barcode = self.request.query_params.get('barcode')
        if barcode:
            qs = qs.filter(barcode=barcode)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAdmin()]
        return [IsCashierOrHigher()]

    def perform_create(self, serializer):
        product = serializer.save()
        log_action(self.request.user, 'PRODUCT_CREATE', 'Product', product.id,
                   {'name': product.name, 'price': str(product.price)})

    def perform_update(self, serializer):
        old = self.get_object()
        old_price = old.price
        old_stock = old.stock
        product = serializer.save()

        if old_price != product.price:
            log_action(self.request.user, 'PRICE_CHANGE', 'Product', product.id,
                       {'name': product.name, 'old_price': str(old_price), 'new_price': str(product.price)})
        if old_stock != product.stock:
            log_action(self.request.user, 'STOCK_CHANGE', 'Product', product.id,
                       {'name': product.name, 'old_stock': old_stock, 'new_stock': product.stock})

    def perform_destroy(self, instance):
        log_action(self.request.user, 'PRODUCT_DELETE', 'Product', instance.id,
                   {'name': instance.name})
        instance.active = False
        instance.save()

    @action(detail=False, methods=['get'], url_path='by-barcode/(?P<code>[^/.]+)')
    def by_barcode(self, request, code=None):
        try:
            product = Product.objects.get(barcode=code, active=True)
            return Response(ProductSerializer(product).data)
        except Product.DoesNotExist:
            return Response({'detail': 'Proizvod nije nađen.'}, status=404)


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsCashierOrHigher]

    def get_queryset(self):
        user = self.request.user
        qs = Sale.objects.all()
        if not user.groups.filter(name__in=['manager', 'admin']).exists():
            qs = qs.filter(Q(cashier=user) | Q(opened_by=user))
        return qs

    def get_locked_sale(self):
        sale = self.get_object()
        return Sale.objects.select_for_update().get(pk=sale.pk)

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()
        log_action(request.user, 'SALE_CREATE', 'Sale', sale.id, {'total': str(sale.total)})
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='open')
    def list_open(self, request):
        sales = (
            Sale.objects.filter(status__in=['PENDING', 'HELD'], opened_by=request.user)
            .prefetch_related('items__product')
            .order_by('created_at')
        )
        return Response(SaleSerializer(sales, many=True).data)

    @action(detail=False, methods=['post'], url_path='open-new')
    def open_new(self, request):
        sale = Sale.objects.create(
            cashier=request.user,
            opened_by=request.user,
            payment_method='CASH',
            status='PENDING',
            terminal_id=request.data.get('terminal_id', ''),
        )
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-item')
    @transaction.atomic
    def add_item(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun nije otvoren.'}, status=400)

        product_id = request.data.get('product_id')
        quantity = serializers.IntegerField(min_value=1).run_validation(
            request.data.get('quantity', 1)
        )
        product = get_object_or_404(
            Product.objects.select_for_update(), id=product_id, active=True
        )

        existing = sale.items.filter(product=product).first()
        current_qty = existing.quantity if existing else 0

        if product.stock < current_qty + quantity:
            return Response({'detail': f'Nema dovoljno na stanju za {product.name}.'}, status=400)

        unit_price = product.final_price
        tax = (unit_price * quantity * product.tax_rate / Decimal('100')).quantize(Decimal('0.01'))

        if existing:
            existing.quantity += quantity
            existing.tax_amount = (existing.unit_price * existing.quantity * product.tax_rate / Decimal('100')).quantize(Decimal('0.01'))
            existing.save()
        else:
            SaleItem.objects.create(
                sale=sale, product=product, quantity=quantity,
                unit_price=unit_price, tax_amount=tax,
                discount_amount=product.price - unit_price,
            )

        sale.recalculate()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='remove-item')
    @transaction.atomic
    def remove_item(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun nije otvoren.'}, status=400)
        item = get_object_or_404(SaleItem, id=request.data.get('item_id'), sale=sale)
        item.delete()
        sale.recalculate()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='update-item')
    @transaction.atomic
    def update_item(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun nije otvoren.'}, status=400)

        item_id = request.data.get('item_id')
        quantity = serializers.IntegerField(min_value=0).run_validation(
            request.data.get('quantity', 1)
        )
        if quantity <= 0:
            return self.remove_item(request, pk)

        item = get_object_or_404(SaleItem, id=item_id, sale=sale)
        product = Product.objects.select_for_update().get(pk=item.product_id)
        other_qty = sum(i.quantity for i in sale.items.filter(product=item.product).exclude(id=item.id))
        if product.stock < other_qty + quantity:
            return Response({'detail': f'Nema dovoljno na stanju za {product.name}.'}, status=400)

        item.quantity = quantity
        item.tax_amount = (item.unit_price * quantity * item.product.tax_rate / Decimal('100')).quantize(Decimal('0.01'))
        item.save()
        sale.recalculate()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='set-item-discount')
    @transaction.atomic
    def set_item_discount(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun nije otvoren.'}, status=400)

        item = get_object_or_404(SaleItem, id=request.data.get('item_id'), sale=sale)
        percent = serializers.DecimalField(
            max_digits=5, decimal_places=2,
            min_value=Decimal('0.00'), max_value=Decimal('100.00'),
        ).run_validation(request.data.get('percent', 0))

        item.item_discount_percent = percent
        item.save()
        sale.recalculate()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='set-discount')
    @transaction.atomic
    def set_discount(self, request, pk=None):
        """Popust na ceo račun."""
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun nije otvoren.'}, status=400)

        percent = serializers.DecimalField(
            max_digits=5, decimal_places=2,
            min_value=Decimal('0.00'), max_value=Decimal('100.00'),
        ).run_validation(request.data.get('percent', 0))

        # Samo manager/admin može više od 20%
        if percent > 20 and not request.user.groups.filter(name__in=['manager', 'admin']).exists():
            return Response({'detail': 'Samo manager može dati popust veći od 20%.'}, status=403)

        sale.discount_percent = percent
        sale.save()
        sale.recalculate()
        log_action(request.user, 'SALE_DISCOUNT', 'Sale', sale.id, {'percent': str(percent)})
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='hold')
    @transaction.atomic
    def hold_sale(self, request, pk=None):
        """Zadrži račun (npr. mušterija zaboravila novčanik)."""
        sale = self.get_locked_sale()
        if sale.status != 'PENDING':
            return Response({'detail': 'Samo otvoreni računi se mogu zadržati.'}, status=400)
        sale.status = 'HELD'
        sale.note = request.data.get('note', '')
        sale.save()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='resume')
    @transaction.atomic
    def resume_sale(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status != 'HELD':
            return Response({'detail': 'Račun nije zadržan.'}, status=400)
        sale.status = 'PENDING'
        sale.save()
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='checkout')
    @transaction.atomic
    def checkout(self, request, pk=None):
        sale = self.get_object()
        sale = Sale.objects.select_for_update().get(pk=sale.pk)
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Račun je već zatvoren.'}, status=400)
        if not sale.items.exists():
            return Response({'detail': 'Račun je prazan.'}, status=400)

        items = list(sale.items.select_related('product'))
        products = Product.objects.select_for_update().filter(
            id__in=[item.product_id for item in items]
        ).order_by('id').in_bulk()
        for item in items:
            product = products[item.product_id]
            if product.stock < item.quantity:
                return Response({'detail': f'Nema dovoljno na stanju za {product.name}.'}, status=400)

        payment_method = serializers.ChoiceField(
            choices=[choice[0] for choice in Sale.PAYMENT_CHOICES]
        ).run_validation(request.data.get('payment_method', 'CASH'))
        payment_splits = None
        if payment_method == 'SPLIT':
            raw_splits = request.data.get('payment_splits')
            if not isinstance(raw_splits, list) or not raw_splits:
                raise serializers.ValidationError({
                    'payment_splits': 'Split plaćanje mora sadržavati iznose.'
                })
            payment_splits = []
            split_total = Decimal('0.00')
            for split in raw_splits:
                if not isinstance(split, dict):
                    raise serializers.ValidationError({'payment_splits': 'Neispravna stavka plaćanja.'})
                method = serializers.ChoiceField(choices=['CASH', 'CARD']).run_validation(
                    split.get('method')
                )
                amount = serializers.DecimalField(
                    max_digits=12, decimal_places=2, min_value=Decimal('0.00')
                ).run_validation(split.get('amount'))
                payment_splits.append({'method': method, 'amount': str(amount)})
                split_total += amount
            if split_total != sale.total:
                raise serializers.ValidationError({
                    'payment_splits': 'Zbir split plaćanja mora odgovarati ukupnom iznosu.'
                })

        sale.payment_method = payment_method
        sale.payment_splits = payment_splits
        sale.customer_name = request.data.get('customer_name', sale.customer_name)
        sale.customer_phone = request.data.get('customer_phone', sale.customer_phone)
        sale.cashier = request.user
        sale.status = 'COMPLETED'
        sale.save()

        # Smanji stock
        for item in items:
            product = products[item.product_id]
            product.stock -= item.quantity
            product.save(update_fields=['stock'])

        log_action(request.user, 'SALE_CHECKOUT', 'Sale', sale.id,
                   {'total': str(sale.total), 'payment': sale.payment_method})

        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    @transaction.atomic
    def cancel(self, request, pk=None):
        sale = self.get_locked_sale()
        if sale.status not in ['PENDING', 'HELD']:
            return Response({'detail': 'Samo otvoreni računi se mogu otkazati.'}, status=400)
        log_action(request.user, 'SALE_CANCEL', 'Sale', sale.id, {'total': str(sale.total)})
        sale.delete()
        return Response(status=204)

    @action(detail=True, methods=['get'], url_path='receipt')
    def receipt(self, request, pk=None):
        sale = self.get_object()
        if sale.status not in ['COMPLETED', 'REFUNDED', 'PARTIALLY_REFUNDED']:
            return Response({'detail': 'PDF samo za završene.'}, status=400)
        buffer = generate_receipt(sale)
        return FileResponse(buffer, as_attachment=True, filename=f'{sale.receipt_number}.pdf')


class RefundViewSet(viewsets.ModelViewSet):
    serializer_class = RefundSerializer
    permission_classes = [IsManagerOrAdmin]

    def get_queryset(self):
        return Refund.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = RefundCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        refund = serializer.save()

        log_action(request.user, 'SALE_REFUND', 'Refund', refund.id,
                   {'original_sale': refund.original_sale_id, 'total': str(refund.total)})

        return Response(RefundSerializer(refund).data, status=201)

    @action(detail=False, methods=['get'], url_path='find-sale')
    def find_sale(self, request):
        """Nađi prodaju po broju računa (za refundaciju)."""
        receipt = request.query_params.get('receipt')
        if not receipt:
            return Response({'detail': 'Proslijedi ?receipt=R-...'}, status=400)

        try:
            sale = Sale.objects.get(receipt_number=receipt)
        except Sale.DoesNotExist:
            return Response({'detail': 'Račun nije nađen.'}, status=404)

        if sale.status == 'REFUNDED':
            return Response({'detail': 'Račun je već u cjelosti refundiran.'}, status=400)

        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['get'], url_path='receipt')
    def receipt(self, request, pk=None):
        refund = self.get_object()
        buffer = generate_refund_receipt(refund)
        return FileResponse(buffer, as_attachment=True, filename=f'{refund.receipt_number}.pdf')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsManagerOrAdmin]

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').all()
        action_filter = self.request.query_params.get('action')
        user_filter = self.request.query_params.get('user')
        if action_filter:
            qs = qs.filter(action=action_filter)
        if user_filter:
            qs = qs.filter(user__username=user_filter)
        return qs


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsManagerOrAdmin]


# ---------- IZVJEŠTAJI ----------
@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_summary(request):
    return Response(rpt.summary())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_revenue_per_day(request):
    return Response(rpt.revenue_per_day())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_top_products(request):
    return Response(rpt.top_products())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_revenue_per_cashier(request):
    return Response(rpt.revenue_per_cashier())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_revenue_per_category(request):
    return Response(rpt.revenue_per_category())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_revenue_per_hour(request):
    return Response(rpt.revenue_per_hour())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_top_margin(request):
    return Response(rpt.top_margin_products())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_low_stock(request):
    return Response(rpt.low_stock_products())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_average_basket(request):
    return Response(rpt.average_basket())


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def report_comparison(request):
    return Response(rpt.comparison_periods())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    groups = [g.name for g in user.groups.all()]
    if user.is_superuser and 'admin' not in groups:
        groups.append('admin')
    return Response({
        'id': user.id,
        'username': user.username,
        'groups': groups,
    })
from .models import ReceiptSettings
from .serializers import ReceiptSettingsSerializer
from .audit import log_action
from . import reports as rpt


class ReceiptSettingsViewSet(viewsets.ViewSet):
    """Singleton: GET / PUT /api/receipt-settings/"""
    permission_classes = [IsManagerOrAdmin]

    def list(self, request):
        settings = ReceiptSettings.get_solo()
        return Response(ReceiptSettingsSerializer(settings).data)

    def create(self, request):
        settings = ReceiptSettings.get_solo()
        serializer = ReceiptSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, 'SETTINGS_CHANGE', 'ReceiptSettings', 1,
                   {'changed': list(request.data.keys())})
        return Response(serializer.data)

    def update(self, request, pk=None):
        return self.create(request)


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def daily_report(request):
    date_value = request.query_params.get('date')
    date = serializers.DateField().run_validation(date_value) if date_value else None
    cashier = request.query_params.get('cashier')
    return Response(rpt.daily_report_data(date=date, cashier=cashier))


@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])
def periodic_report(request):
    date_from = request.query_params.get('from')
    date_to = request.query_params.get('to')
    cashier = request.query_params.get('cashier')
    if not date_from or not date_to:
        return Response({'detail': 'Proslijedi ?from=YYYY-MM-DD&to=YYYY-MM-DD'}, status=400)
    date_from = serializers.DateField().run_validation(date_from)
    date_to = serializers.DateField().run_validation(date_to)
    if date_from > date_to:
        return Response({'detail': 'Početni datum mora biti prije ili isti kao završni datum.'}, status=400)
    return Response(rpt.periodic_report_data(date_from=date_from, date_to=date_to, cashier=cashier))