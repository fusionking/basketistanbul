from django.db.models import Q
from django_filters import CharFilter
from django_filters import rest_framework as filters


class StatusFilter(filters.FilterSet):
    status = CharFilter(field_name="status", method="filter_status")

    def filter_status(self, queryset, name, value):
        return queryset.filter(~Q(status=value))
