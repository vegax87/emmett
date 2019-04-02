# -*- coding: utf-8 -*-
"""
    tests.expose
    ----------------

    Test weppy expose module

    :copyright: (c) 2014-2016 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import pendulum
import pytest

from contextlib import contextmanager

from helpers import FakeRequestContext
from weppy import App, abort
from weppy.ctx import current
from weppy.expose import url
from weppy.http import HTTP
from weppy.testing.env import ScopeBuilder


@contextmanager
def current_ctx(path):
    builder = ScopeBuilder(path)
    token = current._init_(FakeRequestContext, None, builder.get_data()[0])
    yield current
    current._close_(token)


@pytest.fixture(scope='module')
def app():
    app = App(__name__)
    app.languages = ['en', 'it']
    app.language_default = 'en'
    app.language_force_on_url = True

    @app.route()
    def test_route():
        return 'Test Router'

    @app.route()
    def test_404():
        abort(404, 'Not found, dude')

    @app.route('/test2/<int:a>/<str:b>')
    def test_route2(a, b):
        return 'Test Router'

    @app.route('/test3/<int:a>/foo(/<str:b>)?(.<str:c>)?')
    def test_route3(a, b, c):
        return 'Test Router'

    @app.route('/test_int/<int:a>')
    def test_route_int(a):
        return 'Test Router'

    @app.route('/test_float/<float:a>')
    def test_route_float(a):
        return 'Test Router'

    @app.route('/test_date/<date:a>')
    def test_route_date(a):
        return 'Test Router'

    @app.route('/test_alpha/<alpha:a>')
    def test_route_alpha(a):
        return 'Test Router'

    @app.route('/test_str/<str:a>')
    def test_route_str(a):
        return 'Test Router'

    @app.route('/test_any/<any:a>')
    def test_route_any(a):
        return 'Test Router'

    @app.route(
        '/test_complex'
        '/<int:a>'
        '/<float:b>'
        '/<date:c>'
        '/<alpha:d>'
        '/<str:e>'
        '/<any:f>'
    )
    def test_route_complex(a, b, c, d, e, f):
        return 'Test Router'

    return app


def test_routing(app):
    with current_ctx('/test_int') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_int/a') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_int/1.1') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_int/2000-01-01') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_int/1') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_int'

    with current_ctx('/test_float') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_float/a.a') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_float/1') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_float/1.1') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_float'

    with current_ctx('/test_date') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_date/2000-01-01') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_date'

    with current_ctx('/test_alpha') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_alpha/a1') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_alpha/a-a') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_alpha/a') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_alpha'

    with current_ctx('/test_str') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_str/a/b') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_str/a1-') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_str'

    with current_ctx('/test_any') as ctx:
        route, args = app.route.match(ctx.request)
        assert not route

    with current_ctx('/test_any/a/b') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_any'


def test_route_args(app):
    with current_ctx('/test_complex/1/1.2/2000-12-01/foo/foo1/bar/baz') as ctx:
        route, args = app.route.match(ctx.request)
        assert route.name == 'test_expose.test_route_complex'
        assert args['a'] == 1
        assert args['b'] == 1.2
        assert args['c'] == pendulum.datetime(2000, 12, 1)
        assert args['d'] == 'foo'
        assert args['e'] == 'foo1'
        assert args['f'] == 'bar/baz'


@pytest.mark.asyncio
async def test_expose_valid_route(app):
    with current_ctx('/it/test_route') as ctx:
        response = await app.route.dispatch()
        assert response.status_code == ctx.response.status == 200
        assert response.body == 'Test Router'
        assert ctx.request.language == 'it'


@pytest.mark.asyncio
async def test_expose_not_found_route(app):
    with current_ctx('/'):
        with pytest.raises(HTTP) as excinfo:
            await app.route.dispatch()
        assert excinfo.value.status_code == 404
        assert excinfo.value.body == 'Resource not found\n'


@pytest.mark.asyncio
async def test_expose_exception_route(app):
    with current_ctx('/test_404'):
        with pytest.raises(HTTP) as excinfo:
            await app.route.dispatch()
        assert excinfo.value.status_code == 404
        assert excinfo.value.body == 'Not found, dude'


def test_static_url(app):
    link = url('static', 'file')
    assert link == '/static/file'
    app.config.static_version_urls = True
    app.config.static_version = '1.0.0'
    link = url('static', 'js/foo.js', language='it')
    assert link == '/it/static/_1.0.0/js/foo.js'


def test_module_url(app):
    with current_ctx('/') as ctx:
        ctx.request.language = 'it'
        link = url('test_route')
        assert link == '/it/test_route'
        link = url('test_route2')
        assert link == '/it/test2'
        link = url('test_route2', [2])
        assert link == '/it/test2/2'
        link = url('test_route2', [2, 'foo'])
        assert link == '/it/test2/2/foo'
        link = url('test_route3')
        assert link == '/it/test3'
        link = url('test_route3', [2])
        assert link == '/it/test3/2/foo'
        link = url('test_route3', [2, 'bar'])
        assert link == '/it/test3/2/foo/bar'
        link = url('test_route3', [2, 'bar', 'json'])
        assert link == '/it/test3/2/foo/bar.json'
        link = url(
            'test_route3', [2, 'bar', 'json'], {'foo': 'bar', 'bar': 'foo'})
        lsplit = link.split('?')
        assert lsplit[0] == '/it/test3/2/foo/bar.json'
        assert lsplit[1] in ['foo=bar&bar=foo', 'bar=foo&foo=bar']


@pytest.mark.asyncio
async def test_global_url_prefix(app):
    app.route._bind_app_(app, 'foo')

    with current_ctx('/') as ctx:
        app.config.static_version_urls = False
        ctx.request.language = 'en'

        link = url('test_route')
        assert link == '/foo/test_route'

        link = url('static', 'js/foo.js')
        assert link == '/foo/static/js/foo.js'

        app.config.static_version_urls = True
        app.config.static_version = '1.0.0'

        link = url('static', 'js/foo.js')
        assert link == '/foo/static/_1.0.0/js/foo.js'

        app.config.static_version_urls = False
        ctx.request.language = 'it'

        link = url('test_route')
        assert link == '/foo/it/test_route'

        link = url('static', 'js/foo.js')
        assert link == '/foo/it/static/js/foo.js'

        app.config.static_version_urls = True
        app.config.static_version = '1.0.0'

        link = url('static', 'js/foo.js')
        assert link == '/foo/it/static/_1.0.0/js/foo.js'
