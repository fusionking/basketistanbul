from rest_framework.viewsets import ModelViewSet

from .models import Preference
from .serializers import PreferenceSerializer


class PreferenceViewSet(ModelViewSet):
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        selections = self.request.data.get("selections")
        serializer.save(user=user, selections=selections)
