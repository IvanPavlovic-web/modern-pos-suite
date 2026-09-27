from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('17.00'))
    stock = models.IntegerField(default=0)
    min_stock = models.IntegerField(default=5)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    unit = models.CharField(max_length=10, default='kom')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.price} KM)'

    @property
    def price_with_tax(self):
        return round(self.price * (Decimal('1') + self.tax_rate / Decimal('100')), 2)

    @property
    def final_price(self):
        discount = self.price * self.discount_percent / Decimal('100')
        return round(self.price - discount, 2)

    @property
    def margin(self):
        return round(self.price - self.cost_price, 2)


class Sale(models.Model):
    STATUS_CHOICES = [
        ('COMPLETED', 'Completed'),
        ('REFUNDED', 'Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
        ('PENDING', 'Pending'),
        ('HELD', 'Held'),
    ]
    PAYMENT_CHOICES = [
        ('CASH', 'Gotovina'),
        ('CARD', 'Kartica'),
        ('SPLIT', 'Split'),
    ]
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')
    opened_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='open_sales')
    terminal_id = models.CharField(max_length=50, blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='CASH')
    payment_splits = models.JSONField(null=True, blank=True, default=None)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='COMPLETED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    receipt_number = models.CharField(max_length=30, blank=True)
    eo_number = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Sale #{self.id} | {self.total} KM | {self.status}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_number and self.status == 'COMPLETED':
            self.receipt_number = f'R-{self.created_at.strftime("%Y%m%d")}-{self.id:05d}'
            Sale.objects.filter(pk=self.pk).update(receipt_number=self.receipt_number)
        if not self.eo_number and self.status == 'COMPLETED':
            self.eo_number = f'{self.id:05d}'
            Sale.objects.filter(pk=self.pk).update(eo_number=self.eo_number)

    def recalculate(self):
        items = self.items.all()
        subtotal = sum((i.line_total for i in items), Decimal('0.00'))
        discount = (subtotal * self.discount_percent / Decimal('100')).quantize(Decimal('0.01'))
        self.discount_amount = discount
        self.total = subtotal - discount
        self.total_tax = sum((i.tax_amount for i in items), Decimal('0.00'))
        self.save(update_fields=['total', 'total_tax', 'discount_amount', 'updated_at'])


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    item_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    refunded_quantity = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    @property
    def line_total(self):
        base = self.unit_price * self.quantity
        item_discount = (base * self.item_discount_percent / Decimal('100')).quantize(Decimal('0.01'))
        return base - item_discount

    @property
    def available_for_refund(self):
        return self.quantity - self.refunded_quantity


class Refund(models.Model):
    original_sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='refunds')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='refunds')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    reason = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=10, choices=[('CASH', 'Gotovina'), ('CARD', 'Kartica')], default='CASH')
    receipt_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Refund #{self.id} za Sale #{self.original_sale_id}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_number:
            self.receipt_number = f'S-{self.created_at.strftime("%Y%m%d")}-{self.id:05d}'
            Refund.objects.filter(pk=self.pk).update(receipt_number=self.receipt_number)


class RefundItem(models.Model):
    refund = models.ForeignKey(Refund, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.sale_item.product.name} x{self.quantity}'

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('SALE_CREATE', 'Kreiranje prodaje'),
        ('SALE_CHECKOUT', 'Završetak prodaje'),
        ('SALE_CANCEL', 'Otkazivanje prodaje'),
        ('SALE_REFUND', 'Refundacija'),
        ('SALE_DISCOUNT', 'Popust na računu'),
        ('PRODUCT_CREATE', 'Kreiranje proizvoda'),
        ('PRODUCT_UPDATE', 'Izmjena proizvoda'),
        ('PRODUCT_DELETE', 'Brisanje proizvoda'),
        ('PRICE_CHANGE', 'Izmjena cijene'),
        ('STOCK_CHANGE', 'Izmjena stanja'),
        ('SETTINGS_CHANGE', 'Izmjena podešavanja'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f'{self.created_at} | {self.user} | {self.action}'


class ReceiptSettings(models.Model):
    """Singleton model: samo jedan red u tabeli (pk=1)."""
    PAPER_CHOICES = [(58, '58mm'), (80, '80mm')]

    business_name = models.CharField(max_length=200, default='SUR')
    legal_name = models.CharField(max_length=200, default='SIRIUS2010.doo Banja Luka')
    address = models.CharField(max_length=200, default='Prvog Krajiškog Korpusa 18')
    city = models.CharField(max_length=100, default='Banja Luka')
    postal_code = models.CharField(max_length=20, default='78000')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    jib = models.CharField(max_length=20, blank=True, default='', verbose_name='JIB')
    pib = models.CharField(max_length=20, blank=True, default='', verbose_name='PIB')
    mb = models.CharField(max_length=20, blank=True, default='', verbose_name='MB')
    business_unit_id = models.CharField(max_length=30, blank=True, default='4402692070009')
    pos_id = models.CharField(max_length=50, blank=True, default='NOT APPLICABLE')
    store_name = models.CharField(max_length=200, blank=True, default='SIRIUS2010 doo Banja Luka')

    receipt_type = models.CharField(max_length=100, default='MALOPRODAJNI FISKALNI RAČUN')
    header_text = models.TextField(blank=True, default='')
    footer_text = models.TextField(blank=True, default='HVALA NA POSJETI !\nPOS')

    paper_width = models.IntegerField(choices=PAPER_CHOICES, default=80)
    font_family = models.CharField(max_length=100, default='Share Tech Mono')
    font_size = models.IntegerField(default=11)
    line_height = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.35'))
    letter_spacing = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.40'))

    show_logo = models.BooleanField(default=False)
    show_address = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_jib = models.BooleanField(default=True)
    show_pib = models.BooleanField(default=True)
    show_operator = models.BooleanField(default=True)
    show_payment_method = models.BooleanField(default=True)
    show_tax = models.BooleanField(default=True)
    show_qr = models.BooleanField(default=False)
    show_barcode = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Receipt Settings'
        verbose_name_plural = 'Receipt Settings'

    def __str__(self):
        return f'Receipt Settings ({self.business_name})'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj