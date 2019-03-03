import inspect

from aiohttp import web

from .notifier import Notifier


def create_airbrake_middleware(overrides=None):
    async def factory(app, handler):
        async def middleware(request):
            try:
                response = await handler(request)
                await override_error_template(overrides, request, response.status)
                return response

            except web.HTTPException as ex:
                handle_exception(app, ex, request)
                await override_error_template(overrides, request, ex.status)
                raise

            except Exception as ex:
                handle_exception(app, ex, request)
                await override_error_template(overrides, request, 500)
                raise

        return middleware

    return factory


def handle_exception(app, ex, request):
    init_pybrake(app)
    airbrake_send_notification(ex, app["pybrake"], request)


def init_pybrake(app):
    if "pybrake" not in app:
        app["pybrake"] = Notifier(**app["airbrake_config"])


async def override_error_template(overrides, request, status_code):
    if overrides:
        override = overrides.get(status_code)
        if override:
            return await override(request)


def airbrake_send_notification(ex, notifier, request):
    notice = notifier.build_notice(ex)
    notice["context"].update(additional_context(request))
    notice["params"].update(get_headers(request))
    notifier.send_notice(notice)


def additional_context(request):
    return dict(
        userAgent=get_user_agent(request),
        userAddr=attr_from_request(request, "remote"),
        httpMethod=attr_from_request(request, "method"),
        url=attr_from_request(request, "url"),
    )


def get_user_agent(request):
    headers = get_headers(request)
    return headers.get("User-Agent") if headers else None


def get_headers(request):
    headers = attr_from_request(request, "headers")
    return dict(headers=headers) if headers else {}


def attr_from_request(request, attr_name):
    if hasattr(request, attr_name):
        attr = getattr(request, attr_name)
        return attr() if inspect.ismethod(attr) else attr
    return None
