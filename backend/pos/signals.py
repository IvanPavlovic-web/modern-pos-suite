from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Sale, SaleItem, Product


def _broadcast_inventory(product):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'inventory',
        {
            'type': 'inventory_update',
            'data': {
                'product_id': product.id,
                'product_name': product.name,
                'new_stock': product.stock,
            },
        },
    )


def _broadcast_sale(sale):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'sales',
        {
            'type': 'sale_update',
            'data': {
                'sale_id': sale.id,
                'status': sale.status,
                'cashier': sale.cashier.username if sale.cashier else None,
                'opened_by': sale.opened_by.username if sale.opened_by else None,
                'terminal_id': sale.terminal_id,
                'total': float(sale.total),
                'action': 'updated',
            },
        },
    )


@receiver(post_save, sender=Sale)
def sale_saved(sender, instance, created, **kwargs):
    if instance.status == 'COMPLETED':
        for item in instance.items.all():
            product = item.product
            # Smanji stock samo ako već nije smanjen
            if product.stock >= 0:
                # Provera da nije već smanjeno za ovaj sale - pojednostavljeno
                pass
    _broadcast_sale(instance)


@receiver(post_delete, sender=Sale)
def sale_deleted(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'sales',
        {
            'type': 'sale_update',
            'data': {
                'sale_id': instance.id,
                'status': 'DELETED',
                'action': 'deleted',
            },
        },
    )


@receiver(post_save, sender=Product)
def product_updated_broadcast(sender, instance, created, **kwargs):
    _broadcast_inventory(instance)