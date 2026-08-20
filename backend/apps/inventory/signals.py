from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.inventory.models import ExpenseEntry, InventoryItem, StockMovement
from apps.live import publish_live_event


@receiver(post_save, sender=InventoryItem)
def publish_inventory_item_event(sender, instance: InventoryItem, created: bool, **kwargs) -> None:
    publish_live_event(
        'inventory.item.created' if created else 'inventory.item.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'product_id': instance.product_id,
            'available_quantity': str(instance.available_quantity),
        },
    )


@receiver(post_delete, sender=InventoryItem)
def publish_inventory_item_deleted_event(sender, instance: InventoryItem, **kwargs) -> None:
    publish_live_event(
        'inventory.item.deleted',
        {
            'id': instance.pk,
            'tenant_id': instance.tenant_id,
            'product_id': instance.product_id,
        },
    )


@receiver(post_save, sender=StockMovement)
def publish_stock_movement_event(sender, instance: StockMovement, created: bool, **kwargs) -> None:
    publish_live_event(
        'inventory.movement.created' if created else 'inventory.movement.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'inventory_item_id': instance.inventory_item_id,
            'movement_type': instance.movement_type,
        },
    )


@receiver(post_save, sender=ExpenseEntry)
def publish_expense_entry_event(sender, instance: ExpenseEntry, created: bool, **kwargs) -> None:
    publish_live_event(
        'expense.created' if created else 'expense.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'is_deleted': instance.is_deleted,
        },
    )
