from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Category, Order, OrderItem, Product

class CartTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat")
        self.product = Product.objects.create(
            category=self.category,
            title="Produit",
            price=Decimal("12.34"),
            stock=10,
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
            stock=10,
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

        session = self.client.session
        session["order_references"] = [self.order.reference]
        session.save()
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

    def test_webhook_is_idempotent_for_stock(self):
        self.test_stripe_webhook_marks_order_paid()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        with patch("shop.views.stripe.Webhook.construct_event") as construct_event:
            construct_event.return_value = {
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_test", "metadata": {"order_reference": self.order.reference}}},
            }
            self.client.post(
                reverse("shop:stripe_webhook"), data="{}", content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_test",
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)


class CheckoutSecurityTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Sécurité")
        self.product = Product.objects.create(
            category=category, title="Produit sûr", price=Decimal("25.00"), stock=3
        )

    def test_checkout_uses_database_price_and_remembers_order(self):
        session = self.client.session
        session["cart"] = {
            str(self.product.pk): {"title": self.product.title, "price": "0.01", "quantity": 2}
        }
        session.save()
        response = self.client.post(reverse("shop:start_payment"), {
            "email": "client@example.com", "shipping_fee": "0.00"
        })
        order = Order.objects.get()
        self.assertRedirects(response, reverse("shop:payment_page", args=[order.reference]))
        self.assertEqual(order.items.get().price, Decimal("25.00"))
        self.assertIn(order.reference, self.client.session["order_references"])

    def test_checkout_rejects_quantity_above_stock(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): {"price": "25.00", "quantity": 4}}
        session.save()
        response = self.client.post(reverse("shop:start_payment"), {"email": "client@example.com"})
        self.assertRedirects(response, reverse("shop:checkout"), fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())

    def test_order_payment_page_is_private(self):
        order = Order.objects.create(email="private@example.com")
        response = self.client.get(reverse("shop:payment_page", args=[order.reference]))
        self.assertEqual(response.status_code, 404)


class AccountTests(TestCase):
    def test_signup_creates_and_logs_in_user(self):
        response = self.client.post(reverse("signup"), {
            "username": "cliente", "email": "cliente@example.com",
            "password1": "UnMotDePasse!938", "password2": "UnMotDePasse!938",
        })
        self.assertRedirects(response, reverse("account"))
        self.assertTrue(User.objects.filter(username="cliente").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_account_requires_login(self):
        response = self.client.get(reverse("account"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('account')}")

