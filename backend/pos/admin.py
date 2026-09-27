from django.contrib import admin
from .models import (
    Category, Product, Sale, SaleItem, Refund, RefundItem,
    AuditLog, ReceiptSettings,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'barcode', 'category', 'price', 'cost_price', 'stock', 'min_stock', 'active')
    list_filter = ('category', 'active')
    search_fields = ('name', 'barcode')
    list_editable = ('price', 'stock', 'active')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'tax_amount')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'receipt_number', 'cashier', 'total', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('receipt_number',)
    inlines = [SaleItemInline]
    readonly_fields = ('created_at', 'total', 'total_tax', 'receipt_number', 'eo_number')


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0
    readonly_fields = ('sale_item', 'quantity', 'unit_price')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'receipt_number', 'original_sale', 'cashier', 'total', 'created_at')
    inlines = [RefundItemInline]
    search_fields = ('receipt_number',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'target_type', 'target_id', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'target_type')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'details', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReceiptSettings)
class ReceiptSettingsAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'legal_name', 'paper_width', 'updated_at')

    def has_add_permission(self, request):
        return not ReceiptSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False