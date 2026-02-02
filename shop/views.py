from decimal import Decimal, ROUND_HALF_UP











import stripe





from django.conf import settings





from django.utils import timezone





from django.views.decorators.csrf import csrf_exempt





from django.http import HttpResponse
from django.core.mail import send_mail





from django.shortcuts import render, get_object_or_404, redirect





from django.contrib import messages





from django.http import JsonResponse













from .models import Product, Category, Order, OrderItem, NewsletterSubscriber







from django.views.decorators.http import require_POST























# -------------------------







# PAGES BOUTIQUE







# -------------------------















def home(request):







    categories = Category.objects.all()







    return render(request, "shop/home.html", {"categories": categories})























def product_list(request, gender=None):







    products = Product.objects.all()







    if gender in ("homme", "femme"):







        products = products.filter(gender=gender)















    categories = Category.objects.all()







    return render(request, "shop/product_list.html", {







        "products": products,







        "categories": categories,







        "current_gender": gender,







    })























def product_list_men(request):







    return product_list(request, gender="homme")























def product_list_women(request):







    return product_list(request, gender="femme")























def category_detail(request, slug):







    category = get_object_or_404(Category, slug=slug)







    products = category.products.all()







    categories = Category.objects.all()







    return render(request, "shop/product_list.html", {







        "products": products,







        "categories": categories,







        "current_category": category,







    })























def product_detail(request, slug):







    product = get_object_or_404(Product, slug=slug)







    categories = Category.objects.all()







    return render(request, "shop/product_detail.html", {







        "product": product,







        "categories": categories,







    })























# -------------------------







# PANIER (SESSION)







# -------------------------















def _get_cart(session):







    cart = session.get("cart")







    if cart is None:







        cart = {}







        session["cart"] = cart







    return cart























def add_to_cart(request, product_id):







    if request.method != "POST":







        product = get_object_or_404(Product, id=product_id)







        return redirect("shop:product_detail", slug=product.slug)















    product = get_object_or_404(Product, id=product_id)







    cart = _get_cart(request.session)















    try:





        qty = max(1, int(request.POST.get("quantity", 1)))





    except (TypeError, ValueError):





        qty = 1





    pid = str(product.id)















    if pid in cart:







        cart[pid]["quantity"] += qty







    else:







        cart[pid] = {







            "title": product.title,







            "price": str(product.price),





            "quantity": qty,







            "image": product.image.url if product.image else "",







        }















    request.session.modified = True







    messages.success(request, f"{product.title} a été ajouté au panier.")















    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "shop:cart_detail"







    return redirect(next_url)























@require_POST





def remove_from_cart(request, product_id):





    cart = _get_cart(request.session)







    pid = str(product_id)







    if pid in cart:







        del cart[pid]







        request.session.modified = True







    return redirect("shop:cart_detail")























def cart_detail(request):







    cart = _get_cart(request.session)





    items = []





    total = Decimal("0.00")













    for pid, item in cart.items():







        price = Decimal(str(item["price"]))





        qty = int(item["quantity"])





        line_total = (price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)





        total += line_total





        items.append({





            "product_id": pid,





            "title": item["title"],





            "price": price,





            "quantity": qty,





            "image": item["image"],





            "line_total": line_total,





        })













    return render(request, "shop/cart_detail.html", {







        "items": items,







        "total": total,







    })























# -------------------------







# CHECKOUT (INTERAC OU CARTE)







# -------------------------















def checkout(request):







    cart = request.session.get("cart", {})







    if not cart:







        messages.error(request, "Votre panier est vide.")







        return redirect("shop:cart_detail")















    # Récap







    items = []







    total = Decimal("0.00")





    for pid, item in cart.items():





        price = Decimal(str(item["price"]))





        qty = int(item["quantity"])





        line_total = (price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)





        total += line_total





        items.append({





            "title": item["title"],





            "quantity": qty,





            "price": price,





            "line_total": line_total,





        })













    if request.method == "POST":







        email = request.POST.get("email", "").strip()







        first_name = request.POST.get("first_name", "").strip()







        last_name = request.POST.get("last_name", "").strip()







        address = request.POST.get("address", "").strip()





        city = request.POST.get("city", "").strip()





        phone = request.POST.get("phone", "").strip()















        if not email:







            messages.error(request, "Veuillez entrer un email.")







            return redirect("shop:checkout")















        order = Order.objects.create(





            user=request.user if request.user.is_authenticated else None,





            email=email,





            first_name=first_name,





            last_name=last_name,





            address=address,





            city=city,





            phone=phone,





            status=Order.STATUS_PENDING,





        )













        for pid, item in cart.items():





            product = Product.objects.filter(id=int(pid)).first()





            if not product:





                continue





            OrderItem.objects.create(





                order=order,





                product=product,





                price=Decimal(str(item["price"])),





                quantity=int(item["quantity"]),





            )













        # IMPORTANT: on NE vide PAS le panier ici







        return redirect("shop:payment_page", reference=order.reference)















    return render(request, "shop/checkout.html", {"items": items, "total": total})







































