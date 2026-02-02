from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    show_in_menu = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:category_detail", args=[self.slug])


class Product(models.Model):
    GENDER_CHOICES = (
        ("homme", "Homme"),
        ("femme", "Femmes"),
        ("unisex", "Unisexe"),
    )

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    stock = models.PositiveIntegerField(default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="unisex")
    payment_method = models.CharField(max_length=20, default="card")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:product_detail", args=[self.slug])


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    paid = models.BooleanField(default=False)

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reference = models.CharField(max_length=20, unique=True, blank=True)

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "En attente de paiement"),
        (STATUS_PAID, "Payée"),
        (STATUS_SHIPPED, "Expédiée"),
        (STATUS_DELIVERED, "Livrée"),
        (STATUS_CANCELED, "Annulée"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    stripe_session_id = models.CharField(max_length=255, blank=True, default="")
    stripe_payment_intent = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.reference or f"Commande #{self.id}"

    @property
    def total(self):
        items_total = sum((item.total for item in self.items.all()), Decimal("0.00"))
        return items_total + (self.shipping_fee or Decimal("0.00"))

    def save(self, *args, **kwargs):
        """Génère une référence du type KNS-2025-0001 au premier enregistrement."""
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.reference:
            year = timezone.now().year
            self.reference = f"KNS-{year}-{self.id:04d}"
            super().save(update_fields=["reference"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total(self):
        return self.price * self.quantity


class SiteVisit(models.Model):
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10, default="GET")
    status_code = models.PositiveSmallIntegerField(default=200)
    referrer = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["path"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.path} ({self.created_at:%Y-%m-%d %H:%M})"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email
