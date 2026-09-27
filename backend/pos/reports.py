from django.db.models import (
    Sum, Count, Avg, F, OuterRef, Subquery, DecimalField, ExpressionWrapper,
)
from django.db.models.functions import Coalesce, TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from .models import Sale, SaleItem, Product, Refund


def _net_sales():
    refund_totals = (
        Refund.objects.filter(original_sale_id=OuterRef('pk'))
        .order_by()
        .values('original_sale_id')
        .annotate(total=Sum('total'))
        .values('total')[:1]
    )
    money_field = DecimalField(max_digits=12, decimal_places=2)
    return (
        Sale.objects.filter(status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED'])
        .annotate(refunded_total=Coalesce(
            Subquery(refund_totals, output_field=money_field),
            Decimal('0.00'), output_field=money_field,
        ))
        .annotate(net_total=F('total') - F('refunded_total'))
    )


def _sale_item_revenue(quantity):
    return ExpressionWrapper(
        F('unit_price')
        * (Decimal('1.00') - F('item_discount_percent') / Decimal('100.00'))
        * (Decimal('1.00') - F('sale__discount_percent') / Decimal('100.00'))
        * quantity,
        output_field=DecimalField(max_digits=16, decimal_places=4),
    )


def revenue_per_day():
    rows = (
        _net_sales()
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('net_total'), count=Count('id'))
        .order_by('date')
    )
    return [
        {'date': r['date'].strftime('%Y-%m-%d'), 'total': float(r['total'] or 0), 'count': r['count']}
        for r in rows
    ]


def top_products(limit=10):
    rows = (
        SaleItem.objects.filter(
            sale__status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED']
        )
        .annotate(net_quantity=F('quantity') - F('refunded_quantity'))
        .values('product__name')
        .annotate(
            total_sold=Sum('net_quantity'),
            total_revenue=Sum(_sale_item_revenue(F('net_quantity'))),
        )
        .filter(total_sold__gt=0)
        .order_by('-total_sold')[:limit]
    )
    return [
        {'name': r['product__name'], 'total_sold': r['total_sold'],
         'total_revenue': float(r['total_revenue'] or 0)}
        for r in rows
    ]


def revenue_per_cashier():
    rows = (
        _net_sales()
        .values('cashier__username')
        .annotate(total=Sum('net_total'), count=Count('id'))
        .order_by('-total')
    )
    return [
        {'cashier': r['cashier__username'] or '-', 'total': float(r['total'] or 0), 'count': r['count']}
        for r in rows
    ]


def revenue_per_category():
    rows = (
        SaleItem.objects.filter(
            sale__status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED']
        )
        .annotate(net_quantity=F('quantity') - F('refunded_quantity'))
        .values('product__category__name')
        .annotate(
            total=Sum(_sale_item_revenue(F('net_quantity'))),
            count=Sum('net_quantity'),
        )
        .filter(count__gt=0)
        .order_by('-total')
    )
    return [
        {'category': r['product__category__name'] or 'Bez kategorije',
         'total': float(r['total'] or 0), 'count': r['count'] or 0}
        for r in rows
    ]


def revenue_per_hour():
    rows = (
        _net_sales()
        .annotate(hour=TruncHour('created_at'))
        .values('hour')
        .annotate(total=Sum('net_total'), count=Count('id'))
        .order_by('hour')
    )
    return [
        {'hour': r['hour'].strftime('%H:00'), 'total': float(r['total'] or 0), 'count': r['count']}
        for r in rows
    ]


def top_margin_products(limit=10):
    products = Product.objects.filter(active=True).order_by('-price')[:50]
    result = []
    for p in products:
        margin = float(p.price - p.cost_price)
        margin_pct = float((p.price - p.cost_price) / p.price * 100) if p.price > 0 else 0
        result.append({
            'id': p.id, 'name': p.name, 'price': float(p.price),
            'cost_price': float(p.cost_price), 'margin': round(margin, 2),
            'margin_pct': round(margin_pct, 1),
        })
    result.sort(key=lambda x: x['margin'], reverse=True)
    return result[:limit]


