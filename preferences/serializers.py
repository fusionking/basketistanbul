from datetime import datetime

from rest_framework import serializers

from selections.constants import COURT_NAMES_TO_PITCH_IDS
from selections.models import Selection, Slot, SportSelection
from selections.serializers import SelectionSerializer

from .models import Preference, SelectionPreference


class PreferenceSerializer(serializers.ModelSerializer):
    selections = SelectionSerializer(many=True, read_only=True)

    class Meta:
        model = Preference
        fields = (
            "id",
            "selections",
        )

    def create(self, validated_data):
        # Get or create Preference by user
        preference, created = Preference.objects.get_or_create(
            user=validated_data["user"],
        )
        # Check if Selection exists
        selections = validated_data["selections"]
        # Check if slot exists
        for selection_data in selections:
            slot = selection_data["slot"]
            date = slot["date"]
            date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M")
            slot, created = Slot.objects.get_or_create(
                date_time__date=date_obj,
                date_time__hour=date_obj.hour,
                defaults={"date_time": date_obj},
            )
            # Get or create Sport Selection
            sport_selection = selection_data["sport_selection"]
            pitch_name = sport_selection.get("pitch_name")
            pitch_id = sport_selection.get("pitch_id")
            if pitch_name and not pitch_id:
                pitch_id = COURT_NAMES_TO_PITCH_IDS.get(sport_selection["pitch_name"])

            sport_selection, created = SportSelection.objects.get_or_create(
                branch_name=sport_selection["branch_name"],
                complex_name=sport_selection["complex_name"],
                pitch_id=pitch_id,
            )
            # Get or create Selection
            selection, created = Selection.objects.get_or_create(
                sport_selection=sport_selection, slot=slot
            )
            if not preference.selections.filter(pk=selection.pk).exists():
                SelectionPreference.objects.create(
                    preference=preference, selection=selection
                )

        return preference
