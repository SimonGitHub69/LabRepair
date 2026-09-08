from django.db.models import Case, IntegerField, Q, Value, When
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


def annotate_anagrafica_cognome_priority(queryset, query):
    """
    Ordina i match dando priorità al Cognome, poi al Nome.
    Rank più basso = migliore.
    """
    query = (query or "").strip()
    tokens = [part for part in query.split() if part]
    first = tokens[0] if tokens else ""
    second = tokens[1] if len(tokens) > 1 else ""

    whens = []
    if first and second:
        # Cognome + Nome nell'ordine naturale della ricerca.
        whens.extend(
            [
                When(
                    Q(cognome__istartswith=first)
                    & (Q(nome__istartswith=second) | Q(nome__icontains=second)),
                    then=Value(0),
                ),
                When(
                    Q(cognome__icontains=first) & Q(nome__icontains=second),
                    then=Value(1),
                ),
                # Ordine invertito (Nome Cognome): priorità inferiore.
                When(
                    Q(nome__istartswith=first)
                    & (Q(cognome__istartswith=second) | Q(cognome__icontains=second)),
                    then=Value(5),
                ),
            ]
        )
    if first:
        whens.extend(
            [
                When(cognome__istartswith=first, then=Value(2)),
                When(cognome__icontains=first, then=Value(3)),
                When(ragione_sociale__istartswith=first, then=Value(4)),
                When(nome__istartswith=first, then=Value(6)),
                When(nome__icontains=first, then=Value(7)),
            ]
        )

    return queryset.annotate(
        search_rank=Case(
            *whens,
            default=Value(9),
            output_field=IntegerField(),
        )
    )
