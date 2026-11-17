class ContentSecurityPolicyMiddleware:
    """
    EV1DS-42 (CWE-693 / OWASP ZAP Plugin 10038):
    Inyecta la cabecera Content-Security-Policy y Referrer-Policy en todas
    las respuestas HTTP para mitigar XSS y Clickjacking (frame-ancestors).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if 'Content-Security-Policy' not in response:
            csp_directivas = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/ https://fonts.googleapis.com/",
                "font-src 'self' data: https://cdn.jsdelivr.net/ https://fonts.gstatic.com/",
                "img-src 'self' data: blob:",
                "connect-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
            response['Content-Security-Policy'] = "; ".join(csp_directivas)

        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = 'same-origin'

        if 'Permissions-Policy' not in response:
                    response['Permissions-Policy'] = (
                        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
                    )

        return response