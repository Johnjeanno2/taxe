from django import template

register = template.Library()

@register.filter
def get_icon(icon_map, model_name):
    return icon_map.get(model_name, 'fa-cube')