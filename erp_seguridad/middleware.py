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

        # EV1DS-44 (CWE-200): Ocultar versión exacta de Python/WSGI en cabecera Server
        response['Server'] = 'SeguridadLTDA-ERP'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # EV1DS-44 (CWE-525): Evitar caché en vistas autenticadas con datos sensibles de RRHH
        if (
                 hasattr(request, 'user')
                 and request.user.is_authenticated
                 and 'Cache-Control' not in response
             ):
                 response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                 response['Pragma'] = 'no-cache'
                 response['Expires'] = '0'

        if 'Cross-Origin-Opener-Policy' not in response:
                response['Cross-Origin-Opener-Policy'] = 'same-origin'
        if 'Cross-Origin-Resource-Policy' not in response:
                response['Cross-Origin-Resource-Policy'] = 'same-origin'



        return response