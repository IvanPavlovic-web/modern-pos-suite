import json
from channels.generic.websocket import AsyncWebsocketConsumer


class InventoryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('inventory', self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'message': 'Spojeni na inventory stream'}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('inventory', self.channel_name)

    async def inventory_update(self, event):
        await self.send(text_data=json.dumps(event['data']))


class SalesConsumer(AsyncWebsocketConsumer):
    """Sinhronizacija otvorenih računa između terminala."""

    async def connect(self):
        await self.channel_layer.group_add('sales', self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'message': 'Spojeni na sales stream'}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('sales', self.channel_name)

    async def sale_update(self, event):
        await self.send(text_data=json.dumps(event['data']))