def order_success(request, reference):







    return render(request, "shop/order_success.html", {"reference": reference})























# -------------------------







# SUIVI







# -------------------------















def order_tracking(request):





    order = None





    items = []





    total = Decimal("0.00")













    if request.method == "POST":







        reference = request.POST.get("reference", "").strip()







        email = request.POST.get("email", "").strip()















        if reference and email:







            order = Order.objects.filter(reference=reference, email=email).first()







            if not order:







                messages.error(request, "Commande introuvable. Vérifiez la référence et l'email.")







            else:







                qs = OrderItem.objects.select_related("product").filter(order=order)





                for it in qs:





                    line_total = (Decimal(str(it.price)) * int(it.quantity)).quantize(





                        Decimal("0.01"), rounding=ROUND_HALF_UP





                    )





                    total += line_total





                    items.append({





                        "title": it.product.title,





                        "price": Decimal(str(it.price)),





                        "quantity": int(it.quantity),





                        "line_total": line_total,





                        "image": it.product.image.url if getattr(it.product, "image", None) else "",





                    })













    return render(request, "shop/order_tracking.html", {







        "order": order,







        "items": items,







        "total": total,







    })























# -------------------------







# STRIPE







# -------------------------















def start_payment(request):







    cart = request.session.get("cart", {})







    if not cart:







        messages.error(request, "Votre panier est vide.")







        return redirect("shop:cart_detail")















    if request.method != "POST":







        return redirect("shop:checkout")















    email = request.POST.get("email", "").strip()





    first_name = request.POST.get("first_name", "").strip()





    last_name = request.POST.get("last_name", "").strip()





    address = request.POST.get("address", "").strip()





    city = request.POST.get("city", "").strip()





    phone = request.POST.get("phone", "").strip()













    if not email:







        messages.error(request, "Veuillez entrer un email.")







        return redirect("shop:checkout")















    order = Order.objects.create(





        user=None,





        email=email,





        first_name=first_name,





        last_name=last_name,





        address=address,





        city=city,





        phone=phone,





        status=Order.STATUS_PENDING,





    )













    for pid, item in cart.items():







        product = Product.objects.filter(id=int(pid)).first()







        if not product:







            continue







        OrderItem.objects.create(





            order=order,





            product=product,





            price=Decimal(str(item["price"])),





            quantity=int(item["quantity"]),





        )













    return redirect("shop:payment_page", reference=order.reference)























