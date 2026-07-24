from apps.pratiche.models import PraticaFoto


def save_pratica_foto_uploads(request, pratica, field_name="foto_pratica"):
    saved = []
    for uploaded in request.FILES.getlist(field_name):
        foto = PraticaFoto.objects.create(
            pratica=pratica,
            immagine=uploaded,
            created_by=request.user,
            updated_by=request.user,
        )
        saved.append(foto)
    return saved


def delete_pratica_foto_ids(request, pratica):
    ids = [value for value in request.POST.getlist("foto_elimina") if value.strip()]
    if not ids:
        return 0

    deleted = 0
    for foto in pratica.foto.filter(pk__in=ids, is_active=True):
        foto.soft_delete(user=request.user)
        deleted += 1
    return deleted
