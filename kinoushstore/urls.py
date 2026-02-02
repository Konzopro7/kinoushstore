from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.templatetags.static import static as static_url
from django.conf import settings
from django.conf.urls.static import static

from shop import views
from shop.sitemaps import CategorySitemap, ProductSitemap, StaticViewSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
}

urlpatterns = [
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
