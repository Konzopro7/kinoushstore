import logging

from .models import SiteVisit

logger = logging.getLogger(__name__)


class SiteVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if self._should_log(request, response):
                SiteVisit.objects.create(
                    path=(request.path or "")[:255],
                    method=(request.method or "GET")[:10],
                    status_code=response.status_code,
                    referrer=self._trim(request.META.get("HTTP_REFERER", ""), 500),
                    user_agent=self._trim(request.META.get("HTTP_USER_AGENT", ""), 500),
                    ip_address=self._get_ip(request),
                    user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
                )
        except Exception:
            logger.exception("Site visit logging failed.")
        return response

    def _should_log(self, request, response):
        if request.method not in ("GET", "HEAD"):
            return False
        path = request.path or ""
        if path in ("/favicon.ico", "/robots.txt"):
            return False
        if path.startswith(("/admin/", "/static/", "/media/")):
            return False
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return False
        if response.status_code >= 400:
            return False
        return True

    @staticmethod
    def _trim(value, max_len):
        if not value:
            return ""
        return value[:max_len]

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip() or None
        return request.META.get("REMOTE_ADDR") or None