def low_stock_products():
    products = Product.objects.filter(active=True, stock__lte=F('min_stock')).order_by('stock')
    return [
        {'id': p.id, 'name': p.name, 'stock': p.stock, 'min_stock': p.min_stock,
         'category': p.category.name if p.category else '-'}
        for p in products
    ]


def average_basket():
    avg = _net_sales().aggregate(avg=Avg('net_total'), count=Count('id'))
    return {'average': float(avg['avg'] or 0), 'count': avg['count']}


def comparison_periods():
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    sales = _net_sales()
    today_total = sales.filter(created_at__date=today).aggregate(s=Sum('net_total'))['s'] or 0
    yesterday_total = sales.filter(created_at__date=yesterday).aggregate(s=Sum('net_total'))['s'] or 0
    week_total = sales.filter(created_at__date__gte=week_ago).aggregate(s=Sum('net_total'))['s'] or 0
    month_total = sales.filter(created_at__date__gte=month_ago).aggregate(s=Sum('net_total'))['s'] or 0

    return {
        'today': float(today_total), 'yesterday': float(yesterday_total),
        'last_7_days': float(week_total), 'last_30_days': float(month_total),
    }


def summary():
    completed = _net_sales()
    return {
        'total_revenue': float(completed.aggregate(s=Sum('net_total'))['s'] or 0),
        'total_sales': completed.count(),
        'total_items': SaleItem.objects.filter(
            sale__status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED']
        ).aggregate(s=Sum(F('quantity') - F('refunded_quantity')))['s'] or 0,
    }


