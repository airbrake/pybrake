# -*- coding: utf-8 -*-
"""Error controller"""
from tg import request, expose
from weather_fullstack.lib.base import BaseController

__all__ = ['ErrorController']


class ErrorController(BaseController):
    """
    Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.

    """

    @expose('weather_fullstack.templates.error')
    def document(self, *args, **kwargs):
        """Render the error document"""
        resp = request.environ.get('tg.original_response')
        try:
            # tg.abort exposes the message as .detail in response
            message = resp.detail
        except:
            message = None

        if not message:
            message = ("We're sorry but we weren't able to process "
                       " this request.")

        values = dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                      code=request.params.get('code', resp.status_int if resp else 400),
                      message=request.params.get('message', message))
        return values
