from rest_framework import serializers as drf_serializers

from reservations.models import ReservationJob

from .models import Selection, Slot, SportSelection


class SportSelectionSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = SportSelection
        fields = ("id", "branch_name", "complex_name", "pitch_name")


class SlotSerializer(drf_serializers.ModelSerializer):
    date = drf_serializers.SerializerMethodField()

    class Meta:
        model = Slot
        fields = (
            "id",
            "date",
            "event_target",
        )

    def get_date(self, instance):
        return instance.date_time.replace(tzinfo=None)


class SelectionSerializer(drf_serializers.ModelSerializer):
    slot = SlotSerializer()
    sport_selection = SportSelectionSerializer()
    reservation_job_status = drf_serializers.SerializerMethodField()

    class Meta:
        model = Selection
        fields = "__all__"

    def get_reservation_job_status(self, selection):
        rj = ReservationJob.objects.filter(
            selection=selection, user=self.context["request"].user
        ).last()
        return rj.status if rj else ""
