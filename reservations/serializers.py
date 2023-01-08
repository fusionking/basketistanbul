from datetime import datetime

from rest_framework import serializers as drf_serializers

from selections.models import Selection, Slot, SportSelection
from selections.serializers import SelectionSerializer

from .helpers import create_reservation_job
from .models import Reservation, ReservationJob


class ReservationSerializer(drf_serializers.ModelSerializer):
    selection = SelectionSerializer()

    class Meta:
        model = Reservation
        fields = "__all__"


class ReservationJobSerializer(drf_serializers.ModelSerializer):
    selection = SelectionSerializer(read_only=True)

    class Meta:
        model = ReservationJob
        fields = ("id", "selection", "execution_type", "execution_time", "status")
        read_only_fields = ("execution_type", "execution_time")

    def create(self, validated_data):
        # Slot
        selection = validated_data["selection"]
        slot = selection["slot"]
        date_obj = datetime.strptime(slot["date"], "%d.%m.%Y %H:%M")
        slot, created = Slot.objects.get_or_create(
            date_time__date=date_obj,
            date_time__hour=date_obj.hour,
            defaults={"date_time": date_obj, "event_target": slot.get("event_target")},
        )
        # Get or create Sport Selection
        sport_selection = selection["sport_selection"]
        sport_selection, created = SportSelection.objects.get_or_create(
            pitch_id=sport_selection["pitch_id"]
        )
        # Get or create Selection
        selection, created = Selection.objects.get_or_create(
            sport_selection=sport_selection, slot=slot
        )
        reservation_job = create_reservation_job(selection, validated_data["user"])
        return reservation_job
