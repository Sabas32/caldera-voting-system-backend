from rest_framework.response import Response


def success_response(data=None, message: str = "OK", status_code: int = 200):
    return Response({"success": True, "message": message, "data": data}, status=status_code)


def error_response(message: str, details=None, status_code: int = 400):
    return Response(
        {
            "success": False,
            "message": message,
            "details": details,
            "status_code": status_code,
        },
        status=status_code,
    )
