from apps.core.programma import get_liste_righe_per_pagina

PAGE_SIZE_CHOICES = (10, 20, 50, 100)
DEFAULT_PAGE_SIZE = 20
SESSION_PAGE_SIZE_KEY = "liste_page_size"


class ConfigurablePaginationMixin:
    """Paginazione con page_size da GET, sessione o Parametri programma."""

    paginate_by = DEFAULT_PAGE_SIZE
    page_size_choices = PAGE_SIZE_CHOICES

    def get_paginate_by(self, queryset):
        raw = (self.request.GET.get("page_size") or "").strip()
        size = None
        if raw:
            try:
                size = int(raw)
            except (TypeError, ValueError):
                size = None
            if size in self.page_size_choices:
                self.request.session[SESSION_PAGE_SIZE_KEY] = size
                return size

        session_raw = self.request.session.get(SESSION_PAGE_SIZE_KEY)
        try:
            size = int(session_raw) if session_raw is not None else None
        except (TypeError, ValueError):
            size = None
        if size in self.page_size_choices:
            return size

        size = get_liste_righe_per_pagina()
        if size not in self.page_size_choices:
            size = self.paginate_by or DEFAULT_PAGE_SIZE
        return size

    def get_filters_query(self, extra=None):
        query_dict = self.request.GET.copy()
        query_dict.pop("page", None)
        if extra:
            for key, value in extra.items():
                if key not in query_dict or not str(query_dict.get(key) or "").strip():
                    query_dict[key] = value
        # Mantieni page_size nei link filtri/pagine anche se arriva dalla sessione.
        if "page_size" not in query_dict or not str(query_dict.get("page_size") or "").strip():
            query_dict["page_size"] = str(self.get_paginate_by(None))
        return query_dict.urlencode()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("filters_query", self.get_filters_query())
        page_size = self.get_paginate_by(None)
        context["page_size"] = page_size
        context["page_size_choices"] = self.page_size_choices
        page_obj = context.get("page_obj")
        if page_obj is not None and page_obj.paginator.count:
            context["page_range_start"] = page_obj.start_index()
            context["page_range_end"] = page_obj.end_index()
        else:
            context["page_range_start"] = 0
            context["page_range_end"] = 0
        return context
