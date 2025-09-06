from django import forms
from django.core.exceptions import ValidationError
from .models import Zone, LocalisationContribuable
from django.contrib.gis.geos import GEOSGeometry

class ZoneForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = ['nom', 'responsable', 'active', 'geom']
        widgets = {
            'geom': forms.Textarea(attrs={
                'rows': 10,
                'cols': 80,
                'placeholder': 'Entrez les coordonnées GeoJSON du polygone...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].required = False
        self.fields['geom'].help_text = "Entrez les coordonnées GeoJSON du polygone de la zone"

    def clean_geom(self):
        """Accepter en entrée WKT (POLYGON(...)) ou GeoJSON et renvoyer un GEOSGeometry."""
        geom_val = self.cleaned_data.get('geom')
        if not geom_val:
            return None

        # Si c'est déjà un GEOSGeometry, rien à faire
        if hasattr(geom_val, 'geom_type'):
            return geom_val

        # Essayer de parser la chaîne (WKT ou GeoJSON)
        try:
            geom = GEOSGeometry(geom_val)
            # Forcer SRID 4326 si absent
            if not getattr(geom, 'srid', None):
                try:
                    geom.srid = 4326
                except Exception:
                    pass
            return geom
        except Exception:
            # Essayer en cas où l'entrée est un dict JSON
            import json
            try:
                obj = json.loads(geom_val)
                geom = GEOSGeometry(json.dumps(obj))
                if not getattr(geom, 'srid', None):
                    try:
                        geom.srid = 4326
                    except Exception:
                        pass
                return geom
            except Exception as e:
                raise ValidationError('Format de géométrie invalide. Utilisez WKT (POLYGON(...)) ou GeoJSON.')

class LocalisationContribuableForm(forms.ModelForm):
    class Meta:
        model = LocalisationContribuable
        fields = ['contribuable', 'zone', 'geom', 'adresse', 'precision', 'source', 'verifie']
        widgets = {
            'adresse': forms.TextInput(attrs={
                'placeholder': 'Adresse complète...',
                'class': 'form-control'
            }),
            'precision': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            # Le champ geom est un champ texte caché qui recevra le WKT écrit par le JS
            'geom': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Importer Contribuable dynamiquement pour éviter les imports circulaires
        from django.apps import apps
        Contribuable = apps.get_model('gestion_contribuables', 'Contribuable')

        # Exclure les contribuables déjà localisés, sauf celui en cours d'édition
        if self.instance and self.instance.pk:
            deja_localises = LocalisationContribuable.objects.exclude(pk=self.instance.pk).values_list('contribuable_id', flat=True)
        else:
            deja_localises = LocalisationContribuable.objects.values_list('contribuable_id', flat=True)
        self.fields['contribuable'].queryset = Contribuable.objects.exclude(id__in=deja_localises)

        self.fields['zone'].required = False
        self.fields['adresse'].help_text = "Adresse textuelle de la localisation"
        self.fields['precision'].help_text = "Niveau de précision de la localisation"
        self.fields['source'].help_text = "Comment cette localisation a été obtenue"
        self.fields['verifie'].help_text = "Cocher si la localisation a été vérifiée sur le terrain"

    def clean(self):
        cleaned_data = super().clean()
        geom = cleaned_data.get('geom')
        zone = cleaned_data.get('zone')

        # Validation de cohérence géométrie/zone
        if geom and zone and zone.geom:
            if not zone.geom.contains(geom):
                raise ValidationError(
                    "La position sélectionnée ne se trouve pas dans la zone choisie."
                )

        return cleaned_data

class RechercheZoneForm(forms.Form):
    """Formulaire de recherche avancée pour les zones"""
    nom = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom de la zone...',
            'class': 'form-control'
        })
    )
    responsable = forms.ModelChoiceField(
        queryset=None,  # Sera défini dans __init__
        required=False,
        empty_label="Tous les responsables",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    active = forms.BooleanField(
        required=False,
        initial=True,
        label="Zones actives uniquement"
    )

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['responsable'].queryset = User.objects.filter(
            zone__isnull=False
        ).distinct()