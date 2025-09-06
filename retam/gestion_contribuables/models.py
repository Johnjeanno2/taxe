from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import uuid
from django.db.models import Sum, F, Count
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import qrcode
import base64
from io import BytesIO
import os
from weasyprint import HTML
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta

User = get_user_model()

class CustomAdminSite(models.Model):
    """Ce modèle n'est pas utilisé par Django, il faut hériter de admin.AdminSite dans admin.py"""
    class Meta:
        abstract = True

# Si tu veux vraiment un CustomAdminSite, place-le dans admin.py et hérite de admin.AdminSite

TYPE_CONTRIBUABLE_CHOICES = [
    ('physique', 'Personne physique'),
    ('morale', 'Personne morale'),
]

class Contribuable(models.Model):
    id = models.AutoField(primary_key=True, editable=False, verbose_name="ID")
    nif = models.CharField(
        max_length=20,
        unique=True,
        blank=True,  # Permet une valeur vide
        null=True,   # Permet NULL en base de données
        validators=[RegexValidator(r'^[0-9A-Z]+$', 'NIF invalide')],
        verbose_name="Numéro d'identification fiscale",
        error_messages={
            'unique': "Ce NIF est déjà utilisé par un autre contribuable"
        }
    )
    type_contribuable = models.CharField(choices=TYPE_CONTRIBUABLE_CHOICES)
    nom = models.CharField(max_length=200)
    adresse = models.TextField()
    telephone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?[\d\s]{8,20}$', 'Numéro de téléphone invalide')]
    )
    email = models.EmailField(blank=True, null=True)
    date_inscription = models.DateField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)
    notifier_retards = models.BooleanField(
        default=True,
        verbose_name="Notifier les retards de paiement"
    )
    piece_identite = models.FileField(
        upload_to='contribuables/identites/',
        blank=True, 
        null=True,
        verbose_name="Pièce d'identité"
    )
    reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        verbose_name="Référence contribuable",
        error_messages={
            'unique': "Cette référence existe déjà"
        }
    )
    
    total_paye = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
        verbose_name="Total payé"
    )
    montant_a_payer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant net à payer"
    )
    date_echeance = models.DateField(
        verbose_name="Date d'échéance",
        blank=True,
        null=True
    )
    taxe_redevance = models.CharField(
        max_length=32,
        choices=[
            ('patentes', "Patentes"),
            ('taxe_licences', "Taxe de licences"),
            ('propriete_batie', "Propriété bâtie"),
            ('propriete_non_batie', "Propriété non bâtie"),
            ('droit_mutation', "Droit de mutation"),
            ('taxe_stationnement', "Taxe de stationnement"),
            ('taxe_ordures', "Taxe d'enlèvement des ordures ménagères"),
            ('taxe_publicites', "Taxe de publicités"),
            ('occupation_domaine', "Occupation du domaine public"),
        ],
        blank=True,
        null=True,
        verbose_name="Taxe/Redevance"
    )

    class Meta:
        ordering = ['nom']
        verbose_name = "Contribuable"
        verbose_name_plural = "Contribuables"
        indexes = [
            models.Index(fields=['nif']),
            models.Index(fields=['nom']),
            models.Index(fields=['actif']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['nif'], name='unique_nif'),
            models.UniqueConstraint(fields=['reference'], name='unique_reference'),
            models.UniqueConstraint(fields=['id'], name='unique_contribuable_id'),
        ]
    
    def __str__(self):
        return f"{self.nom} (NIF: {self.nif})"
    
    def clean(self):
        if self.nif and Contribuable.objects.exclude(id=self.id).filter(nif=self.nif).exists():
            raise ValidationError({'nif': 'Ce NIF est déjà utilisé'})
        if self.reference and Contribuable.objects.exclude(id=self.id).filter(reference=self.reference).exists():
            raise ValidationError({'reference': 'Cette référence existe déjà'})
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        prefix = "CONTRIB"
        year = timezone.now().strftime("%Y")
        unique_part = uuid.uuid4().hex[:4].upper()
        return f"{prefix}-{year}-{unique_part}"
    
    def update_total_paye(self):
        total = self.paiements.aggregate(total=Sum('montant'))['total'] or 0
        if self.total_paye != total:
            self.total_paye = total
            self.save(update_fields=['total_paye'])
    
    @property
    def paiements_en_retard(self):
        return self.paiements.filter(date_paiement__gt=F('date_echeance'))
    
    @property
    def a_des_retards(self):
        return self.paiements_en_retard.exists()
    
    @property
    def dernier_paiement(self):
        return self.paiements.order_by('-date_paiement').first()
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('admin:gestion_contribuables_contribuable_change', args=[str(self.id)])
    
    def generer_quittance(self, paiement):
        qr_data = f"Tél: {self.telephone}\nMail: {self.email}\nAdresse: {self.adresse}"
        qr = qrcode.make(qr_data)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        context = {
            'contribuable': self,
            'paiement': paiement,
            'date_emission': timezone.now().date().isoformat(),
            'total_paye': self.total_paye,
            'qr_base64': qr_base64,
        }

        html_string = render_to_string('quittance_template.html', context)
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        quittance_dir = os.path.join(settings.MEDIA_ROOT, 'quittances')
        os.makedirs(quittance_dir, exist_ok=True)
        filename = f"quittance_{paiement.reference or paiement.pk}.pdf"
        filepath = os.path.join(quittance_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(pdf_file)

        return filepath


class Paiement(models.Model):
    MODES_PAIEMENT = [
        ('ESP', 'Espèces'),
        ('CHQ', 'Chèque'),
        ('VIR', 'Virement'),
        ('CB', 'Carte Bancaire'),
        ('OM', 'Orange Money'),
        ('FM', 'Free Money'),
        ('WM', 'Wizale Money'),
        ('WA', 'Wave'),
        ('MOMO', 'MTN Mobile Money'),
    ]
    
    TAXE_REDEVANCE_CHOICES = [
        ('patentes', "Patentes"),
        ('taxe_licences', "Taxe de licences"),
        ('propriete_batie', "Propriété bâtie"),
        ('propriete_non_batie', "Propriété non bâtie"),
        ('droit_mutation', "Droit de mutation"),
        ('taxe_stationnement', "Taxe de stationnement"),
        ('taxe_ordures', "Taxe d'enlèvement des ordures ménagères"),
        ('taxe_publicites', "Taxe de publicités"),
        ('occupation_domaine', "Occupation du domaine public"),
    ]

    contribuable = models.ForeignKey(
        Contribuable,
        on_delete=models.CASCADE,
        related_name='paiements'
    )
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    date_paiement = models.DateField()
    date_echeance = models.DateField()
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )
    mode_paiement = models.CharField(
        max_length=10,
        choices=MODES_PAIEMENT
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='paiements_enregistres'
    )
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    quittance_generee = models.BooleanField(default=False)
    fichier_quittance = models.FileField(
        upload_to='quittances/',
        null=True,
        blank=True
    )
    taxe_redevance = models.CharField(
        max_length=32,
        choices=TAXE_REDEVANCE_CHOICES,
        blank=True,
        null=True,
        verbose_name="Taxe/Redevance"
    )
    
    class Meta:
        ordering = ['-date_paiement']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        constraints = [
            models.UniqueConstraint(fields=['reference'], name='unique_paiement_reference')
        ]
    
    def __str__(self):
        return f"Paiement {self.reference} - {self.contribuable.nom}"
    
    def save(self, *args, **kwargs):
        # Générer la référence si elle n'existe pas
        if not self.reference:
            self.reference = self.generate_reference()

        # Préremplir les champs si ils sont vides
        if self.contribuable:
            if self.montant is None:
                self.montant = self.contribuable.montant_a_payer
            if self.taxe_redevance is None and hasattr(self.contribuable, 'taxe_redevance'):
                self.taxe_redevance = self.contribuable.taxe_redevance
            if self.date_echeance is None:
                self.date_echeance = self.contribuable.date_echeance

        super().save(*args, **kwargs)
        self.contribuable.update_total_paye()

        if not self.quittance_generee or not self.fichier_quittance:
            quittance_path = self.generer_quittance()
            self.fichier_quittance.name = quittance_path.replace(settings.MEDIA_ROOT + '/', '')
            self.quittance_generee = True
            super().save(update_fields=['fichier_quittance', 'quittance_generee'])

        if self.est_en_retard and self.contribuable.notifier_retards:
            self.notifier_retard()

    def generate_reference(self):
        prefix = "PAY"
        date_part = timezone.now().strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{date_part}-{unique_part}"
    
    def generer_quittance(self):
        quittance_path = self.contribuable.generer_quittance(self)
        return quittance_path
    
    @property
    def est_en_retard(self):
        return self.date_paiement > self.date_echeance if all([self.date_paiement, self.date_echeance]) else False

    def notifier_retard(self):
        subject = f"Mise en demeure de paiement - {self.contribuable.nom}"
        context = {
            'contribuable': self.contribuable,
            'paiement': self,
            'jours_retard': (timezone.now().date() - self.date_echeance).days
        }
        html_message = render_to_string('emails/notification_retard.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [self.contribuable.email],
            html_message=html_message,
            fail_silently=True
        )

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('admin:gestion_contribuables_paiement_change', args=[str(self.id)])


