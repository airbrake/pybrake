from .route_metric import _RouteBreakdown


def test_initiate_route_breakdown():
    route = _RouteBreakdown(method="GET", route="/test",
                            responseType="application/json", time=1648551580.0367732)
    assert route.__dict__ == {'count': 0,
                              'sum': 0,
                              'sumsq': 0,
                              'tdigest': 'AAAAAkAkAAAAAAAAAAAAAA==',
                              'groups': {},
                              'method': 'GET',
                              'route': '/test',
                              'responseType': 'application/json',
                              'time': '2022-03-29T10:59:00Z'}
