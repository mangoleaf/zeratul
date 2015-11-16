from django import template

register = template.Library()

@register.simple_tag
def divide(value, divisor):
    return int(value) / int(divisor)

