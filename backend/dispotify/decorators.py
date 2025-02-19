from typing import Literal
import requests
import json

from functools import wraps
from rest_framework import viewsets
from django.http import HttpRequest, HttpResponse
from asgiref.sync import async_to_sync

from chord.chord import ChordNode, ChordNodeReference, get_hash, hash_string

TARGETING_HEADER = "Chord-Target-Signature"


def chord_distribute(k: int, _key: Literal[None, "metadata"] = None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(
            self: viewsets.ModelViewSet, request: HttpRequest, *args, **kwargs
        ) -> HttpResponse:
            node = ChordNode.get_instance()

            assert node

            req_method = request.method
            req_body = request.body.decode()
            req_headers = dict(request.headers)
            req_path = request.path
            req_params = request.GET

            key = req_body if not _key else _key
            data_id = get_hash(key)

            try:
                json_body = json.loads(req_body)

                if "id" not in json_body:
                    json_body["id"] = hash_string(req_body)

                if "audio_id" in req_params:
                    data_id = int(req_params["audio_id"], 16) % (1 << node.id_bitlen)
                elif "id" in req_params:
                    data_id = int(req_params["id"], 16) % (1 << node.id_bitlen)
                else:
                    data_id = int(json_body["id"], 16) % (1 << node.id_bitlen)
                req_body = json.dumps(json_body)
            except json.JSONDecodeError:
                print("Request body is not JSON, this must be an error.")

            succ = async_to_sync(node.find_successor)(data_id)
            replicants = async_to_sync(node.get_replicants)(k, succ)  # Usar k aquí

            target_signature = req_headers.get(TARGETING_HEADER, None)

            # This is a hack to make the request body available in the view function.
            # It's not a good idea to modify the request object like this, but it's the only way to make it work.
            # TODO: Find a better way to do this. Perhaps...
            setattr(request, "body", req_body.encode())

            if target_signature == node.ring_signature:
                return view_func(self, request, *args, **kwargs)

            for rep in replicants:
                if rep.node_id == node.node_id:
                    response = view_func(self, request, *args, **kwargs)
                else:
                    response = forward_request_to_successor(
                        rep,
                        req_method,
                        req_body,
                        req_headers,
                        req_path,
                        req_params,
                    )

            return response

        return _wrapped_view

    return decorator


def forward_request_to_successor(
    succ: ChordNodeReference,
    method: str | None,
    body: str | None,
    headers: dict | None,
    path: str,
    params,
) -> HttpResponse:
    url = f"http://{succ.ip_address}:8000{path}"

    headers[TARGETING_HEADER] = ChordNode.get_instance().ring_signature  # type: ignore

    try:
        if method == "POST":
            response = requests.post(url, data=body, headers=headers)

        elif method == "GET":
            response = requests.get(url, headers=headers, params=params)

        elif method == "PUT":
            response = requests.put(url, data=body, headers=headers)

        elif method == "DELETE":
            response = requests.delete(url, headers=headers)

        elif method == "PATCH":
            response = requests.patch(url, data=body, headers=headers)

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
