from rest_framework.throttling import SimpleRateThrottle


class TokenLoginThrottle(SimpleRateThrottle):
    scope = "token_login"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class TokenSubmitThrottle(SimpleRateThrottle):
    scope = "token_submit"

    def get_cache_key(self, request, view):
        return self.get_ident(request)
