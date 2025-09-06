from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.db.models import Count, Sum, F, Value, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.http import JsonResponse
import logging
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Paiement, Contribuable, HistoriqueModification
from geolocalisation.models import Zone, LocalisationContribuable
from django.apps import apps
from django.templatetags.static import static
from django import forms
from django.core.serializers import serialize
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.conf import settings
import json
from django.db.models import Sum
from django.db.models.functions import TruncMonth, Coalesce
from django.contrib.admin.actions import delete_selected

def _get_last_12_months_payments():
    now = timezone.now()
    # start candidate : 12 mois glissants (mois courant - 11)
    base_start = datetime(now.year, now.month, 1).date()
    def shift_month_date(d, months):
        m = d.month - 1 + months
        y = d.year + m // 12
        mm = m % 12 + 1
        return date(y, mm, 1)

    base_start = shift_month_date(base_start, -11)

    # clamp : ne pas afficher avant janvier 2025
    forced_start = date(2025, 1, 1)
    start = forced_start if forced_start > base_start else base_start

    qs = (
        Paiement.objects
        .filter(date_paiement__gte=start)
        .annotate(mois=TruncMonth('date_paiement'))
        .values('mois')
        .annotate(total=Coalesce(Sum('montant'), Value(0), output_field=DecimalField()))
        .order_by('mois')
    )
    # map mois -> montant
    month_map = {}
    for item in qs:
        m = item['mois']
        if hasattr(m, 'date'):
            m = m.date()
        key = datetime(m.year, m.month, 1).date()
        month_map[key] = int(item['total'])
    labels = []
    data = []
    # construire 12 mois à partir de start (ou moins si vous préférez)
    dt = start
    for _ in range(12):
        labels.append(dt.strftime('%b %Y'))
        data.append(month_map.get(dt, 0))
        dt = shift_month_date(dt, 1)
    return labels, data

def _first_field_name(model, candidates, default=None):
    names = {f.name for f in model._meta.get_fields() if hasattr(f, 'name')}
    for c in candidates:
        if c in names:
            return c
    return default

def _month_start(dt):
    return date(dt.year, dt.month, 1)

class CustomAdminSite(admin.AdminSite):
    site_header = "Mairie de Mbour"
    site_title = "Admin - RETAM"

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

    def get_app_list(self, request, app_label=None):
        return super().get_app_list(request, app_label)

    # Ajouter cette méthode pour permettre la suppression
    def has_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def index(self, request, extra_context=None):
        # Contexte de base
        # sécuriser la récupération de la liste d'applications (reverse peut échouer si certains admin ne sont pas enregistrés)
        try:
            app_list = self.get_app_list(request)
        except Exception as e:
            logging.getLogger(__name__).warning("get_app_list failed in admin.index: %s", e)
            app_list = []

        context = {
            **super().each_context(request),
            'title': self.index_title,
            'subtitle': None,
            'app_list': app_list,
            'available_apps': app_list,
        }
        
        # Statistiques
        stats = {
            'total_contribuables': Contribuable.objects.count(),
            'contribuables_actifs': Contribuable.objects.filter(actif=True).count(),
            'paiements_mois': Paiement.objects.filter(
                date_paiement__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('montant'))['total'] or 0,
            'retards': Paiement.objects.filter(date_paiement__gt=F('date_echeance')).count(),
            'show_stats_dashboard': True
        }

        # Données pour les graphiques
        paiements_par_mois = list(Paiement.objects.annotate(
            mois=TruncMonth('date_paiement')
        ).values('mois').annotate(
            total=Sum('montant')
        ).order_by('mois'))

        types_contribuables = list(Contribuable.objects.values(
            'type_contribuable'
        ).annotate(
            count=Count('id')
        ))

        # Statistiques zones (réelles)
        raw_counts = (
            LocalisationContribuable.objects
            .values('zone__nom')
            .annotate(count=Count('contribuable'))
            .order_by('-count')
        )
        zones_stats = [
            {'nom': item['zone__nom'] or 'Non spécifiée', 'count': item['count']}
            for item in raw_counts
        ]
        total_zones = Zone.objects.count()

        # Mise à jour du contexte
        context.update({
            'stats': stats,
            'paiements_data': json.dumps([{
                'mois': item['mois'].strftime('%Y-%m') if item['mois'] else None,
                'total': float(item['total']) if item['total'] else 0
            } for item in paiements_par_mois]),
            'types_data': json.dumps([{
                'type': item['type_contribuable'] or 'Non défini',
                'count': item['count']
            } for item in types_contribuables]),
            'zones_data': json.dumps([{
                'zone': item['nom'],
                'count': item['count']
            } for item in zones_stats]),
            'extra_js': [
                'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js',
                static('js/admin_dashboard_charts.js'),
                'https://unpkg.com/leaflet/dist/leaflet.js',
            ],
            'types_contribuables': types_contribuables,
            'zones_stats': list(zones_stats),
            'total_zones': total_zones,
        })

        if extra_context:
            context.update(extra_context)

        # Utilise un template qui vide les blocs usertools/nav-global/branding/breadcrumbs
        return TemplateResponse(request, 'admin/index.html', context)

