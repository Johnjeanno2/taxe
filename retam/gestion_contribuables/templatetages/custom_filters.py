# gestion_contribuables/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def sum_values(queryset, attribute):
    return sum(getattr(item, attribute, 0) for item in queryset)