from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(response.data, dict):
        detail = response.data.get('detail')
        if not detail:
            for value in response.data.values():
                if isinstance(value, list) and value:
                    detail = value[0]
                    break
                if isinstance(value, str) and value.strip():
                    detail = value.strip()
                    break
        if detail:
            response.data['detail'] = detail
        response.data['status_code'] = response.status_code
    else:
        response.data = {
            'detail': str(response.data),
            'status_code': response.status_code,
        }
    return response
