"""Ordinamento colonne liste via ?sort=&dir= (whitelist per vista)."""


class SortableListMixin:
    """
    Aggiunge ordinamento server-side alle ListView.

    Definire sulla vista:
      sort_fields = {"codice": "codice", "cliente": ("cliente__cognome", "cliente__nome")}
      default_sort = "codice"   # chiave in sort_fields
      default_dir = "asc"      # asc|desc
    e nel get_queryset terminare con:
      return self.apply_list_ordering(queryset)
    """

    sort_fields = {}
    default_sort = ""
    default_dir = "asc"
    sort_param = "sort"
    dir_param = "dir"

    def get_default_sort(self):
        return self.default_sort

    def get_default_dir(self):
        direction = (self.default_dir or "asc").lower()
        return direction if direction in {"asc", "desc"} else "asc"

    def get_sort_fields(self):
        return self.sort_fields or {}

    def get_sort_state(self):
        fields_map = self.get_sort_fields()
        raw_key = (self.request.GET.get(self.sort_param) or "").strip()
        raw_dir = (self.request.GET.get(self.dir_param) or "").strip().lower()

        key = raw_key if raw_key in fields_map else (self.get_default_sort() or "")
        if key and key not in fields_map:
            key = ""

        if raw_key in fields_map and raw_dir in {"asc", "desc"}:
            direction = raw_dir
        elif key == self.get_default_sort():
            direction = self.get_default_dir()
        elif raw_dir in {"asc", "desc"}:
            direction = raw_dir
        else:
            direction = "asc"

        if not key:
            return "", direction, self._fallback_ordering()

        fields = fields_map[key]
        if isinstance(fields, str):
            fields = (fields,)

        prefix = "-" if direction == "desc" else ""
        ordering = tuple(f"{prefix}{str(field).lstrip('-')}" for field in fields)
        has_id = any(str(field).lstrip("-") == "id" for field in ordering)
        if not has_id:
            ordering = ordering + (("-id" if direction == "desc" else "id"),)
        return key, direction, ordering

    def _fallback_ordering(self):
        """Se non c'è default_sort valido, lascia l'ordine già impostato o usa -id."""
        return ("-id",)

    def apply_list_ordering(self, queryset):
        _key, _direction, ordering = self.get_sort_state()
        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        key, direction, _ordering = self.get_sort_state()
        context["list_sort"] = key
        context["list_dir"] = direction
        return context
