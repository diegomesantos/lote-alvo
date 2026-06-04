from django import template
from django.utils.html import format_html, mark_safe
from core.calculos.motor import fmt_brl, fmt_pct

register = template.Library()


@register.simple_tag
def money_field(field, label=None):
    """Renderiza campo monetário com wrapper R$ e IMask."""
    lbl = label or field.label
    errors = ""
    if field.errors:
        errors = f'<p class="text-red-500 text-xs mt-1">{", ".join(field.errors)}</p>'
    # Gera input visível com IMask + input hidden para submissão
    field_id = field.field.widget.attrs.get('id', f'id_{field.html_name}')
    hidden_field = f'<input type="hidden" name="{field.html_name}" id="{field_id}_hidden" value="{field.value() or 0}">'
    return format_html(
        '<div>'
        '<label class="block text-sm font-medium text-gray-700 mb-1">{}</label>'
        '<div class="field-money"><span class="field-prefix">R$</span>{}{}</div>'
        '{}</div>',
        lbl, mark_safe(str(field)), mark_safe(hidden_field), mark_safe(errors)
    )


@register.simple_tag
def pct_field(field, label=None, suffix="%"):
    """Renderiza campo percentual com wrapper % e IMask."""
    lbl = label or field.label
    errors = ""
    if field.errors:
        errors = f'<p class="text-red-500 text-xs mt-1">{", ".join(field.errors)}</p>'
    # Gera input visível com IMask + input hidden para submissão
    field_id = field.field.widget.attrs.get('id', f'id_{field.html_name}')
    hidden_field = f'<input type="hidden" name="{field.html_name}" id="{field_id}_hidden" value="{field.value() or 0}">'
    return format_html(
        '<div>'
        '<label class="block text-sm font-medium text-gray-700 mb-1">{}</label>'
        '<div class="field-pct">{}<span class="field-suffix">{}</span>{}</div>'
        '{}</div>',
        lbl, mark_safe(str(field)), suffix, mark_safe(hidden_field), mark_safe(errors)
    )


@register.filter
def brl(value, short=False):
    try:
        return fmt_brl(float(value), short=bool(short))
    except (TypeError, ValueError):
        return "—"


@register.filter
def brl_short(value):
    try:
        return fmt_brl(float(value), short=True)
    except (TypeError, ValueError):
        return "—"


@register.filter
def pct(value):
    try:
        return fmt_pct(float(value))
    except (TypeError, ValueError):
        return "—"


@register.filter
def abs_val(value):
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return value


@register.filter
def dict_get(d, key):
    """Access dict value by key in templates: {{ mydict|dict_get:key }}"""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.simple_tag
def resultado_classe(valor):
    try:
        v = float(valor)
        if v > 0:
            return "text-green-600"
        return "text-red-600"
    except (TypeError, ValueError):
        return "text-gray-600"


@register.simple_tag
def verdict_classe(roi):
    try:
        r = float(roi)
        if r >= 15:
            return "bg-green-50 border-green-200 text-green-800"
        elif r > 0:
            return "bg-yellow-50 border-yellow-200 text-yellow-800"
        return "bg-red-50 border-red-200 text-red-800"
    except (TypeError, ValueError):
        return "bg-gray-50 border-gray-200 text-gray-800"
