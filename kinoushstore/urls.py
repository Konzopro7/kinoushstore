from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.templatetags.static import static as static_url
from django.conf import settings
from django.conf.urls.static import static

from shop import views
from shop.admin_2fa import admin_has_permission, admin_login, recovery_codes, setup_totp, verify_totp
from shop.sitemaps import CategorySitemap, ProductSitemap, StaticViewSitemap

admin.site.login = admin_login
admin.site.has_permission = admin_has_permission


sitemaps = {
    "static": StaticViewSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
}

urlpatterns = [
    path("admin/2fa/setup/", setup_totp, name="admin_2fa_setup"),
    path("admin/2fa/verifier/", verify_totp, name="admin_2fa_verify"),
    path("admin/2fa/codes-secours/", recovery_codes, name="admin_2fa_recovery_codes"),
    path("admin/traffic/", views.admin_traffic_dashboard, name="admin_traffic_dashboard"),
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("favicon.ico", RedirectView.as_view(url=static_url("img/favicon.ico"), permanent=True)),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("<str:key>.txt", views.indexnow_key, name="indexnow_key"),
    path("", include("shop.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
