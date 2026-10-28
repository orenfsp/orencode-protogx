from datetime import date, timedelta
from uuid import uuid4
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole, PersonalDataConsent, AthleteProfile
from apps.catalogs.models import Discipline
from apps.competitions.models import Competition, ProtocolTemplate, AgeGroup
from apps.registry.models import DisciplinePeriod
import json
with transaction.atomic():
    athlete=User.objects.create_user(email=f'criteria-audit-{uuid4().hex}@example.test',full_name='Fictional audit athlete',date_of_birth=date(2000,1,1))
    UserRole.objects.create(user=athlete,role='athlete')
    PersonalDataConsent.objects.create(user=athlete,text_version='audit-fictional',confirmation_method='demo_seed')
    profile=AthleteProfile.objects.create(user=athlete)
    DisciplinePeriod.objects.create(athlete=athlete,discipline=Discipline.objects.get(code='algorithmic'),starts_on=date(2025,1,1))
    discipline=Discipline.objects.get(code='product')
    now=timezone.now()
    federation=User.objects.filter(role_assignments__role='federation').first()
    event=Competition.objects.create(title='Fictional criteria probe',discipline=discipline,template=ProtocolTemplate.objects.filter(discipline=discipline).first(),level='Regional',competition_type='cup',format='online',starts_at=now+timedelta(days=10),ends_at=now+timedelta(days=11),registration_deadline=now+timedelta(days=7),state='published',created_by=federation,location='Fictional',regulations='Fictional')
    group=AgeGroup.objects.filter(min_age=18).first()
    event.age_groups.add(group)
    client=APIClient(HTTP_HOST="localhost");client.force_login(athlete)
    session=client.session;session['active_role']='athlete';session.save()
    response=client.post('/api/v1/applications/',{'competition':event.pk,'athlete':athlete.pk,'age_group':group.pk},format='json')
    print(json.dumps({'profile_discipline':'algorithmic','competition_discipline':'product','http_status':response.status_code,'rolled_back':True}))
    transaction.set_rollback(True)
