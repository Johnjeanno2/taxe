from grappelli.dashboard import modules, Dashboard
from django.utils import timezone
import pytz

# Exemple pour l'Afrique/Abidjan
fuseau_horaire = pytz.timezone("Africa/Abidjan")

class CustomDashboard(Dashboard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        date = timezone.now().astimezone(fuseau_horaire)
        
        self.children.append(modules.Group(
            title="Statistiques",
            column=1,
            children=[
                modules.LinkList(
                    title="Rapports",
                    children=[
                        {'title': 'Paiements mensuels', 'url': '/admin/paiements/'},
                        {'title': 'Contribuables actifs', 'url': '/admin/contribuables/?actif__exact=1'},
                    ]
                ),
                modules.ContentTypeList(
                    title='Analyses',
                    column=2
                )
            ]
        ))

class CustomIndexDashboard(Dashboard):
    def init_with_context(self, context):
        self.children += [
            modules.AppList(
                title="Système de rappel",
                models=('systeme_rappel.models.*',),
            ),
            modules.AppList(
                title="Trésorerie",
                models=('tresorerie.models.*',),
            ),
        ]