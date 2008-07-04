from uliweb.middlewares import Middleware

class AuthMiddle(Middleware):
    def process_request(self, request):
        from uliweb.builtins.auth import get_user
        request.user = get_user(request)
        print request.user
