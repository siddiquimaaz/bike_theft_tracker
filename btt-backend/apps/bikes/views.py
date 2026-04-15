"""
apps/bikes/views.py
Bike CRUD (owner-only) and public vehicle search endpoints.
"""
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsOwner
from .models import Bike
from .serializers import (
    BikeCreateSerializer,
    BikeUpdateSerializer,
    BikeListSerializer,
    BikeDetailSerializer,
)


class BikeListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/bikes/  — List the authenticated owner's bikes
    POST /api/bikes/  — Register a new motorcycle
    """
    permission_classes = [IsOwner]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BikeCreateSerializer
        return BikeListSerializer

    def get_queryset(self):
        return (
            Bike.objects.filter(owner=self.request.user, deleted_at__isnull=True)
            .prefetch_related("theft_reports")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class BikeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/bikes/{id}/  — Full bike detail
    PUT    /api/bikes/{id}/  — Update mutable fields (color, plate, photo)
    DELETE /api/bikes/{id}/  — Soft-delete (blocked if active theft report)
    """
    permission_classes = [IsOwner]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return BikeUpdateSerializer
        return BikeDetailSerializer

    def get_queryset(self):
        return Bike.objects.filter(owner=self.request.user, deleted_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        bike = self.get_object()
        try:
            bike.soft_delete()
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"message": "Bike removed from your registry."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ─── Public Search ─────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def public_bike_search(request):
    """
    GET /api/search/bike/?q={query}
    Search by engine number, chassis number, or registration plate.
    Returns stolen status ONLY — no owner personal data exposed.
    """
    query = request.query_params.get("q", "").strip().upper()
    if len(query) < 3:
        return Response(
            {"error": "Search query must be at least 3 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    bikes = Bike.objects.filter(
        Q(engine_number__icontains=query)
        | Q(chassis_number__icontains=query)
        | Q(registration_number__icontains=query),
        deleted_at__isnull=True,
    ).prefetch_related("theft_reports")

    results = [
        {
            "make": b.make,
            "model": b.model,
            "year": b.year,
            "color": b.color,
            "engine_number": b.engine_number,
            "chassis_number": b.chassis_number,
            "registration_number": b.registration_number,
            "status": "REPORTED STOLEN" if b.is_stolen else "Not reported stolen",
        }
        for b in bikes
    ]

    return Response({"query": query, "results": results, "count": len(results)})


@api_view(["GET"])
@permission_classes([AllowAny])
def city_report_count(request, city):
    """
    GET /api/search/city/{city}/
    Returns count of active stolen reports in a city — for public awareness.
    """
    from apps.reports.models import TheftReport

    count = TheftReport.objects.filter(
        theft_city__iexact=city,
        status__in=["stolen", "under_investigation"],
        deleted_at__isnull=True,
    ).count()

    return Response({"city": city, "active_theft_reports": count})
