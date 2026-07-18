from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Order, OrderItem, Product


@transaction.atomic
def create_order_from_cart(*, cart, user, customer, shipping_fee):
    """Create an order from authoritative product data, never session prices."""
    if not cart:
        raise ValidationError("Votre panier est vide.")

    try:
        product_ids = [int(product_id) for product_id in cart]
    except (TypeError, ValueError):
        raise ValidationError("Le panier contient un produit invalide.")

    products = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(pk__in=product_ids)
    }
    if len(products) != len(set(product_ids)):
        raise ValidationError("Un produit du panier n’est plus disponible.")

    lines = []
    for product_id, cart_item in cart.items():
        product = products[int(product_id)]
        try:
            quantity = int(cart_item.get("quantity", 1))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError(f"Quantité invalide pour {product.title}.")
        if quantity < 1:
            raise ValidationError(f"Quantité invalide pour {product.title}.")
        if quantity > product.stock:
            raise ValidationError(
                f"Stock insuffisant pour {product.title} (disponible : {product.stock})."
            )
        lines.append((product, quantity))

    order = Order.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        email=customer["email"],
        first_name=customer.get("first_name", ""),
        last_name=customer.get("last_name", ""),
        address=customer.get("address", ""),
        city=customer.get("city", ""),
        phone=customer.get("phone", ""),
        shipping_fee=shipping_fee,
        status=Order.STATUS_PENDING,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(order=order, product=product, price=product.price, quantity=quantity)
            for product, quantity in lines
        ]
    )
    return order


def authorize_order(request, order):
    if request.user.is_authenticated and order.user_id == request.user.id:
        return True
    return order.reference in request.session.get("order_references", [])


def remember_order(request, order):
    references = request.session.get("order_references", [])
    if order.reference not in references:
        request.session["order_references"] = [*references[-19:], order.reference]
        request.session.modified = True


@transaction.atomic
def mark_order_paid(*, order_reference, payment_intent=""):
    """Apply a Stripe success idempotently and decrement stock once."""
    order = (
        Order.objects.select_for_update()
        .prefetch_related("items__product")
        .filter(reference=order_reference)
        .first()
    )
    if not order:
        return None
    if order.paid:
        return order

    items = list(order.items.all())
    products = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(
            pk__in=[item.product_id for item in items]
        )
    }
    for item in items:
        product = products[item.product_id]
        if product.stock < item.quantity:
            raise ValidationError(f"Stock insuffisant pour {product.title}.")
    for item in items:
        product = products[item.product_id]
        product.stock -= item.quantity
        product.save(update_fields=["stock"])

    from django.utils import timezone

    order.paid = True
    order.status = Order.STATUS_PAID
    order.paid_at = timezone.now()
    order.stripe_payment_intent = payment_intent or order.stripe_payment_intent
    order.save(update_fields=["paid", "status", "paid_at", "stripe_payment_intent"])
    return order
