from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Order, OrderItem, Product

class CartTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat")
        self.product = Product.objects.create(
            category=self.category,
            title="Produit",
            price=Decimal("12.34"),
        )

    def test_add_to_cart_invalid_quantity_defaults_to_one(self):
        url = reverse("shop:add_to_cart", args=[self.product.id])
        self.client.post(url, {"quantity": "abc"})
        session = self.client.session
        self.assertIn(str(self.product.id), session.get("cart", {}))
        self.assertEqual(session["cart"][str(self.product.id)]["quantity"], 1)

    def test_remove_from_cart_requires_post(self):
        url = reverse("shop:remove_from_cart", args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        self.client.post(reverse("shop:add_to_cart", args=[self.product.id]), {"quantity": 1})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(str(self.product.id), self.client.session.get("cart", {}))


class StripeTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat")
        self.product = Product.objects.create(
            category=self.category,
            title="Produit",
            price=Decimal("10.00"),
        )
        self.order = Order.objects.create(email="client@test.com", status=Order.STATUS_PENDING)
        OrderItem.objects.create(order=self.order, product=self.product, price=Decimal("10.00"), quantity=2)

    @patch("shop.views.stripe.PaymentIntent.create")
    def test_create_payment_intent(self, mock_create):
        mock_create.return_value = type(
            "Intent",
            (),
            {"id": "pi_test", "client_secret": "secret_test"},
        )()
        url = reverse("shop:create_payment_intent", args=[self.order.reference])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("clientSecret"), "secret_test")

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test", STRIPE_SECRET_KEY="sk_test")
    @patch("shop.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_marks_order_paid(self, mock_construct):
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test",
                    "metadata": {"order_reference": self.order.reference},
                }
            },
        }
        response = self.client.post(
            reverse("shop:stripe_webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_PAID)

