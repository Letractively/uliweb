from uliweb.middleware import Middleware

class AuthMiddle(Middleware):
    def process_request(self, request):
        from uliweb.contrib.auth import get_user
        request.user = get_user(request)
