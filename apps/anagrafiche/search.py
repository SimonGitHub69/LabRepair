from django.db.models import Q, Value
from django.db.models.functions import Concat


def build_anagrafica_name_search_q(query, *, include_contacts=True):
    """
    Ricerca anagrafica indipendente dall'ordine delle parole.
    Es. "Rossi Mario" e "Mario Rossi" trovano lo stesso cliente.
    """
    query = (query or "").strip()
    if not query:
        return Q()

    def field_q(token):
        q = (
            Q(cognome__icontains=token)
            | Q(nome__icontains=token)
            | Q(ragione_sociale__icontains=token)
            | Q(codice_fiscale__icontains=token)
            | Q(partita_iva__icontains=token)
            | Q(email__icontains=token)
            | Q(telefono__icontains=token)
        )
        if include_contacts:
            q |= Q(cellulare__icontains=token)
        return q

    tokens = [part for part in query.split() if part]
    if not tokens:
        return Q()

    combined = field_q(tokens[0])
    for token in tokens[1:]:
        combined &= field_q(token)

    # Match anche su "Cognome Nome" / "Nome Cognome" come stringa intera.
    combined |= Q(cognome_nome__icontains=query) | Q(nome_cognome__icontains=query)
    return combined


def annotate_anagrafica_name_search(queryset):
    return queryset.annotate(
        cognome_nome=Concat("cognome", Value(" "), "nome"),
        nome_cognome=Concat("nome", Value(" "), "cognome"),
    )
