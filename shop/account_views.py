from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AccountEditForm, SignUpForm
from .models import Order


def signup(request):
    if request.user.is_authenticated:
        return redirect("account")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Votre compte a bien été créé.")
        return redirect("account")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def account(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
    return render(request, "accounts/account.html", {"orders": orders})


@login_required
def account_edit(request):
    form = AccountEditForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vos informations ont été mises à jour.")
        return redirect("account")
    return render(request, "accounts/account_edit.html", {"form": form})
