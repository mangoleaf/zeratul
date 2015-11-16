from django import template

register = template.Library()

@register.simple_tag
def divide(value, divisor):
    return int(value) / int(divisor)

@register.filter
def get_type(value):
    return str(type(value)).split('\'')[1]

