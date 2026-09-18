from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Order, OrderItem, Product, ProductVariant


@transaction.atomic
def create_order_from_cart(*, cart, user, customer, shipping_fee):
    """Create an order from authoritative product data, never session prices."""
    if not cart:
        raise ValidationError("Votre panier est vide.")

    try:
        product_ids = [
            int(item.get("product_id") or str(item_key).split(":", 1)[0])
            for item_key, item in cart.items()
        ]
    except (TypeError, ValueError, AttributeError):
        raise ValidationError("Le panier contient un produit invalide.")

    products = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(pk__in=product_ids)
    }
    if len(products) != len(set(product_ids)):
        raise ValidationError("Un produit du panier n’est plus disponible.")

    variant_ids = []
    for cart_item in cart.values():
        try:
            variant_id = cart_item.get("variant_id")
            if variant_id not in (None, ""):
                variant_ids.append(int(variant_id))
        except (AttributeError, TypeError, ValueError):
            raise ValidationError("Le panier contient un modèle invalide.")
    variants = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update().filter(
            pk__in=variant_ids, is_active=True
        )
    }
    if len(variants) != len(set(variant_ids)):
        raise ValidationError("Un modèle sélectionné n’est plus disponible.")

    lines = []
    for item_key, cart_item in cart.items():
        try:
            product_id = int(cart_item.get("product_id") or str(item_key).split(":", 1)[0])
        except (AttributeError, TypeError, ValueError):
            raise ValidationError("Le panier contient un produit invalide.")
        product = products[product_id]
        try:
            quantity = int(cart_item.get("quantity", 1))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError(f"Quantité invalide pour {product.title}.")
        if quantity < 1:
            raise ValidationError(f"Quantité invalide pour {product.title}.")
        variant_id = cart_item.get("variant_id")
        variant = variants.get(int(variant_id)) if variant_id not in (None, "") else None
        if variant and variant.product_id != product.pk:
            raise ValidationError("Le modèle sélectionné ne correspond pas à ce produit.")
        if product.variants.filter(is_active=True).exists() and not variant:
            raise ValidationError(f"Choisissez un modèle pour {product.title}.")
        available_stock = variant.stock if variant else product.stock
        if quantity > available_stock:
            label = f"{product.title} — {variant.name}" if variant else product.title
            raise ValidationError(
                f"Stock insuffisant pour {label} (disponible : {available_stock})."
            )
        price = variant.price if variant else product.price
        lines.append((product, variant, quantity, price))

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
            OrderItem(
                order=order,
                product=product,
                variant=variant,
                variant_label=variant.name if variant else "",
                price=price,
                quantity=quantity,
            )
            for product, variant, quantity, price in lines
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
        .prefetch_related("items__product", "items__variant")
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
    variant_ids = [item.variant_id for item in items if item.variant_id]
    variants = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
    }
    for item in items:
        if item.variant_id:
            variant = variants.get(item.variant_id)
            if not variant or variant.stock < item.quantity:
                raise ValidationError(f"Stock insuffisant pour {item.product.title} — {item.variant_label}.")
        else:
            product = products[item.product_id]
            if product.stock < item.quantity:
                raise ValidationError(f"Stock insuffisant pour {product.title}.")
    for item in items:
        if item.variant_id:
            variant = variants[item.variant_id]
            variant.stock -= item.quantity
            variant.save(update_fields=["stock"])
        else:
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
