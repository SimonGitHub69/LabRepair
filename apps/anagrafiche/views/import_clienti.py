from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.anagrafiche.forms.import_clienti import ImportClientiCsvForm
from apps.anagrafiche.import_clienti import format_import_stats, import_clienti_csv


class ImportClientiCsvView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = "anagrafiche/import_clienti_csv.html"
    permission_required = "anagrafiche.import_clienti_csv"
    raise_exception = True

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": ImportClientiCsvForm()},
        )

    def post(self, request):
        form = ImportClientiCsvForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        dry_run = form.cleaned_data["dry_run"]
        update_existing = form.cleaned_data["update_existing"]
        uploaded = form.cleaned_data["csv_file"]

        try:
            stats = import_clienti_csv(
                uploaded,
                dry_run=dry_run,
                update_existing=update_existing,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, {"form": form})
        except Exception as exc:
            messages.error(request, f"Errore durante l'importazione: {exc}")
            return render(request, self.template_name, {"form": form})

        message = format_import_stats(stats, dry_run=dry_run)
        if dry_run:
            messages.info(request, message)
        else:
            messages.success(request, message)

        return redirect("anagrafiche:import_clienti_csv")
