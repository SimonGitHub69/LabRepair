from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def sort_header(context, key, label, css_class="", element="th"):
    """
    Header di colonna ordinabile.
    Uso: {% sort_header "codice" "Codice" %}
         {% sort_header "prezzo" "Prezzo" "text-end" %}
         {% sort_header "codice" "Codice" "" "div" %}
    """
    request = context.get("request")
    if request is None:
        if element == "div":
            return format_html('<div class="{}">{}</div>', css_class, label)
        return format_html('<th class="{}">{}</th>', css_class, label)

    current = context.get("list_sort") or ""
    current_dir = context.get("list_dir") or "asc"
    active = current == key

    if active:
        next_dir = "desc" if current_dir == "asc" else "asc"
    else:
        next_dir = "asc"

    query = request.GET.copy()
    query["sort"] = key
    query["dir"] = next_dir
    query.pop("page", None)
    url = "?" + query.urlencode()

    link_class = "st-sort-link"
    if active:
        link_class += f" is-active is-{current_dir}"
        icon_name = "ti-chevron-up" if current_dir == "asc" else "ti-chevron-down"
        link = format_html(
            '<a href="{}" class="{}" title="Ordina per {}">{} <i class="ti {}" aria-hidden="true"></i></a>',
            url,
            link_class,
            label,
            label,
            icon_name,
        )
    else:
        link = format_html(
            '<a href="{}" class="{}" title="Ordina per {}">{}</a>',
            url,
            link_class,
            label,
            label,
        )

    el_class = (css_class or "").strip()
    if element == "div":
        if el_class:
            return format_html('<div class="{}">{}</div>', el_class, link)
        return format_html("<div>{}</div>", link)

    if el_class:
        return format_html('<th class="{}">{}</th>', el_class, link)
    return format_html("<th>{}</th>", link)


@register.inclusion_tag("partials/list_sort_hidden.html", takes_context=True)
def list_sort_hidden(context):
    """Campi hidden per preservare sort/dir nei form filtri GET."""
    return {
        "list_sort": context.get("list_sort") or "",
        "list_dir": context.get("list_dir") or "",
    }
