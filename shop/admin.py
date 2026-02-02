from django.contrib import admin, messages
from django.utils import timezone

from .emails import email_delivered, email_shipped
from .models import Category, Order, OrderItem, NewsletterSubscriber, Product, SiteVisit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "show_in_menu")
    list_filter = ("show_in_menu",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "stock", "gender", "is_featured")
    list_filter = ("gender", "is_featured", "category")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("category",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "email", "status", "created_at", "paid_at", "shipping_fee")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "email")
    inlines = [OrderItemInline]

    readonly_fields = (
        "reference",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
        "paid_at",
        "shipping_fee",
    )
    actions = ["mark_shipped", "mark_delivered"]

    def mark_shipped(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_SHIPPED
            order.shipped_at = timezone.now()
            order.save(update_fields=["status", "shipped_at"])
            if order.email:
                email_shipped(order)
        self.message_user(request, "Commandes marquées comme expédiées + emails envoyés ✅")

    mark_shipped.short_description = "Marquer comme expédiée (envoyer email)"

    def mark_delivered(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_DELIVERED
            order.delivered_at = timezone.now()
            order.save(update_fields=["status", "delivered_at"])
            if order.email:
                email_delivered(order)
        self.message_user(request, "Commandes marquées comme livrées + emails envoyés ✅")

    mark_delivered.short_description = "Marquer comme livrée (envoyer email)"

    def has_change_permission(self, request, obj=None):
        # tu peux changer l'adresse etc. (admin), mais on protège le paiement
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            # On empêche l'admin de passer "paid" manuellement (protection)
            ro.append("status")
        return ro

    def response_change(self, request, obj):
        """
        Gère nos boutons custom dans la page admin (change form)
        """
        if "_mark_shipped" in request.POST:
            if obj.status == Order.STATUS_PAID:
                obj.status = Order.STATUS_SHIPPED
                obj.save(update_fields=["status"])
                self.message_user(request, "✅ Commande marquée comme EXPÉDIÉE.", level=messages.SUCCESS)
            else:
                self.message_user(
                    request,
                    "⚠️ La commande doit être PAYÉE avant d'être expédiée.",
                    level=messages.WARNING,
                )
            return super().response_change(request, obj)

        if "_mark_delivered" in request.POST:
            if obj.status in (Order.STATUS_SHIPPED, Order.STATUS_PAID):
                obj.status = Order.STATUS_DELIVERED
                obj.save(update_fields=["status"])
                self.message_user(request, "✅ Commande marquée comme LIVRÉE.", level=messages.SUCCESS)
            else:
                self.message_user(
                    request,
                    "⚠️ La commande doit être EXPÉDIÉE (ou PAYÉE) avant d'être livrée.",
                    level=messages.WARNING,
                )
            return super().response_change(request, obj)

        return super().response_change(request, obj)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    search_fields = ("email",)
    list_filter = ("is_active", "created_at")


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ("path", "created_at", "status_code", "ip_address", "user")
    list_filter = ("status_code", "created_at")
    search_fields = ("path", "referrer", "ip_address", "user_agent")
    readonly_fields = (
        "path",
        "method",
        "status_code",
        "referrer",
        "user_agent",
        "ip_address",
        "user",
        "created_at",
    )
    ordering = ("-created_at",)
    list_select_related = ("user",)
