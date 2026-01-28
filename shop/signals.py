from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import (
    email_delivered,
    email_order_received,
    email_payment_confirmed,
    email_shipped,
)
from .models import Order


@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance: Order, **kwargs):
    if instance.pk:
        old = Order.objects.filter(pk=instance.pk).only("status").first()
        instance._old_status = old.status if old else None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created, **kwargs):
    if created and instance.status == Order.STATUS_PENDING:
        email_order_received(instance)
        return

    old_status = getattr(instance, "_old_status", None)
    new_status = instance.status
    if old_status == new_status:
        return

    if new_status == Order.STATUS_PAID:
        email_payment_confirmed(instance)
    elif new_status == Order.STATUS_SHIPPED:
        email_shipped(instance)
    elif new_status == Order.STATUS_DELIVERED:
        email_delivered(instance)

