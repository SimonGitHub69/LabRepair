from django import forms
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class NoAutofillTextInput(forms.Widget):
    """
    Campo testo anti-autofill Chrome.
    - hidden con il name reale (quello che arriva in POST)
    - textarea visibile senza name: Chrome non propone gli indirizzi salvati
    """

    input_type = "text"
    template_name = None

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "form-control st-input-like",
            "rows": "1",
            "wrap": "off",
            "spellcheck": "false",
            "autocomplete": "off",
            "data-block-autofill": "1",
            "data-no-autofill-mirror": "1",
        }
        if attrs:
            merged = default_attrs.copy()
            extra_class = attrs.get("class")
            merged.update(attrs)
            css = merged.get("class") or ""
            if extra_class and "st-input-like" not in css:
                merged["class"] = f"{css} st-input-like".strip()
            if "form-control" not in (merged.get("class") or ""):
                merged["class"] = f"form-control {merged.get('class', '')}".strip()
            default_attrs = merged
        super().__init__(default_attrs)

    def format_value(self, value):
        if value is None:
            return ""
        return str(value)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        field_id = final_attrs.get("id")
        css_class = final_attrs.get("class") or "form-control st-input-like"
        rows = final_attrs.get("rows") or "1"
        wrap = final_attrs.get("wrap") or "off"
        spellcheck = final_attrs.get("spellcheck") or "false"
        value = self.format_value(value)

        skip = {
            "id",
            "class",
            "rows",
            "wrap",
            "spellcheck",
            "autocomplete",
            "type",
            "name",
        }
        extra = {}
        for key, val in final_attrs.items():
            if key in skip or val is False or val is None:
                continue
            extra[key] = val

        hidden_attrs = {"type": "hidden", "name": name, "value": value, "data-no-autofill-store": "1"}
        if field_id:
            hidden_attrs["id"] = f"{field_id}_store"

        textarea_attrs = {
            "class": css_class,
            "rows": rows,
            "wrap": wrap,
            "spellcheck": spellcheck,
            "autocomplete": "off",
            "data-no-autofill-mirror": "1",
            "data-store-name": name,
        }
        if field_id:
            textarea_attrs["id"] = field_id
        textarea_attrs.update(extra)

        return mark_safe(
            format_html(
                "<input{}><textarea{}>{}</textarea>",
                flatatt(hidden_attrs),
                flatatt(textarea_attrs),
                value,
            )
        )


class NoAutofillEmailInput(NoAutofillTextInput):
    def __init__(self, attrs=None):
        attrs = dict(attrs or {})
        attrs.setdefault("inputmode", "email")
        super().__init__(attrs=attrs)
