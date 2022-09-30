import pybrake.metrics as metrics

from pybrake.notifier import Notifier
from .test_helper import get_exception, TestBacklog, MockResponse

route_payload = {
    "routes": [
        {
            "count": 1,
            "sum": 0.006198883056640625,
            "sumsq": 3.842615114990622e-05,
            "tdigest": "AAAAAkAkAAAAAAAAAAAAATvLIAAB",
            "method": "GET",
            "route": "/test",
            "statusCode": 200,
            "time": "2022-09-29T10:10:00Z"
        }
    ]
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer xxxxxxxxxxxxxxxxxxxxxxx",
}
route_url = "http://localhost:5000/api/v5/projects/0/routes-stats"
error_url = "http://localhost:5000/api/v3/projects/0/notices"

notifier = Notifier()

err = get_exception()
notice = notifier.build_notice(err)


metrics.Error_Backlog = TestBacklog()
metrics.APM_Backlog = TestBacklog()


def test_send_500_status(mocker, caplog):
    resp = MockResponse(resp_data="Error: Internal Server Error", code=500)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    metrics.send(url=route_url, payload=route_payload, headers=headers)
    assert "airbrake: unexpected response status_code=500" in caplog.text


def test_send_exception(mocker, caplog):
    resp = MockResponse(resp_data="IOError", code=200)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    metrics.send(url=route_url, payload=route_payload, headers=headers)
    assert "IOError: for tes" in caplog.text


def test_send_success(mocker, caplog):
    resp = MockResponse(resp_data="Done", code=200)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    assert metrics.send(url=route_url, payload=route_payload, headers=headers) is None


def test_send_json_loads(mocker, caplog):
    resp = MockResponse(resp_data=b'Gone', code=410)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    metrics.send(url=route_url, payload=route_payload, headers=headers)
    assert "Expecting value" in caplog.text


def test_send_return_message(mocker, caplog):
    resp = MockResponse(resp_data='{"message": "Message in data!"}'.encode("utf-8"), code=410)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    metrics.send(url=route_url, payload=route_payload, headers=headers)
    assert "Message in data!" in caplog.text


def test_send_without_encode(mocker, caplog):
    resp = MockResponse(resp_data=b"\x81", code=410)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    metrics.send(url=route_url, payload=route_payload, headers=headers)
    assert "'utf-8' codec can't decode byte 0x81 in position 0" in caplog.text


def test_send_too_many_request(mocker, caplog):
    resp = MockResponse(resp_data="IOError", code=429)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    assert metrics.send(url=route_url, payload=route_payload,
                        headers=headers) is None


def test_send_notice_unexpected_res(mocker, caplog):
    resp = MockResponse(resp_data='{"ID": "this id the ID"}'.encode(
        "utf-8"), code=200)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert output["error"] == 'unexpected Airbrake response'


def test_send_notice_too_many_request(mocker, caplog):
    resp = MockResponse(resp_data="Too Many Request", code=429)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert output["error"] == 'X-RateLimit-Delay header is missing'


def test_send_notice_backlog(mocker, caplog):
    resp = MockResponse(resp_data=b'Gone', code=410)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert "Expecting value" in caplog.text
    assert str(output["error"]) == "Expecting value: line 1 column 1 (char 0)"


def test_send_notice_unexpected(mocker, caplog):
    resp = MockResponse(resp_data=b'Gone', code=310)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert str(output["error"]) == "airbrake: unexpected response status_code=310"


def test_send_notice_return_id(mocker, caplog):
    resp = MockResponse(resp_data='{"id": "this id the ID"}'.encode(
        "utf-8"), code=200)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert "this id the ID" in output["id"]


def test_send_notice_without_encode(mocker, caplog):
    resp = MockResponse(resp_data=b"\x81", code=410)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert "'utf-8' codec can't decode byte 0x81 in position 0" in str(output[
        "error"])


def test_send_notice_ioerror(mocker, caplog):
    resp = MockResponse(resp_data="IOError", code=200)
    mocker.patch(
        "urllib.request.urlopen",
        return_value=resp
    )

    output = metrics.send_notice(notifier=notifier, url=error_url,
                                 notice=notice, headers=headers)
    assert "IOError: for tes" in str(output[
        "error"])

metrics.APM_Backlog = None
metrics.Error_Backlog = None
