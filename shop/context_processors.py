from .models import Category

def categories_global(request):
    return {'categories_global': Category.objects.all()}

def cart_item_count(request):
    cart = request.session.get('cart', {})

    count = 0
    for item in cart.values():
        if isinstance(item, dict):
            count += int(item.get('quantity', 0))
        else:
            count += int(item)

    return {'cart_item_count': count}

