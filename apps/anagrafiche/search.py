from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Concat

from apps.core.accents import AccentFold, fold_accents


def build_anagrafica_name_search_q(query, *, include_contacts=True):
    """
    Ricerca anagrafica indipendente dall'ordine delle parole e dagli accenti.
    Es. "Rossi Mario" / "Mario Rossi", "Filie" / "Filiè".
    """
    query = (query or "").strip()
    if not query:
        return Q()

    folded_tokens = [fold_accents(part) for part in query.split() if part]
    folded_tokens = [token for token in folded_tokens if token]
    if not folded_tokens:
        return Q()

    def field_q(token):
        q = (
            Q(_af_cognome__icontains=token)
            | Q(_af_nome__icontains=token)
            | Q(_af_ragione__icontains=token)
            | Q(_af_cf__icontains=token)
            | Q(_af_piva__icontains=token)
            | Q(_af_email__icontains=token)
            | Q(_af_telefono__icontains=token)
        )
        if include_contacts:
            q |= Q(_af_cellulare__icontains=token)
        return q

    combined = field_q(folded_tokens[0])
    for token in folded_tokens[1:]:
        combined &= field_q(token)

    folded_query = fold_accents(query)
    combined |= Q(_af_cognome_nome__icontains=folded_query) | Q(
        _af_nome_cognome__icontains=folded_query
    )
    return combined


def annotate_anagrafica_name_search(queryset):
    return queryset.annotate(
        cognome_nome=Concat("cognome", Value(" "), "nome"),
        nome_cognome=Concat("nome", Value(" "), "cognome"),
        _af_cognome=AccentFold("cognome"),
        _af_nome=AccentFold("nome"),
        _af_ragione=AccentFold("ragione_sociale"),
        _af_cf=AccentFold("codice_fiscale"),
        _af_piva=AccentFold("partita_iva"),
        _af_email=AccentFold("email"),
        _af_telefono=AccentFold("telefono"),
        _af_cellulare=AccentFold("cellulare"),
        _af_cognome_nome=AccentFold(Concat("cognome", Value(" "), "nome")),
        _af_nome_cognome=AccentFold(Concat("nome", Value(" "), "cognome")),
    )


def annotate_anagrafica_cognome_priority(queryset, query):
    """
    Ordina i match dando priorità al Cognome, poi al Nome.
    Rank più basso = migliore.
    """
    query = (query or "").strip()
    tokens = [fold_accents(part) for part in query.split() if part]
    tokens = [token for token in tokens if token]
    first = tokens[0] if tokens else ""
    second = tokens[1] if len(tokens) > 1 else ""

    whens = []
    if first and second:
        whens.extend(
            [
                When(
                    Q(_af_cognome__istartswith=first)
                    & (Q(_af_nome__istartswith=second) | Q(_af_nome__icontains=second)),
                    then=Value(0),
                ),
                When(
                    Q(_af_cognome__icontains=first) & Q(_af_nome__icontains=second),
                    then=Value(1),
                ),
                When(
                    Q(_af_nome__istartswith=first)
                    & (
                        Q(_af_cognome__istartswith=second)
                        | Q(_af_cognome__icontains=second)
                    ),
                    then=Value(5),
                ),
            ]
        )
    if first:
        whens.extend(
            [
                When(_af_cognome__istartswith=first, then=Value(2)),
                When(_af_cognome__icontains=first, then=Value(3)),
                When(_af_ragione__istartswith=first, then=Value(4)),
                When(_af_nome__istartswith=first, then=Value(6)),
                When(_af_nome__icontains=first, then=Value(7)),
            ]
        )

    return queryset.annotate(
        search_rank=Case(
            *whens,
            default=Value(9),
            output_field=IntegerField(),
        )
    )
