import os
from datetime import date

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from oauth2_provider.models import Application as OIDCApplication

from apps.accounts.models import PersonalDataConsent, User
from apps.catalogs.models import Discipline, Organization
from apps.competitions.models import Competition
from apps.competitions.services import audit
from apps.extensions.models import (
    AssessmentAttempt,
    AssessmentNorm,
    AwardRate,
    AwardScheme,
    OIDCClientPolicy,
    ProgressionRule,
    TrainingGroup,
    TrainingMembership,
    TrainingOrganization,
)


class Command(BaseCommand):
    help="Аддитивные вымышленные сценарии Д1–Д12; не переписывает документы, пароли или существующие результаты"

    @transaction.atomic
    def handle(self,*args,**options):
        if not settings.DEBUG or os.environ.get("DEMO_ENVIRONMENT")!="local" or os.environ.get("DEMO_SEED_ENABLED")!="1":
            raise CommandError("Требуется локальное DEBUG-окружение с явным разрешением demo seed")
        call_command("seed_demo",verbosity=0)
        federation=User.objects.get(email="demo.federation@example.test")
        athlete=User.objects.get(email="demo.athlete@example.test")
        coach=User.objects.get(email="demo.coach@example.test")
        discipline=Discipline.objects.get(code="algorithmic")
        year=timezone.localdate().year
        org,_=Organization.objects.get_or_create(code="demo-optional-training",defaults={"name":"Демо: вымышленная школа ОренКод"})
        if org.name!="Демо: вымышленная школа ОренКод":
            raise CommandError("Зарезервированный demo-код уже занят")
        card,_=TrainingOrganization.objects.get_or_create(organization=org,defaults={"organization_type":"Демонстрационная спортивная школа","municipality":"Вымышленный муниципалитет","program":"Демо-программа по четырём этапам спортивной подготовки","license_details":"ДЕМО-ЛИЦЕНЗИЯ — не подтверждает права","contact_url":"https://example.test/training","public":True})
        card.coaches.add(coach)
        card.disciplines.add(discipline)
        groups=[]
        for stage,label in [("initial","Начальная"),("training","Учебно-тренировочная"),("mastery","Совершенствование мастерства"),("highest","Высшее мастерство")]:
            group,_=TrainingGroup.objects.get_or_create(organization=card,discipline=discipline,coach=coach,stage=stage,name=f"Демо: {label}")
            groups.append(group)
        if not TrainingMembership.objects.filter(athlete=athlete,discipline=discipline).exists():
            membership=TrainingMembership.objects.create(athlete=athlete,discipline=discipline,group=groups[0],starts_on=date(year-2,1,1),recorded_by=federation)
            audit(federation,"training.enrolled",membership,after={"demo":True})
        norm,_=AssessmentNorm.objects.get_or_create(key="demo-typing",version=1,discipline=discipline,stage="initial",sex="all",defaults={"name":"Демо: скорость печати (вымышленный порог)","unit":"знаков/мин","comparator":"min","threshold":"100","effective_from":date(year-2,1,1),"source_version":"fictional-demo-not-order-445"})
        AssessmentAttempt.objects.get_or_create(athlete=athlete,norm=norm,measured_on=timezone.localdate(),defaults={"value":"110","recorded_by":coach,"outcome":{"passed":True,"threshold":"100","comparator":"min","explanation":"110 знаков/мин >= 100; демонстрационный порог выполнен","demonstration":True}})
        ProgressionRule.objects.get_or_create(discipline=discipline,target_rank="adult_2",version=1,defaults={"effective_from":date(year-2,1,1),"levels":["Regional","Russian Championship"],"maximum_place":3,"required_results":2,"source_version":"fictional-demo-not-EVSK"})
        # Include existing fictional protocol years; the amounts deliberately are
        # small invented values and never represented as the Governor's rates.
        for award_year in Competition.objects.filter(created_by=federation,title__startswith="Демо",protocols__isnull=False).values_list("starts_at__year",flat=True).distinct():
            scheme,_=AwardScheme.objects.get_or_create(year=award_year,version=1,defaults={"name":f"ДЕМО: вымышленные премии {award_year}","deadline":date(award_year+1,2,1),"aggregation":"best","source_version":"fictional-demo-not-decree-93"})
            for level in ["Regional","Russian Championship","Russian Junior Championship"]:
                for place,amount in [(1,"300.00"),(2,"200.00"),(3,"100.00")]:
                    AwardRate.objects.get_or_create(scheme=scheme,level=level,place=place,defaults={"amount":amount})
        ministry,created=User.objects.get_or_create(email="demo.ministry@example.test",defaults={"full_name":"Демо Наблюдатель министерства","date_of_birth":date(1980,1,1)})
        if not created and not PersonalDataConsent.objects.filter(user=ministry,confirmation_method="demo_seed").exists():
            raise CommandError("Зарезервированная demo-учётная запись уже занята")
        if created:
            ministry.set_password("DemoOnly2026!")
            ministry.save(update_fields=["password"])
            PersonalDataConsent.objects.create(user=ministry,text_version="v1-demo-2026-10-27",confirmation_method="demo_seed")
        # Observer stays an existing User with Django permission; no write role.
        ministry.user_permissions.add(Permission.objects.get(content_type__app_label="extensions",codename="view_ministry_dashboard"))
        app,created=OIDCApplication.objects.get_or_create(client_id="fsp-fictional-client",defaults={"name":"Демо: вымышленный региональный сервис","user":federation,"client_type":"public","authorization_grant_type":"authorization-code","redirect_uris":"http://127.0.0.1:9012/callback","post_logout_redirect_uris":"http://127.0.0.1:9012/","algorithm":"RS256"})
        if app.name!="Демо: вымышленный региональный сервис":
            raise CommandError("Зарезервированный OIDC client_id занят")
        OIDCClientPolicy.objects.get_or_create(application=app,defaults={"scopes":["openid","profile","fsp_roles","fsp_disciplines","fsp_rank"]})
        self.stdout.write("Seeded optional fictional scenarios. No existing passwords, results or published documents changed. OIDC client: fsp-fictional-client")
