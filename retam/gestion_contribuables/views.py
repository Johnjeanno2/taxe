# gestion_contribuables/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponseForbidden, Http404, HttpResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Count, Exists, OuterRef, F, Avg, Q
from django.core import serializers
from django.core.serializers import serialize
from urllib.parse import quote_plus
from io import BytesIO
import json
import base64
import qrcode
from .models import Contribuable, Paiement, HistoriqueModification
from .forms import ContribuableForm, PaiementForm, ContribuableSearchForm
from geolocalisation.models import Zone, LocalisationContribuable
from django.utils.dateparse import parse_date
from datetime import timedelta
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.core.files.storage import default_storage

class PaiementCreateView(LoginRequiredMixin, CreateView):
    model = Paiement
    form_class = PaiementForm
    template_name = 'gestion_contribuables/paiement_form.html'
    success_url = reverse_lazy('contribuable_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Paiement enregistré avec succès")
        return response

def generate_qr_code(data):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@staff_member_required
def zones_geojson(request):
    """Endpoint GeoJSON pour les zones"""
    try:
        zones = Zone.objects.all()
        geojson = serialize('geojson', zones,
                          geometry_field='geom',
                          fields=('nom', 'couleur'))
        return JsonResponse(json.loads(geojson), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def dashboard_stats(request):
    """Endpoint AJAX pour les stats filtrées"""
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            filters = {
                'debut': request.POST.get('debut'),
                'fin': request.POST.get('fin'),
                'type': request.POST.get('type'),
                'zone': request.POST.get('zone')
            }

            # QuerySets de base
            contribuables = Contribuable.objects.all()
            paiements = Paiement.objects.all()  # Ajout de cette ligne
           

            # Appliquer les filtres
            if filters['type'] and filters['type'] != "all":
                contribuables = contribuables.filter(type_contribuable=filters['type'])
                paiements = paiements.filter(contribuable__type_contribuable=filters['type'])
            if filters['zone'] and filters['zone'] != "all":
                contribuables = contribuables.filter(localisation__zone__id=filters['zone'])
                paiements = paiements.filter(contribuable__localisation__zone__id=filters['zone'])
            if filters['debut']:
                contribuables = contribuables.filter(date_creation__gte=filters['debut'])
                paiements = paiements.filter(date_paiement__gte=filters['debut'])
            if filters['fin']:
                contribuables = contribuables.filter(date_creation__lte=filters['fin'])
                paiements = paiements.filter(date_paiement__lte=filters['fin'])

            # Calcul des statistiques
            paiements_a_temps = paiements.filter(date_paiement__lte=F('date_echeance')).count()
            paiements_en_retard = paiements.filter(date_paiement__gt=F('date_echeance')).count()
            total_paiements = paiements.count()

            # Récupérer les 12 derniers mois (du plus ancien au plus récent)
            now = timezone.now()
            months = []
            for i in range(11, -1, -1):
                month = (now - relativedelta(months=i)).replace(day=1)
                months.append(month)

            # Paiements groupés par mois
            paiements = (
                paiements
                .annotate(mois=TruncMonth('date_paiement'))
                .values('mois')
                .annotate(montant=Sum('montant'), count=Count('id'))
            )

            # Indexer par mois
            paiements_dict = {p['mois'].strftime('%Y-%m'): p for p in paiements if p['mois']}

            # Générer la liste complète
            montant_par_mois = []
            for month in months:
                key = month.strftime('%Y-%m')
                p = paiements_dict.get(key)
                montant_par_mois.append({
                    'mois': month.strftime('%Y-%m-01'),
                    'montant': p['montant'] if p else 0,
                    'count': p['count'] if p else 0,
                })

            stats = {
                "total_contribuables": contribuables.count(),
                "contribuables_actifs": contribuables.filter(actif=True).count(),
                "paiements_mois": paiements.filter(
                    date_paiement__gte=timezone.now() - timedelta(days=30)
                ).aggregate(total=Sum('montant'))['total'] or 0,
                "retards": paiements.filter(
                    date_echeance__lt=timezone.now(),
                    date_paiement__isnull=True
                ).count(),
                "taux_recouvrement": round(paiements_a_temps / total_paiements * 100) if total_paiements > 0 else 0,
                "paiements_a_temps": paiements_a_temps,
                "paiements_en_retard": paiements_en_retard,
                "montant_moyen": paiements.aggregate(avg=Avg('montant'))['avg'] or 0,
                "montants_par_mois": montant_par_mois,
                "success": True
            }
            return JsonResponse(stats)

        except Exception as e:
            return JsonResponse({"error": str(e), "success": False}, status=400)

    return JsonResponse({"error": "Requête invalide"}, status=405)

@staff_member_required
def admin_dashboard(request):
    """Vue simplifiée du tableau de bord admin sans filtres"""
    # QuerySets de base - on garde les 12 derniers mois par défaut
    date_debut = timezone.now() - relativedelta(months=11)
    paiements = Paiement.objects.filter(date_paiement__gte=date_debut)

    # Regrouper par mois
    paiements_par_mois = (
        paiements
        .annotate(mois=TruncMonth('date_paiement'))
        .values('mois')
        .annotate(montant=Sum('montant'), count=Count('id'))
        .order_by('mois')
    )

    # Générer la liste des 12 derniers mois
    months = []
    now = timezone.now()
    for i in range(11, -1, -1):
        month = (now - relativedelta(months=i)).replace(day=1)
        months.append(month)

    # Créer un dict pour accès rapide
    paiements_dict = {p['mois'].strftime('%Y-%m'): p for p in paiements_par_mois if p['mois']}

    montant_par_mois = []
    for month in months:
        key = month.strftime('%Y-%m')
        p = paiements_dict.get(key)
        montant_par_mois.append({
            'mois': month.strftime('%B %Y'),
            'montant': p['montant'] if p else 0,
            'count': p['count'] if p else 0,
        })

    context = {
        'montant_par_mois': montant_par_mois,
    }
    return render(request, "admin/index.html", context)

class ContribuableListView(LoginRequiredMixin, ListView):
    model = Contribuable
    template_name = 'gestion_contribuables/contribuable_list.html'
    paginate_by = 25
    context_object_name = 'contribuables'

    def get_queryset(self):
        queryset = super().get_queryset()
        form = ContribuableSearchForm(self.request.GET)
        
        if form.is_valid():
            if form.cleaned_data.get('q'):
                queryset = queryset.filter(
                    Q(nom__icontains=form.cleaned_data['q']) |
                    Q(nif__icontains=form.cleaned_data['q'])
                )
            if form.cleaned_data.get('actif_only'):
                queryset = queryset.filter(actif=True)
            if form.cleaned_data.get('en_retard'):
                queryset = queryset.annotate(
                    a_retard=Exists(
                        Paiement.objects.filter(
                            contribuable=OuterRef('pk'),
                            date_paiement__gt=F('date_echeance')
                        )
                    )
                ).filter(a_retard=True)
        
        return queryset.prefetch_related('paiements')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ContribuableSearchForm(self.request.GET)
        context['stats'] = self.calculate_stats()
        return context

    def calculate_stats(self):
        queryset = self.get_queryset()
        return {
            'total': queryset.count(),
            'actifs': queryset.filter(actif=True).count(),
            'en_retard': queryset.annotate(
                a_retard=Exists(
                    Paiement.objects.filter(
                        contribuable=OuterRef('pk'),
                        date_paiement__gt=F('date_echeance')
                    )
                )
            ).filter(a_retard=True).count()
        }

class ContribuableCreateView(LoginRequiredMixin, CreateView):
    model = Contribuable
    form_class = ContribuableForm
    template_name = 'gestion_contribuables/contribuable_form.html'
    success_url = reverse_lazy('contribuable_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Contribuable {self.object.nom} créé avec succès")
        return response

class ContribuableDetailView(LoginRequiredMixin, DetailView):
    model = Contribuable
    template_name = 'gestion_contribuables/contribuable_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paiements = self.object.paiements.all().order_by('-date_paiement')

        context['stats'] = {
            'total_paiements': paiements.count(),
            'montant_total': float(paiements.aggregate(total=Sum('montant'))['total'] or 0),
            'retards': paiements.filter(date_paiement__gt=F('date_echeance')).count(),
            'dernier_paiement': paiements.first()
        }

        paiements_data = list(paiements.values('date_paiement', 'montant').order_by('date_paiement'))
        context['paiements_chart'] = {
            'labels': json.dumps([p['date_paiement'].strftime("%Y-%m-%d") for p in paiements_data]),
            'data': json.dumps([float(p['montant']) for p in paiements_data])
        }

        context['paiements'] = paiements
        return context

class ContribuableUpdateView(LoginRequiredMixin, UpdateView):
    model = Contribuable
    form_class = ContribuableForm
    template_name = 'gestion_contribuables/contribuable_form.html'

    def get_success_url(self):
        return reverse('contribuable_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Contribuable {self.object.nom} mis à jour")
        return response

class ContribuableDeleteView(LoginRequiredMixin, DeleteView):
    model = Contribuable
    template_name = 'gestion_contribuables/contribuable_confirm_delete.html'
    success_url = reverse_lazy('contribuable_list')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Contribuable {self.object.nom} supprimé")
        return response

@staff_member_required
def fiche_contribuable(request, pk):
    contribuable = get_object_or_404(Contribuable, pk=pk)
    paiements = Paiement.objects.filter(contribuable=contribuable).order_by('-date_paiement')

    stats = {
        'total_paiements': paiements.count(),
        'montant_total': paiements.aggregate(total=Sum('montant'))['total'] or 0,
        'moyenne_mensuelle': paiements.filter(
            date_paiement__gte=timezone.now() - timedelta(days=365))
            .aggregate(moyenne=Sum('montant')/12)['moyenne'] or 0,
    }

    return render(request, "gestion_contribuables/fiche_contribuable.html", {
        "contribuable": contribuable,
        "paiements": paiements,
        "stats": stats
    })

@staff_member_required
def quittance_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, pk=paiement_id)

    # Récupère l'URL publique du fichier PDF (champ FileField : fichier_quittance)
    file_url = ''
    file_field = getattr(paiement, 'fichier_quittance', None)
    if file_field:
        try:
            # si storage fournit .url utilisable
            rel = file_field.url
            file_url = request.build_absolute_uri(rel)
        except Exception:
            # fallback : construire via default_storage
            name = getattr(file_field, 'name', '')
            try:
                rel = default_storage.url(name)
                file_url = request.build_absolute_uri(rel)
            except Exception:
                file_url = ''

    # Construire le lien WhatsApp (wa.me) avec message pré‑rempli
    msg = f"Quittance paiement {getattr(paiement, 'reference', paiement.pk)} : {file_url}"
    whatsapp_link_url = "https://wa.me/?text=" + quote_plus(msg)

    return render(request, "quittance_template.html", {
        "paiement": paiement,
        "file_url": file_url,
        "whatsapp_link_url": whatsapp_link_url,
    })

@staff_member_required
def historique_contribuable(request, pk):
    """Vue de l'historique d'un contribuable"""
    contribuable = get_object_or_404(Contribuable, pk=pk)
    historiques = HistoriqueModification.objects.filter(contribuable=contribuable).order_by('-date_modification')

    for h in historiques:
        try:
            h.details_dict = json.loads(h.details)
        except Exception:
            h.details_dict = {}

    return render(request, "gestion_contribuables/historique_contribuable.html", {
        "contribuable": contribuable,
        "historiques": historiques
    })

from django.http import JsonResponse
from django.db.models import Count

@staff_member_required
def repartition_stats(request):
    # Répartition par type
    types = list(
        Contribuable.objects.values('type_contribuable')
        .annotate(count=Count('id'))
    )
    # Répartition par zone
    zones = list(
        Contribuable.objects.values('localisationcontribuable__zone__nom')
        .annotate(count=Count('id'))
    )
    return JsonResponse({
        "types": types,
        "zones": zones,
    })

@staff_member_required
def stats_contribuables(request):
    """Stats détaillées sur les contribuables"""
    date_debut = timezone.now() - timedelta(days=365)
    
    stats = {
        "total_contribuables": Contribuable.objects.count(),
        "contribuables_actifs": Contribuable.objects.filter(actif=True).count(),
        "contribuables_inactifs": Contribuable.objects.filter(actif=False).count(),
        "paiements_totaux": Paiement.objects.aggregate(Sum('montant'))['montant__sum'] or 0,
        "paiements_a_temps": Paiement.objects.filter(date_paiement__lte=F('date_echeance')).count(),
        "paiements_en_retard": Paiement.objects.filter(date_paiement__gt=F('date_echeance')).count(),
        "taux_recouvrement": round(
            Paiement.objects.filter(date_paiement__lte=F('date_echeance')).count() /
            Paiement.objects.count() * 100
        ) if Paiement.objects.count() > 0 else 0,
        "montant_moyen_paiement": Paiement.objects.aggregate(avg=Avg('montant'))['avg'] or 0,
        "montants_par_mois": list(
            Paiement.objects
            .annotate(mois=TruncMonth('date_paiement'))
            .values('mois')
            .annotate(montant=Sum('montant'), count=Count('id'))
            .order_by('mois')
        ),
    }

    return JsonResponse(stats)

def serve_quittance_signed(request):
    signer = TimestampSigner()
    token_b64 = request.GET.get('token', '')
    if not token_b64:
        return HttpResponseForbidden("Token manquant")
    try:
        token = base64.urlsafe_b64decode(token_b64.encode()).decode()
    except Exception:
        return HttpResponseForbidden("Token invalide")
    try:
        name = signer.unsign(token, max_age=86400)
    except SignatureExpired:
        return HttpResponseForbidden("Lien expiré")
    except BadSignature:
        return HttpResponseForbidden("Signature invalide")

    try:
        f = default_storage.open(name, 'rb')
    except Exception:
        raise Http404("Fichier introuvable")

    resp = FileResponse(f, content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="quittance.pdf"'
    return resp

import base64
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from .models import Paiement
from django.utils import timezone
from django.db.models import Sum

def serve_quittance_html(request):
    """
    Render the HTML quittance for a signed paiement pk.
    public URL: /s/quittance/html/?token=<base64(token)>
    token = signer.sign(str(paiement.pk))
    """
    signer = TimestampSigner()
    token_b64 = request.GET.get('token', '')
    if not token_b64:
        return HttpResponseForbidden("Token manquant")
    try:
        token = base64.urlsafe_b64decode(token_b64.encode()).decode()
    except Exception:
        return HttpResponseForbidden("Token invalide")
    try:
        pk_str = signer.unsign(token, max_age=86400)
    except SignatureExpired:
        return HttpResponseForbidden("Lien expiré")
    except BadSignature:
        return HttpResponseForbidden("Signature invalide")

    try:
        pk = int(pk_str)
    except Exception:
        return HttpResponseForbidden("Token invalide")

    paiement = get_object_or_404(Paiement, pk=pk)
    contribuable = paiement.contribuable

    total_paye = Paiement.objects.filter(contribuable=contribuable).aggregate(total=Sum('montant'))['total'] or 0

    # QR / autres context vars si tu les utilises (ici on laisse vide si tu n'as pas de génération)
    qr_base64 = getattr(paiement, 'qr_base64', None)

    context = {
        'paiement': paiement,
        'contribuable': contribuable,
        'total_paye': total_paye,
        'date_emission': timezone.now().date(),
        'qr_base64': qr_base64,
        # file_url peut pointer vers PDF signé si tu veux inclure aussi le PDF link
        'file_url': request.build_absolute_uri(request.path)  # placeholder
    }
    return render(request, "quittance_template.html", context)

import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Paiement, Contribuable  # adapte selon ton modèle

@csrf_exempt
@require_POST
def api_offline_sync(request):
    """
    Reçoit un JSON représentant un paiement (ou un lot) envoyé en offline.
    Format attendu: either { ...paiement... } or [ {...}, {...} ]
    Retourne 200 si ok.
    ATTENTION: validation/sécurité minimale — améliorer en prod.
    """
    try:
        data = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest('JSON invalide')

    items = data if isinstance(data, list) else [data]
    created = 0
    for it in items:
        try:
            # exemple minimal : chercher contribuable par nif ou créer un contribuable minimal
            contrib_data = it.get('contribuable') or {}
            nif = contrib_data.get('nif')
            if nif:
                contribuable, _ = Contribuable.objects.get_or_create(nif=nif, defaults={
                    'nom': contrib_data.get('nom', 'Offline user'),
                    'telephone': contrib_data.get('telephone', '')
                })
            else:
                contribuable = None

            # map fields selon ton modèle Paiement
            Paiement.objects.create(
                contribuable=contribuable,
                montant=it.get('montant', 0),
                reference=it.get('reference', ''),
                date_paiement=it.get('date_paiement', None),
                # ajoute/ajuste selon ton modèle
            )
            created += 1
        except Exception as e:
            # log et continuer
            import logging
            logging.exception("Erreur création paiement offline: %s", e)
            continue

    return JsonResponse({'créés': created})

def api_offline_sync_heartbeat(request):
    return HttpResponse(status=204)