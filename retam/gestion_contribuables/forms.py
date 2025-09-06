from django import forms
from django.core.exceptions import ValidationError
from .models import Contribuable, Paiement
from django.utils import timezone

class ContribuableForm(forms.ModelForm):
    class Meta:
        model = Contribuable
        fields = [
            'nif', 'type_contribuable', 'nom', 'adresse', 'telephone', 'email',
            'actif', 'notifier_retards', 'piece_identite',
            'montant_a_payer', 'date_echeance'  # <-- Ajoute ces champs
        ]
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'date_echeance': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean_nif(self):
        nif = self.cleaned_data['nif']
        if Contribuable.objects.filter(nif=nif).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ce NIF est déjà utilisé par un autre contribuable")
        return nif

class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = [
            'contribuable', 'montant', 'taxe_redevance', 'date_paiement', 'date_echeance',
            'mode_paiement', 'agent', 'notes'
        ]
        widgets = {
            'date_paiement': forms.DateInput(attrs={'type': 'date'}),
            'date_echeance': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les champs obligatoires
        self.fields['contribuable'].required = True
        self.fields['date_paiement'].required = True
        self.fields['mode_paiement'].required = True

        # Préremplir les champs depuis le contribuable si déjà sélectionné
        if 'initial' in kwargs and kwargs['initial'].get('contribuable'):
            contribuable_id = kwargs['initial']['contribuable']
            try:
                c = Contribuable.objects.get(pk=contribuable_id)
                self.fields['montant'].initial = c.montant_a_payer
                self.fields['taxe_redevance'].initial = getattr(c, 'taxe_redevance', None)
                self.fields['date_echeance'].initial = c.date_echeance
            except Contribuable.DoesNotExist:
                pass

class ContribuableSearchForm(forms.Form):
    q = forms.CharField(label='Recherche', required=False)
    actif_only = forms.BooleanField(
        label='Contribuables actifs seulement', 
        required=False,
        initial=True
    )
    en_retard = forms.BooleanField(
        label='Avec retards de paiement', 
        required=False
    )