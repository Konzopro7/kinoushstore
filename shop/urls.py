from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    path('', views.home, name='home'),
    path('boutique/', views.product_list, name='product_list'),
    path('boutique/hommes/', views.product_list_men, name='product_list_men'),
    path('boutique/femmes/', views.product_list_women, name='product_list_women'),
    path('categorie/<slug:slug>/', views.category_detail, name='category_detail'),
    path('produit/<slug:slug>/', views.product_detail, name='product_detail'),
    path('panier/', views.cart_detail, name='cart_detail'),
    path('panier/ajouter/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('panier/supprimer/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('commande/', views.checkout, name='checkout'),
    path('commande/merci/<str:reference>/', views.order_success, name='order_success'),
    path('suivi-commande/', views.order_tracking, name='order_tracking'),

    path("paiement/demarrer/", views.start_payment, name="start_payment"),
    path("paiement/succes/", views.payment_success, name="payment_success"),
    path("paiement/annule/", views.payment_cancel, name="payment_cancel"),
    path("paiement/<str:reference>/intent/", views.create_payment_intent, name="create_payment_intent"),
    path("paiement/<str:reference>/", views.payment_page, name="payment_page"),

    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("newsletter/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("contact/", views.contact, name="contact"),
    path("a-propos/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("seo-checklist/", views.seo_checklist, name="seo_checklist"),

]
















