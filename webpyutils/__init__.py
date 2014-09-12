'''utilities to make web.py restful api server'''
import sys
import logging
import logging.handlers
import web
import time
import os
import json
from web.webapi import HTTPError
from functools import partial, wraps

#json encode that supports datetime objects
json_dumps = partial(json.dumps, default=lambda x: {'__isodatetime__' : x.isoformat()} if hasattr(x, 'isoformat') else str(x))

rest_status_codes = {
    100 : '100 Continue',
    101 : '101 Switching Protocols',

    200 : '200 OK',
    201 : '201 Created',
    202 : '202 Accepted',
    203 : '203 Non-Authoritative Information',
    204 : '204 No Content',
    205 : '205 Reset Content',
    206 : '206 Partial Content',
    207 : '207 Multi-Status',

    300 : '300 Multiple Choices',
    301 : '301 Moved Permanently',
    302 : '302 Found',
    303 : '303 See Other',
    304 : '304 Not Modified',
    305 : '305 Use Proxy',
    307 : '307 Temporary Redirect',

    400 : '400 Bad Request',
    401 : '401 Unauthorized',
    402 : '402 Payment Required',
    403 : '403 Forbidden',
    404 : '404 Not Found',
    405 : '405 Method Not Allowed',
    406 : '406 Not Acceptable',
    407 : '407 Proxy Authentication',
    408 : '408 Request Timeout',
    409 : '409 Conflict',
    410 : '410 Gone',
    411 : '411 Length Required',
    412 : '412 Precondition Failed',
    413 : '413 Request Entity Too Large',
    414 : '414 Request-URI Too Long',
    415 : '415 Unsupported Media Type',
    416 : '416 Requested Range Not Satisfiable',
    417 : '417 Expectation Failed',
    422 : '422 Unprocessable Entity',
    423 : '423 Locked',
    424 : '424 Failed Dependency',

    500 : '500 Internal Server Error',
    501 : '501 Not Implemented',
    502 : '502 Bad Gateway',
    503 : '503 Service Unavailable',
    504 : '504 Gateway Timeout',
    505 : '505 HTTP Version Not Supported',
    507 : '507 Insufficient Storage',
}

def api(func):
    '''decorator to format output as web.py json responses'''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        #JSONP callback function
        callback = web.input().get('callback')
        data = func(self, *args, **kwargs)
        if 'code' not in data:
            data['code'] = 200
        if 'status' not in data:
            #if no status is given we set it by assuming return code < 400 ok
            if data['code'] < 400:
                data['status'] = 'ok'
            else:
                data['status'] = 'error'
        web.ctx['status'] = rest_status_codes.get(data['code'], str(data['code']))
        #support callback to support JSONP by setting the content-type
        if callback:
            web.header('Content-Type', 'application/javascript')
            return '%s(%s);' % (callback, json_dumps(data))
        web.header('Content-Type', 'application/json')
        return json_dumps(data)
    return wrapper

class APIServer(object):
    '''wraps, monkey patches web.py's dev webserver for production use'''
    def __init__(self, app, server_name='apiserver', log_path='./apiserver.log', log_level=logging.DEBUG):
        '''setup required params'''
        self._app = app
        self._server_name = server_name
        self._log_path = log_path
        self._log_level = log_level

        #make error message output in json
        self._restify_error_pages()
        #setup logging error level
        self._setup_logging()

    def _restify_error_pages(self):
        '''setup web.py's default error responses to be JSON'''
        #reimplement error states to return json data
        def build_error(error, message):
            '''build json error blob and content type'''
            callback = web.input().get('callback')
            try:
                code = int(error.partition(' ')[0])
            except:
                code = 500
            if callback:
                content = {'Content-Type' : 'application/javascript'}
                data = '%s(%s);' % (callback, json_dumps({'status' : 'error', 'message' : message, 'code' : code}))
            else:
                content = {'Content-Type' : 'application/json'}
                data = json_dumps({'status' : 'error', 'message' : message, 'code' : code})

            return error, content, data

        def notfound():
            return HTTPError(*build_error('404 Not Found', 'This page is not found'))

        def internalerror():
            return HTTPError(*build_error('500 Internal Server Error', 'An unexpected error occured'))

        def nomethod(cls):
            return HTTPError(*build_error('405 Method Not Allowed', 'This HTTP Method is not supported on %s' % (cls.__name__)))

        #monkey patching error methods 
        self._app.notfound = notfound
        self._app.internalerror = internalerror
        web.webapi.nomethod = nomethod

    def _setup_logging(self, log_format='%(asctime)s %(process)s %(levelname)s %(name)s %(message)s'):
        '''override logging middleware to use python logging instead of stderr'''
        from web.httpserver import LogMiddleware
        def log(self, status, environ):
            _log = logging.getLogger('apiserver')
            req = environ.get('PATH_INFO', '_')
            protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
            method = environ.get('REQUEST_METHOD', '-')
            host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                              environ.get('REMOTE_PORT','-'))

            msg = '%s - - "%s %s %s" - %s' % (host, protocol, method, req, status)
            _log.info(web.utils.safestr(msg))

        #monkey patching log method
        LogMiddleware.log = log

        #setup logging
        root_logger = logging.getLogger()
        root_logger.setLevel(self._log_level)
        logging_handle = logging.handlers.WatchedFileHandler(self._log_path)
        log_formatter = logging.Formatter(log_format)
        logging_handle.setFormatter(log_formatter)
        root_logger.addHandler(logging_handle)

    def run(self, ip='0.0.0.0', port=8080, threads=10):
        '''run apiserver instance on a given ip and port'''
        #monkey patch WSGIServer so we can control the initial amount of thread in the pool
        def WSGIServer(server_address, wsgi_app):
            '''increase threads in pool and ignore any ssl support'''
            from web.wsgiserver import CherryPyWSGIServer
            return CherryPyWSGIServer(server_address, wsgi_app, numthreads=threads, server_name=self._server_name)

        web.httpserver.WSGIServer = WSGIServer

        #run server
        web.httpserver.runsimple(self._app.wsgifunc(), (ip, port))