def payment_page(request, reference):





    order = get_object_or_404(Order, reference=reference)





    items = []





    for it in OrderItem.objects.select_related("product").filter(order=order):





        items.append({





            "title": it.product.title,





            "quantity": it.quantity,





            "price": Decimal(str(it.price)),





            "line_total": (Decimal(str(it.price)) * int(it.quantity)).quantize(





                Decimal("0.01"), rounding=ROUND_HALF_UP





            ),





        })











    return render(request, "shop/payment_page.html", {





        "order": order,





        "items": items,





        "total": Decimal(str(order.total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),





        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,





    })













































def payment_success(request):







    payment_intent_id = request.GET.get("payment_intent", "")















    if not payment_intent_id:







        messages.success(request, "Paiement en cours de confirmation.")







        return redirect("shop:home")















    stripe.api_key = settings.STRIPE_SECRET_KEY





    try:





        intent = stripe.PaymentIntent.retrieve(payment_intent_id)





    except Exception:





        messages.error(request, "Paiement non confirmé.")





        return redirect("shop:home")













    ref = (intent.metadata or {}).get("order_reference")







    if not ref:







        messages.success(request, "Paiement reçu.")







        return redirect("shop:home")















    order = Order.objects.filter(reference=ref).first()





    if order and intent.status == "succeeded":





        if not order.paid or order.status != Order.STATUS_PAID:





            order.paid = True





            order.status = Order.STATUS_PAID





            order.paid_at = timezone.now()





            order.stripe_payment_intent = intent.id





            order.save(update_fields=["paid", "status", "paid_at", "stripe_payment_intent"])













        # panier vidé après paiement OK







        request.session["cart"] = {}







        request.session.modified = True















        return redirect("shop:order_success", reference=order.reference)















    messages.error(request, "Paiement non confirmé.")







    return redirect("shop:payment_page", reference=ref)























def payment_cancel(request):







    return render(request, "shop/payment_cancel.html")























@csrf_exempt







def stripe_webhook(request):





    stripe.api_key = settings.STRIPE_SECRET_KEY











    payload = request.body





    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")











    if not settings.STRIPE_WEBHOOK_SECRET:





        return HttpResponse(status=400)











    try:





        event = stripe.Webhook.construct_event(





            payload=payload,





            sig_header=sig_header,





            secret=settings.STRIPE_WEBHOOK_SECRET,





        )





    except Exception:





        return HttpResponse(status=400)











    if event["type"] == "payment_intent.succeeded":





        intent = event["data"]["object"]





        order_ref = (intent.get("metadata") or {}).get("order_reference")





        if order_ref:





            order = Order.objects.filter(reference=order_ref).first()





            if order and order.status != Order.STATUS_PAID:





                order.status = Order.STATUS_PAID





                order.paid = True





                order.paid_at = timezone.now()





                order.stripe_payment_intent = intent.get("id", "") or ""





                order.save(update_fields=["status", "paid", "paid_at", "stripe_payment_intent"])





    elif event["type"] == "checkout.session.completed":





        session = event["data"]["object"]





        order_ref = session.get("metadata", {}).get("order_reference")





        payment_intent = session.get("payment_intent", "")











        if order_ref:





            order = Order.objects.filter(reference=order_ref).first()





            if order and order.status != Order.STATUS_PAID:





                order.status = Order.STATUS_PAID





                order.paid = True





                order.paid_at = timezone.now()





                order.stripe_payment_intent = payment_intent or ""





                order.save(update_fields=["status", "paid", "paid_at", "stripe_payment_intent"])













    return HttpResponse(status=200)































@require_POST







def newsletter_subscribe(request):







    email = request.POST.get("email", "").strip().lower()







    if not email:







        messages.error(request, "Veuillez entrer un email.")







        return redirect(request.META.get("HTTP_REFERER", "shop:home"))















    obj, created = NewsletterSubscriber.objects.get_or_create(email=email)







    if created:







        messages.success(request, "Merci ! Vous êtes inscrit(e) à la newsletter.")







    else:







        messages.info(request, "Vous êtes déjà inscrit(e).")















    return redirect(request.META.get("HTTP_REFERER", "shop:home"))































@require_POST





def create_payment_intent(request, reference):





    order = get_object_or_404(Order, reference=reference)











    if order.paid or order.status == Order.STATUS_PAID:





        return JsonResponse({"error": "order already paid"}, status=400)











    stripe.api_key = settings.STRIPE_SECRET_KEY





    amount_cents = int((Decimal(str(order.total)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))













    try:







        if order.stripe_payment_intent:







            intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent)







        else:







            intent = stripe.PaymentIntent.create(







                amount=amount_cents,







                currency=settings.STRIPE_CURRENCY,







                automatic_payment_methods={"enabled": True},







                metadata={"order_reference": order.reference},







                receipt_email=order.email,







            )







            order.stripe_payment_intent = intent.id







            order.save(update_fields=["stripe_payment_intent"])















        return JsonResponse({"clientSecret": intent.client_secret})















    except Exception as e:







        return JsonResponse({"error": str(e)}, status=400)























def about(request):







    return render(request, "shop/about.html")















def faq(request):







    return render(request, "shop/faq.html")


def seo_checklist(request):



    return render(request, "shop/seo_checklist.html")






















def indexnow_key(request, key):


    if not settings.INDEXNOW_KEY or key != settings.INDEXNOW_KEY:
        return HttpResponse(status=404)


    return HttpResponse(settings.INDEXNOW_KEY, content_type="text/plain")




def contact(request):

    client_email = settings.EMAIL_HOST_USER or "contact@kinoushstore.com"
    client_phone = "+1 (819) 209-8271"

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        if not all([first_name, last_name, email, message]):
            messages.error(request, "Veuillez remplir tous les champs.")
        else:
            subject = f"Nouveau message - {first_name} {last_name}"
            body = (
                f"Nom: {first_name} {last_name}\n"
                f"Email: {email}\n\n"
                f"Message:\n{message}\n"
            )
            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [client_email],
                    reply_to=[email],
                )
                messages.success(request, "Merci ! Votre message a ete envoye.")
                return redirect("shop:contact")
            except Exception:
                messages.error(
                    request,
                    "Impossible d'envoyer le message pour le moment. Reessayez plus tard.",
                )

    return render(request, "shop/contact.html", {
        "client_email": client_email,
        "client_phone": client_phone,
    })

