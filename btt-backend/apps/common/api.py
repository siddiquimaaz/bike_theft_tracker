"""
apps/common/api.py
Small helpers shared by the function-based API views.

Every view in this project reports failures the same way — a JSON body with a
single "error" key — and most of them start by fetching one row that may not
exist (or may exist but sit outside the caller's city/ownership scope, which we
deliberately report as 404 rather than 403). These two helpers keep that shape
in one place instead of restating it at every call site.
"""
from rest_framework.response import Response


def error_response(message, status_code):
    """A `{"error": message}` body with the given HTTP status."""
    return Response({"error": message}, status=status_code)


def get_object_or_none(queryset, **lookup):
    """
    Return the single row matching `lookup`, or None when there is no match.

    Prefer this over catching DoesNotExist at the call site: the caller does not
    have to name the model's exception class, and the "missing" and "out of
    scope" cases collapse into one branch, since callers pass an already-scoped
    queryset.
    """
    try:
        return queryset.get(**lookup)
    except queryset.model.DoesNotExist:
        return None
