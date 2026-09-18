from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail

from .models import Category, Order, OrderItem, Product, ProductVariant

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

    def test_variant_is_stored_as_a_distinct_cart_line(self):
        variant = ProductVariant.objects.create(
            product=self.product, name="Noir · 100 ml", stock=4, price_adjustment=Decimal("5.00")
        )
        response = self.client.post(
            reverse("shop:add_to_cart", args=[self.product.id]), {"variant_id": variant.id, "quantity": 2}
        )
        self.assertRedirects(response, reverse("shop:cart_detail"))
        item = self.client.session["cart"][f"{self.product.id}:{variant.id}"]
        self.assertEqual(item["variant_name"], "Noir · 100 ml")
        self.assertEqual(item["price"], "17.34")

    def test_cart_removes_stale_product_without_an_error_page(self):
        session = self.client.session
        session["cart"] = {"999999": {"product_id": 999999, "quantity": 1, "price": "12.00"}}
        session.save()
        response = self.client.get(reverse("shop:cart_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panier vide")
        self.assertEqual(self.client.session["cart"], {})


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

    @override_settings(
        DEBUG=False,
        STRIPE_PAYMENT_ENABLED=False,
        STRIPE_LIVE_MODE=False,
        STRIPE_PUBLISHABLE_KEY="pk_test_example",
        STRIPE_SECRET_KEY="sk_test_example",
    )
    def test_test_keys_are_disabled_in_production(self):
        session = self.client.session
        session["order_references"] = [self.order.reference]
        session.save()
        response = self.client.post(
            reverse("shop:create_payment_intent", args=[self.order.reference])
        )
        self.assertEqual(response.status_code, 503)

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


class AdminTwoFactorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "Admin!Password938")

    def test_admin_requires_totp_enrollment_before_login(self):
        response = self.client.post("/admin/login/", {"username": "admin", "password": "Admin!Password938"})
        self.assertRedirects(response, reverse("admin_2fa_setup"))

        from .admin_2fa import _decrypt, _totp
        from .models import AdminTwoFactorDevice

        device = AdminTwoFactorDevice.objects.get(user=self.admin)
        response = self.client.post(reverse("admin_2fa_setup"), {"code": _totp(_decrypt(device.encrypted_secret))})
        self.assertRedirects(response, reverse("admin_2fa_recovery_codes"))
        response = self.client.post(reverse("admin_2fa_recovery_codes"))
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)

    def test_admin_session_without_totp_marker_is_denied(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, "/admin/login/?next=/admin/")

    def test_public_customer_login_routes_are_not_exposed(self):
        self.assertEqual(self.client.get("/connexion/").status_code, 404)
        self.assertEqual(self.client.get("/inscription/").status_code, 404)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_EMAIL="contact@example.com",
)
class ContactTests(TestCase):
    def test_contact_sends_valid_message(self):
        response = self.client.post(reverse("shop:contact"), {
            "first_name": "Awa",
            "last_name": "Diallo",
            "email": "awa@example.com",
            "message": "Bonjour, je souhaite obtenir des informations.",
        })
        self.assertRedirects(response, reverse("shop:contact"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to, ["awa@example.com"])

    def test_contact_rejects_invalid_email(self):
        response = self.client.post(reverse("shop:contact"), {
            "first_name": "Awa",
            "last_name": "Diallo",
            "email": "adresse-invalide",
            "message": "Ceci est un message suffisamment long.",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox, [])
        self.assertContains(response, "adresse e-mail valide")

    def test_contact_honeypot_silently_rejects_spam(self):
        response = self.client.post(reverse("shop:contact"), {
            "first_name": "Robot",
            "last_name": "Spam",
            "email": "spam@example.com",
            "message": "Ceci est un message automatisé indésirable.",
            "website": "https://spam.example",
        })
        self.assertRedirects(response, reverse("shop:contact"))
        self.assertEqual(mail.outbox, [])