# Instance de l'admin personnalisé
admin_site = CustomAdminSite(name='myadmin')

# Modèles de base
@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    pass

@admin.register(Group, site=admin_site)
class CustomGroupAdmin(GroupAdmin):
    pass

# Modèles personnalisés
class PaiementInlineForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['montant', 'taxe_redevance', 'date_echeance', 'date_paiement', 'mode_paiement']
        widgets = {
            'date_paiement': forms.TextInput(),  # <-- ceci désactive le calendrier !
        }

class PaiementInline(admin.TabularInline):
    model = Paiement
    form = PaiementInlineForm
    fields = ('montant', 'taxe_redevance', 'date_echeance', 'date_paiement', 'mode_paiement')
    readonly_fields = ('montant', 'taxe_redevance', 'date_echeance')
    extra = 1
    can_delete = False

@admin.register(Contribuable, site=admin_site)
class ContribuableAdmin(admin.ModelAdmin):
    list_display = (
        'nif', 'nom', 'type_contribuable', 'telephone', 
        'email', 'actif', 'total_paye_display', 'lien_paiements',
        'has_paiements_retard'
    )
    # Ajout du filtre Type de contribuable (et utile : actif)
    list_filter = ('type_contribuable', 'actif')
    search_fields = ('nif', 'nom', 'telephone', 'email', 'reference')
    readonly_fields = (
        'date_inscription', 'date_modification', 'total_paye', 
        'reference', 'lien_historique', 'voir_fiche_link'
    )
    fieldsets = (
        ('Informations générales', {
            'fields': ('nif', 'type_contribuable', 'nom', 'adresse', 'voir_fiche_link')
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'email')
        }),
        ('Statut et notifications', {
            'fields': ('actif', 'notifier_retards')
        }),
        ('Documents', {
            'fields': ('piece_identite',)
        }),
        ('Informations financières', {
            'fields': ('montant_a_payer', 'taxe_redevance', 'date_echeance', 'total_paye')
        }),
        ('Métadonnées', {
            'fields': ('reference', 'date_inscription', 'date_modification', 'lien_historique'),
            'classes': ('collapse',)
        })
    )
    # Utiliser l'action standard de suppression
    actions = ['generer_quittances', 'notifier_retards', 'delete_selected']
    inlines = [PaiementInline]

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def total_paye_display(self, obj):
        return f"{obj.total_paye:,} FCFA"
    total_paye_display.short_description = "Total payé"

    def has_paiements_retard(self, obj):
        return obj.a_des_retards
    has_paiements_retard.boolean = True
   
    def lien_paiements(self, obj):
        count = obj.paiements.count()
        url = reverse("admin:gestion_contribuables_paiement_changelist") + f"?contribuable__id__exact={obj.id}"
        return format_html('<a href="{}">{} Paiements</a>', url, count)
    lien_paiements.short_description = "Paiements"

    def lien_historique(self, obj):
        count = obj.historique.count()
        url = reverse("admin:gestion_contribuables_historiquemodification_changelist") + f"?contribuable__id__exact={obj.id}"
        return format_html('<a href="{}">{} Modifications</a>', url, count)
    lien_historique.short_description = "Historique"

    def generer_quittances(self, request, queryset):
        for contribuable in queryset:
            for paiement in contribuable.paiements.filter(quittance_generee=False):
                paiement.generer_quittance()
        self.message_user(request, f"Quittances générées pour {queryset.count()} contribuables")
    generer_quittances.short_description = "Générer les quittances manquantes"

    def notifier_retards(self, request, queryset):
        for contribuable in queryset.filter(notifier_retards=True):
            for paiement in contribuable.paiements_en_retard:
                paiement.notifier_retard()
        self.message_user(request, f"Notifications envoyées pour {queryset.count()} contribuables")
    notifier_retards.short_description = "Notifier les retards"

    def voir_fiche_link(self, obj):
        if obj.pk:
            url = reverse('gestion_contribuables:fiche_contribuable', args=[obj.pk])
            return format_html('<a class="button" href="{}" target="_blank">Voir la fiche</a>', url)
        return ""
    voir_fiche_link.short_description = "Voir la fiche"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['nif'].required = False  # Rendre le champ non obligatoire
        return form

    def save_model(self, request, obj, form, change):
        if not obj.nif or obj.nif.strip() == "":
            nom = (obj.nom or "XXX").upper().replace(" ", "")
            prefix = nom[:3] if len(nom) >= 3 else nom.ljust(3, "X")
            date_str = timezone.now().strftime("%Y%m%d")
            obj.nif = f"{prefix}{date_str}"
        if not change:  # Si c'est une création
            today = timezone.now().date()
            year = today.year
            month = today.month
            if month == 2:
                day = 28
            else:
                day = 30
            try:
                obj.date_echeance = today.replace(day=day)
            except ValueError:
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                obj.date_echeance = today.replace(day=last_day)
        super().save_model(request, obj, form, change)

    def get_changeform_initial_data(self, request):
        from calendar import monthrange
        today = timezone.now().date()
        year = today.year
        month = today.month
        # Si février, 28, sinon 30 (ou dernier jour du mois si pas de 30)
        if month == 2:
            day = 28
        else:
            day = 30
        try:
            date_echeance = today.replace(day=day)
        except ValueError:
            last_day = monthrange(year, month)[1]
            date_echeance = today.replace(day=last_day)
        initial = super().get_changeform_initial_data(request)
        initial['date_echeance'] = date_echeance
        return initial

    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        # S'assurer que delete_selected est disponible
        if 'delete_selected' not in actions:
            from django.contrib.admin.actions import delete_selected
            actions['delete_selected'] = delete_selected
        return actions

    def delete_selected(self, request, queryset):
        """Action personnalisée avec logs"""
        try:
            count = queryset.count()
            logging.info(f"Tentative de suppression de {count} contribuables")
            
            for obj in queryset:
                logging.info(f"Suppression du contribuable: {obj.nom} (ID: {obj.id})")
                obj.delete()
                
            self.message_user(request, f"{count} contribuable(s) supprimé(s) avec succès.")
            logging.info(f"Suppression réussie de {count} contribuables")
            
        except Exception as e:
            logging.error(f"Erreur lors de la suppression: {str(e)}")
            self.message_user(request, f"Erreur lors de la suppression: {str(e)}", level='ERROR')
    
    delete_selected.short_description = "Supprimer les contribuables sélectionnés"

class PaiementAdminForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = '__all__'
        widgets = {
            'date_paiement': forms.DateInput(attrs={'type': 'date'}),
        }

# ---- Filtre personnalisé pour le type de contribuable (déclaré une seule fois) ----
class TypeContribuableFilter(admin.SimpleListFilter):
    title = "Type contribuable"
    parameter_name = "type_contribuable"

    def lookups(self, request, model_admin):
        qs = Contribuable.objects.order_by('type_contribuable').values_list('type_contribuable', flat=True).distinct()
        return [(v, v) for v in qs if v is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(contribuable__type_contribuable=self.value())
        return queryset

@admin.register(Paiement, site=admin_site)
class PaiementAdmin(admin.ModelAdmin):
    form = PaiementAdminForm
    fields = (
        'contribuable', 'montant', 'taxe_redevance', 'date_echeance',
        'date_paiement', 'mode_paiement', 'agent', 'notes',
        'reference', 'fichier_quittance'
    )
    readonly_fields = (
        'montant', 'taxe_redevance', 'reference', 'fichier_quittance'
    )
    list_display = (
        'contribuable',
        'get_type_contribuable',
        'get_reference_contribuable',
        'taxe_redevance',
        'montant',
        'date_paiement',
        'mode_paiement',
        'imprimer_quittance'
    )
    search_fields = ('reference', 'contribuable__nom', 'contribuable__nif')
    # Permet de filtrer par mode, taxe/redevance et aussi par type du contribuable lié
    list_filter = ('mode_paiement', 'taxe_redevance', TypeContribuableFilter)

    def get_type_contribuable(self, obj):
        return obj.contribuable.type_contribuable if obj.contribuable else "-"
    get_type_contribuable.short_description = "Type de contribuable"

    def get_reference_contribuable(self, obj):
        return obj.contribuable.reference if obj.contribuable else "-"
    get_reference_contribuable.short_description = "Référence contribuable"

    def get_readonly_fields(self, request, obj=None):
        return ['montant', 'taxe_redevance', 'date_echeance'] + list(self.readonly_fields)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        contribuable_id = request.GET.get('contribuable')
        if contribuable_id:
            try:
                c = Contribuable.objects.get(pk=contribuable_id)
                initial.update({
                    'contribuable': c.pk,
                    'montant': c.montant_a_payer,
                    'taxe_redevance': getattr(c, 'taxe_redevance', None),
                    'date_echeance': c.date_echeance
                })
            except Contribuable.DoesNotExist:
                pass
        return initial

    def save_model(self, request, obj, form, change):
        if obj.contribuable:
            if obj.montant is None:
                obj.montant = obj.contribuable.montant_a_payer
            if obj.taxe_redevance is None and hasattr(obj.contribuable, 'taxe_redevance'):
                obj.taxe_redevance = obj.contribuable.taxe_redevance
            if obj.date_echeance is None:
                obj.date_echeance = obj.contribuable.date_echeance
        if not obj.agent:
            obj.agent = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'view-quittance/<int:pk>/',
                self.admin_site.admin_view(self.view_quittance_view),
                name='gestion_contribuables_paiement_view_quittance'
            ),
            path(
                'send-whatsapp/<int:pk>/',
                self.admin_site.admin_view(self.send_quittance_view),
                name='gestion_contribuables_paiement_send_whatsapp'
            ),
        ]
        return custom + urls

    def imprimer_quittance(self, obj):
        """Ouvre la preview (Imprimer + Partager)."""
        if obj and obj.pk:
            url = reverse('admin:gestion_contribuables_paiement_view_quittance', args=[obj.pk])
            return format_html('<a class="button" href="{}" target="_blank">Partager / Imprimer</a>', url)
        return "-"
    imprimer_quittance.short_description = "Imprimer quittance"

    def partager_quittance(self, obj):
        """Raccourci vers la même preview (utiliser le bouton 'Partager' après impression)."""
        if obj and obj.pk:
            url = reverse('admin:gestion_contribuables_paiement_view_quittance', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" target="_blank" style="background:#25D366;color:#fff;">Partager la quittance</a>',
                url
            )
        return "-"
    partager_quittance.short_description = "Partager quittance"

    @method_decorator(ensure_csrf_cookie)
    def view_quittance_view(self, request, pk, *args, **kwargs):
        """Vue de prévisualisation : iframe PDF + boutons Ouvrir/Imprimer et Partager (serveur-side)."""
        if not self.has_change_permission(request):
            self.message_user(request, "Permission refusée.", level=admin.messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', '..'))

        obj = get_object_or_404(Paiement, pk=pk)

        # génération PDF si nécessaire (si vous avez _ensure_quittance_pdf)
        try:
            ok_pdf = True
            if '_ensure_quittance_pdf' in globals():
                ok_pdf, pdf_res = _ensure_quittance_pdf(obj)
                if not ok_pdf:
                    self.message_user(request, f"Erreur génération PDF: {pdf_res}", level=admin.messages.ERROR)
                    return redirect(request.META.get('HTTP_REFERER', '..'))
        except Exception as e:
            logging.getLogger(__name__).exception("Erreur génération PDF: %s", e)
            self.message_user(request, "Erreur génération PDF", level=admin.messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', '..'))

        # résoudre URL absolue du fichier
        file_url = getattr(obj, 'fichier_quittance', None)
        if not file_url or not getattr(file_url, 'url', None):
            self.message_user(request, "Quittance introuvable.", level=admin.messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', '..'))
        file_url = file_url.url
        if not file_url.startswith('http'):
            site = getattr(settings, 'SITE_URL', '')
            file_url = site.rstrip('/') + file_url

        send_url = reverse('admin:gestion_contribuables_paiement_send_whatsapp', args=[obj.pk])
        context = {
            **self.admin_site.each_context(request),
            'title': 'Prévisualiser quittance',
            'file_url': file_url,
            'send_url': send_url,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/quittance_preview.html', context)

    def send_quittance_view(self, request, pk, *args, **kwargs):
        """Vue admin : envoie la quittance via WhatsApp. Toujours renvoie JSON en cas d'erreur."""
        try:
            # garde‑fou méthode
            if request.method != 'POST':
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'msg': 'Méthode non autorisée'}, status=405)
                self.message_user(request, "Méthode non autorisée.", level=admin.messages.ERROR)
                return redirect(request.META.get('HTTP_REFERER', '..'))

            if not self.has_change_permission(request):
                return JsonResponse({'ok': False, 'msg': 'Permission refusée.'}, status=403)

            obj = get_object_or_404(Paiement, pk=pk)

            # génération / vérifications (conserver votre logique existante)
            if '_ensure_quittance_pdf' in globals():
                ok_pdf, pdf_res = _ensure_quittance_pdf(obj)
                if not ok_pdf:
                    return JsonResponse({'ok': False, 'msg': f"Erreur génération PDF: {pdf_res}"}, status=500)

            file_field = obj.fichier_quittance
            name = getattr(file_field, 'name', None)
            if not name or not default_storage.exists(name):
                return JsonResponse({'ok': False, 'msg': f"Fichier introuvable ({name})"}, status=500)

            # appel à la fonction d'envoi existante
            if hasattr(self, '_send_whatsapp_api'):
                ok_send, msg = self._send_whatsapp_api(obj)
                if ok_send:
                    return JsonResponse({'ok': True, 'msg': 'Quittance envoyée via WhatsApp.'})
                logging.getLogger(__name__).warning("WhatsApp send failed for %s: %s", pk, msg)
                return JsonResponse({'ok': False, 'msg': f"Envoi échoué: {msg}"}, status=500)

            return JsonResponse({'ok': False, 'msg': "Fonction d'envoi non implémentée."}, status=500)

        except Exception:
            logging.getLogger(__name__).exception("send_quittance_view exception for pk=%s", pk)
            # ne pas renvoyer la stack au client en prod, message générique suffira
            return JsonResponse({'ok': False, 'msg': 'Erreur interne du serveur.'}, status=500)

    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' not in actions:
            actions['delete_selected'] = self.get_action('delete_selected')
        return actions

@admin.register(HistoriqueModification, site=admin_site)
class HistoriqueModificationAdmin(admin.ModelAdmin):
    list_display = (
        'contribuable_link', 'action', 'date_modification', 
        'utilisateur_display', 'champs_modifies'
    )
    list_filter = ('action', 'utilisateur')
    search_fields = ('contribuable__nif', 'contribuable__nom', 'utilisateur__username')
    readonly_fields = (
        'contribuable_link', 'action', 'date_modification', 
        'utilisateur_display', 'details_display'
    )
    date_hierarchy = 'date_modification'

    def contribuable_link(self, obj):
        url = reverse("admin:gestion_contribuables_contribuable_change", args=[obj.contribuable.id])
        return format_html('<a href="{}">{}</a>', url, obj.contribuable.nom)
    contribuable_link.short_description = "Contribuable"

    def utilisateur_display(self, obj):
        return obj.utilisateur.username if obj.utilisateur else "Système"
    utilisateur_display.short_description = "Utilisateur"

    def details_display(self, obj):
        details = obj.get_details()
        if 'champs_modifies' in details and details['champs_modifies']:
            return format_html("Modification des champs: <strong>{}</strong>", ", ".join(details['champs_modifies']))
        return "Création"
    details_display.short_description = "Détails"

    def champs_modifies(self, obj):
        details = obj.get_details()
        return ", ".join(details.get('champs_modifies', [])) if details.get('champs_modifies') else "Création"
    champs_modifies.short_description = "Champs modifiés"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' not in actions:
            actions['delete_selected'] = self.get_action('delete_selected')
        return actions

# Remplacement du site admin par défaut
admin.site = admin_site
admin.sites.site = admin_site

# --- Injection d'un wrapper propre pour afficher la somme des paiements sur 30 jours ---
_orig_admin_index = admin.site.index

def _index_with_30d_stats(request, extra_context=None):
    extra_context = extra_context or {}
    now = timezone.now()
    since = now - timedelta(days=30)

    # total 30 jours
    total_30j = Paiement.objects.filter(date_paiement__gte=since).aggregate(
        total=Coalesce(Sum('montant'), Value(0), output_field=DecimalField())
    )['total'] or 0

    # total global
    total_global = Paiement.objects.aggregate(
        total=Coalesce(Sum('montant'), Value(0), output_field=DecimalField())
    )['total'] or 0

    # nombre de contribuables
    total_contribuables = Contribuable.objects.count()

    # --- statistiques mensuelles (derniers 12 mois) ---
    since_year = now - timedelta(days=365)
    qs = (
        Paiement.objects
        .filter(date_paiement__gte=since_year)
        .annotate(month=TruncMonth('date_paiement'))
        .values('month')
        .annotate(total=Coalesce(Sum('montant'), Value(0), output_field=DecimalField()))
        .order_by('month')
    )

    # normaliser résultats en dict {date(YYYY,MM,1): total}
    month_map = {}
    for item in qs:
        m = item['month']
        if hasattr(m, 'date'):
            m = m.date()
        month_key = datetime(m.year, m.month, 1).date()
        month_map[month_key] = int(item['total'])

    # start candidate (12 mois glissants)
    base_start = datetime(now.year, now.month, 1).date()
    def shift_month_date(d, months):
        m = d.month - 1 + months
        y = d.year + m // 12
        mm = m % 12 + 1
        return date(y, mm, 1)
    base_start = shift_month_date(base_start, -11)

    # clamp to jan 2025
    forced_start = date(2025, 1, 1)
    start = forced_start if forced_start > base_start else base_start

    # construire labels/data à partir de start (12 mois)
    labels = []
    data = []
    dt = start
    for _ in range(12):
        labels.append(dt.strftime('%b %Y'))
        data.append(month_map.get(dt, 0))
        dt = shift_month_date(dt, 1)

    stats = extra_context.get('stats', {})
    stats.update({
        'show_stats_dashboard': True,
        'paiements_mois': int(total_30j),
        'paiements_total': int(total_global),
        'total_contribuables': int(total_contribuables),
        'months_labels_json': json.dumps(labels),
        'months_data_json': json.dumps(data),
    })
    extra_context['stats'] = stats
    return _orig_admin_index(request, extra_context=extra_context)

admin.site.index = _index_with_30d_stats

# Dans ContribuableAdmin : override changelist_view
try:
    # si ContribuableAdmin existe plus bas, on insère la méthode dynamiquement
    ContribuableAdmin  # type: ignore
except NameError:
    pass
else:
    def contrib_changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        labels, data = _get_last_12_months_payments()
        extra_context['paiements_months_labels_json'] = json.dumps(labels)
        extra_context['paiements_months_data_json'] = json.dumps(data)
        return super(self.__class__, self).changelist_view(request, extra_context=extra_context)
    ContribuableAdmin.changelist_view = contrib_changelist_view  # type: ignore

# Dans PaiementAdmin : override changelist_view
try:
    PaiementAdmin  # type: ignore
except NameError:
    pass
else:
    def paiement_changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        labels, data = _get_last_12_months_payments()
        extra_context['paiements_months_labels_json'] = json.dumps(labels)
        extra_context['paiements_months_data_json'] = json.dumps(data)
        return super(self.__class__, self).changelist_view(request, extra_context=extra_context)
    PaiementAdmin.changelist_view = paiement_changelist_view  # type: ignore