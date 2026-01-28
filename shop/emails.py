from django.conf import settings
from django.core.mail import send_mail

def send_order_email(to_email: str, subject: str, message: str):
    if not to_email:
        return
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=True,
    )

def email_order_received(order):
    subject = f"Kinoush Store — Commande reçue ({order.reference})"
    message = (
        f"Bonjour {order.first_name} {order.last_name},\n\n"
        f"Nous avons bien reçu votre commande.\n"
        f"Référence : {order.reference}\n"
        f"Statut : {order.get_status_display()}\n\n"
        f"Adresse : {order.address}, {order.city}\n\n"
        f"Merci,\nKinoush Store"
    )
    send_order_email(order.email, subject, message)

def email_payment_confirmed(order):
    subject = f"Kinoush Store — Paiement confirmé ({order.reference})"
    message = (
        f"Bonjour {order.first_name} {order.last_name},\n\n"
        f"Votre paiement a été confirmé ✅\n"
        f"Référence : {order.reference}\n\n"
        f"Merci,\nKinoush Store"
    )
    send_order_email(order.email, subject, message)

def email_shipped(order):
    subject = f"Kinoush Store — Commande expédiée ({order.reference})"
    message = (
        f"Bonjour {order.first_name} {order.last_name},\n\n"
        f"Votre commande a été expédiée 📦\n"
        f"Référence : {order.reference}\n\n"
        f"Merci,\nKinoush Store"
    )
    send_order_email(order.email, subject, message)

def email_delivered(order):
    subject = f"Kinoush Store — Commande livrée ({order.reference})"
    message = (
        f"Bonjour {order.first_name} {order.last_name},\n\n"
        f"Votre commande a été livrée ✅\n"
        f"Référence : {order.reference}\n\n"
        f"Merci,\nKinoush Store"
    )
    send_order_email(order.email, subject, message)


