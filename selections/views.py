from rest_framework_json_api.views import ModelViewSet

from .models import Selection, Slot, SportSelection
from .serializers import SelectionSerializer, SlotSerializer, SportSelectionSerializer


class SelectionViewSet(ModelViewSet):
    queryset = Selection.objects.all()
    serializer_class = SelectionSerializer


class SlotViewSet(ModelViewSet):
    queryset = Slot.objects.all()
    serializer_class = SlotSerializer


class SportSelectionViewSet(ModelViewSet):
    queryset = SportSelection.objects.all()
    serializer_class = SportSelectionSerializer
