from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from selections.models import Selection, SportSelection

from .commands.base import (FillFormCommand, LoginCommand,
                            RemoveFromBasketCommand, ReservationCommandRunner)
from .filters import StatusFilter
from .helpers import show_slots
from .models import Reservation, ReservationJob
from .serializers import ReservationJobSerializer, ReservationSerializer


class ShowSlotsView(APIView):
    def get(self, request):
        court_selection = request.GET.get("court_selection")
        show_future_slots = bool(int(request.GET.get("sfs", 1)))
        sport_selection = SportSelection.objects.get(pitch_id=court_selection)
        selection = Selection.objects.filter(sport_selection=sport_selection).last()
        runner = ReservationCommandRunner(
            request.user,
            selection,
            sport_selection,
            commands=[LoginCommand(), FillFormCommand()],
            court_selection=court_selection,
        )
        runner()
        data = show_slots(runner.browser, show_future_slots=show_future_slots)
        return Response(data)


class ReservationViewSet(ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StatusFilter

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(methods=["POST"], detail=False, url_path="remove-basket")
    def remove_basket(self, *args, **kwargs):
        request = args[0]
        reservation = Reservation.objects.get(id=request.data["id"])
        runner = ReservationCommandRunner(
            request.user,
            reservation.selection,
            reservation.selection.sport_selection,
            commands=[LoginCommand(), RemoveFromBasketCommand()],
            court_selection=None,
        )
        runner()
        reservation.status = Reservation.REMOVED_FROM_BASKET
        reservation.save()
        return Response({"status": "OK"})


class ReservationJobViewSet(ModelViewSet):
    queryset = ReservationJob.objects.all()
    serializer_class = ReservationJobSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StatusFilter

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user, **self.request.data)