# ============================================================
#  DNEVNI PRESEK STANJA
# ============================================================
def daily_report_data(date=None, cashier=None):
    """
    Vraća sve podatke za dnevni presek stanja.
    date: YYYY-MM-DD (default: danas)
    cashier: username (opcionalno)
    """
    if date is None:
        target_date = timezone.now().date()
    elif isinstance(date, str):
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        target_date = date

    sales_qs = Sale.objects.filter(created_at__date=target_date)
    refunds_qs = Refund.objects.filter(created_at__date=target_date)

    if cashier:
        sales_qs = sales_qs.filter(cashier__username=cashier)
        refunds_qs = refunds_qs.filter(cashier__username=cashier)

    completed = sales_qs.filter(status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED'])
    refunded = sales_qs.filter(status__in=['REFUNDED', 'PARTIALLY_REFUNDED'])

    # Broj izdatih računa
    sale_count = completed.count()
    refund_count = refunds_qs.count()

    # Evidentiran promet
    total_sales = completed.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    total_refunds = refunds_qs.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    net_total = total_sales - total_refunds

    # Prodati artikli
    items_qs = SaleItem.objects.filter(sale__in=completed).values(
        'product__name', 'product__barcode', 'unit_price'
    ).annotate(
        quantity=Sum('quantity'),
        total=Sum(_sale_item_revenue(F('quantity'))),
    ).order_by('-total')

    items_list = []
    for i in items_qs:
        items_list.append({
            'name': i['product__name'],
            'barcode': i['product__barcode'] or '-',
            'price': float(i['unit_price']),
            'quantity': i['quantity'],
            'total': float(i['total'] or 0),
        })

    items_total = sum(i['total'] for i in items_list)

    # Promet po vrstama plaćanja
    payment_qs = completed.values('payment_method').annotate(
        total=Sum('total'), count=Count('id')
    )
    payments = []
    for p in payment_qs:
        payments.append({
            'method': dict(Sale.PAYMENT_CHOICES).get(p['payment_method'], p['payment_method']),
            'total': float(p['total'] or 0),
            'count': p['count'],
        })

    # Avansne uplate (placeholder: ako nemaš model avansa, ostavi prazno)
    advances = []

    # Info o izvještaju
    first = completed.first()
    cashier_name = '-'
    if cashier:
        cashier_name = cashier
    elif first and first.cashier:
        cashier_name = f'{first.cashier.first_name} {first.cashier.last_name}'.strip() or first.cashier.username

    return {
        'report_type': 'DNEVNI PRESEK STANJA',
        'report_id': f'DR-{target_date.strftime("%Y%m%d")}',
        'date': target_date.strftime('%d.%m.%Y'),
        'date_iso': target_date.strftime('%Y-%m-%d'),
        'time': timezone.now().strftime('%H:%M:%S'),
        'cashier': cashier_name,
        'counts': {
            'sale_count': sale_count,
            'refund_count': refund_count,
            'total_count': sale_count + refund_count,
            'advance_sale': 0,
            'advance': 0,
            'advance_refund': 0,
        },
        'revenue': {
            'total_sales': float(total_sales),
            'total_refunds': float(total_refunds),
            'net_total': float(net_total),
        },
        'items': items_list,
        'items_total': items_total,
        'advances': advances,
        'advances_total': sum(a.get('total', 0) for a in advances),
        'payments': payments,
        'payments_total': sum(p['total'] for p in payments),
    }


# ============================================================
#  PERIODIČNI IZVJEŠTAJ PROMETA
# ============================================================
def periodic_report_data(date_from, date_to, cashier=None):
    """
    Vraća sve podatke za periodični izvještaj prometa.
    date_from, date_to: YYYY-MM-DD
    """
    if isinstance(date_from, str):
        df = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        df = date_from
    if isinstance(date_to, str):
        dt = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        dt = date_to

    sales_qs = Sale.objects.filter(created_at__date__gte=df, created_at__date__lte=dt)
    refunds_qs = Refund.objects.filter(created_at__date__gte=df, created_at__date__lte=dt)

    if cashier:
        sales_qs = sales_qs.filter(cashier__username=cashier)
        refunds_qs = refunds_qs.filter(cashier__username=cashier)

    completed = sales_qs.filter(status__in=['COMPLETED', 'PARTIALLY_REFUNDED', 'REFUNDED'])

    sale_count = completed.count()
    refund_count = refunds_qs.count()

    total_sales = completed.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    total_refunds = refunds_qs.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    net_total = total_sales - total_refunds

    items_qs = SaleItem.objects.filter(sale__in=completed).values(
        'product__name', 'product__barcode', 'unit_price'
    ).annotate(
        quantity=Sum('quantity'),
        total=Sum(_sale_item_revenue(F('quantity'))),
    ).order_by('-total')

    items_list = []
    for i in items_qs:
        items_list.append({
            'name': i['product__name'],
            'barcode': i['product__barcode'] or '-',
            'price': float(i['unit_price']),
            'quantity': i['quantity'],
            'total': float(i['total'] or 0),
        })

    items_total = sum(i['total'] for i in items_list)

    payment_qs = completed.values('payment_method').annotate(
        total=Sum('total'), count=Count('id')
    )
    payments = []
    for p in payment_qs:
        payments.append({
            'method': dict(Sale.PAYMENT_CHOICES).get(p['payment_method'], p['payment_method']),
            'total': float(p['total'] or 0),
            'count': p['count'],
        })

    first = completed.first()
    cashier_name = '-'
    if cashier:
        cashier_name = cashier
    elif first and first.cashier:
        cashier_name = f'{first.cashier.first_name} {first.cashier.last_name}'.strip() or first.cashier.username

    return {
        'report_type': 'PERIODIČNI IZVJEŠTAJ PROMETA',
        'report_id': f'PR-{df.strftime("%Y%m%d")}-{dt.strftime("%Y%m%d")}',
        'date_from': df.strftime('%d.%m.%Y'),
        'date_to': dt.strftime('%d.%m.%Y'),
        'date_from_iso': df.strftime('%Y-%m-%d'),
        'date_to_iso': dt.strftime('%Y-%m-%d'),
        'time': timezone.now().strftime('%H:%M:%S'),
        'cashier': cashier_name,
        'counts': {
            'sale_count': sale_count,
            'refund_count': refund_count,
            'total_count': sale_count + refund_count,
        },
        'revenue': {
            'total_sales': float(total_sales),
            'total_refunds': float(total_refunds),
            'net_total': float(net_total),
        },
        'items': items_list,
        'items_total': items_total,
        'advances': [],
        'advances_total': 0,
        'payments': payments,
        'payments_total': sum(p['total'] for p in payments),
    }