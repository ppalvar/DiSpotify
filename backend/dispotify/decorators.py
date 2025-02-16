from typing import Literal
import requests

from functools import wraps
from rest_framework import viewsets
from django.http import HttpRequest, HttpResponse
from asgiref.sync import async_to_sync

from chord.chord import ChordNode, ChordNodeReference, get_hash

TARGETING_HEADER = "Chord-Target-Signature"


def chord_distribute(k: int, _key: Literal[None, "metadata"] = None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(
            self: viewsets.ModelViewSet, request: HttpRequest, *args, **kwargs
        ) -> HttpResponse:
            node = ChordNode.get_instance()

            assert node

            key = request.body.decode("utf-8") if not _key else _key
            data_id = get_hash(key)

            succ = async_to_sync(node.find_successor)(data_id)
            replicants = async_to_sync(node.get_replicants)(k, succ)  # Usar k aquí

            print(f">>>>>> {key} {data_id} -> {[r.node_id for r in replicants]}")

            target_signature = request.headers.get(TARGETING_HEADER, None)

            if target_signature == node.ring_signature:
                return view_func(self, request, *args, **kwargs)

            for rep in replicants:
                if rep.node_id == node.node_id:
                    response = view_func(self, request, *args, **kwargs)
                else:
                    response = forward_request_to_successor(rep, request)

            return response

        return _wrapped_view

    return decorator


def forward_request_to_successor(
    succ: ChordNodeReference, request: HttpRequest
) -> HttpResponse:
    url = f"http://{succ.ip_address}:8000{request.path}"
    headers = dict(request.headers)

    headers[TARGETING_HEADER] = ChordNode.get_instance().ring_signature  # type: ignore

    print(f"Redireccionando a {url}.")

    try:
        if request.method == "POST":
            response = requests.post(url, data=request.body, headers=headers)

        elif request.method == "GET":
            response = requests.get(url, headers=headers, params=request.GET)

        elif request.method == "PUT":
            response = requests.put(url, data=request.body, headers=headers)

        elif request.method == "DELETE":
            response = requests.delete(url, headers=headers)

        elif request.method == "PATCH":
            response = requests.patch(url, data=request.body, headers=headers)

        else:
            return HttpResponse("Unknown HTTP method.", status=500)

        return parse_response(response)
    except requests.RequestException:
        return HttpResponse("Internal Server Error", status=500)


def parse_response(
    requests_response: requests.Response,
) -> HttpResponse:
    content = requests_response.content
    status_code = requests_response.status_code
    headers = requests_response.headers

    django_response = HttpResponse(content=content, status=status_code)

    for key, value in headers.items():
        django_response[key] = value

    return django_response