class HistoriqueModification(models.Model):
    contribuable = models.ForeignKey(
        Contribuable,
        on_delete=models.CASCADE,
        related_name='historique'
    )
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_modification = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=[
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression')
    ])
    details = models.JSONField(encoder=DjangoJSONEncoder)
    
    class Meta:
        ordering = ['-date_modification']
        verbose_name = "Historique de modification"
        verbose_name_plural = "Historiques de modifications"
    
    def __str__(self):
        return f"{self.action} - {self.contribuable.nom}"

    def get_details(self):
        if isinstance(self.details, str):
            try:
                return json.loads(self.details)
            except json.JSONDecodeError:
                return {'erreur': 'Format JSON invalide', 'contenu': self.details}
        return self.details


@receiver(post_save, sender=Contribuable)
def suivre_modifications(sender, instance, created, **kwargs):
    user = getattr(instance, '_current_user', None)
    action = "CREATE" if created else "UPDATE"
    
    details = {
        'champs_modifies': [],
        'dates': {
            'inscription': instance.date_inscription.isoformat() if instance.date_inscription else None,
            'modification': instance.date_modification.isoformat() if instance.date_modification else None
        },
        'utilisateur': user.username if user and user.is_authenticated else None
    }
    
    if not created:
        for field in instance._meta.fields:
            if hasattr(instance, f'_original_{field.name}'):
                original_value = getattr(instance, f'_original_{field.name}')
                current_value = getattr(instance, field.name)
                if hasattr(original_value, 'isoformat'):
                    original_value = original_value.isoformat()
                if hasattr(current_value, 'isoformat'):
                    current_value = current_value.isoformat()
                if original_value != current_value:
                    details['champs_modifies'].append(field.name)
    
    HistoriqueModification.objects.create(
        contribuable=instance,
        utilisateur=user if user and user.is_authenticated else None,
        action=action,
        details=details,
    )