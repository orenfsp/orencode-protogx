import json
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User, UserRole, PersonalDataConsent
from apps.catalogs.models import Discipline
from apps.competitions.models import ProtocolTemplate
from apps.qualifications.models import QualificationRule
from apps.qualifications.services import active_rules
from apps.extensions.models import AssessmentNorm, ProgressionRule, AwardScheme, TrainingGroup
from apps.extensions.training import enroll, training_report
from apps.registry.analytics import participation_report

result = {
 'disciplines': Discipline.objects.count(),
 'qualification_rules_total': QualificationRule.objects.count(),
 'qualification_rules_verified_active': len(active_rules()),
 'protocol_templates_total': ProtocolTemplate.objects.count(),
 'protocol_templates_verified': ProtocolTemplate.objects.filter(source_verified=True).count(),
 'assessment_norms_total': AssessmentNorm.objects.count(),
 'assessment_norms_verified': AssessmentNorm.objects.filter(source_verified=True).count(),
 'progression_rules_total': ProgressionRule.objects.count(),
 'progression_rules_verified': ProgressionRule.objects.filter(source_verified=True).count(),
 'award_schemes_total': AwardScheme.objects.count(),
 'award_schemes_verified': AwardScheme.objects.filter(source_verified=True).count(),
}
with transaction.atomic():
 year=timezone.localdate().year
 before=participation_report(year-1,year)
 before_training=training_report(year-1,year)
 athlete=User.objects.create_user(email=f'audit-fictional-{uuid4().hex}@example.test',full_name='Audit fictional athlete',date_of_birth=date(2000,1,1))
 UserRole.objects.create(user=athlete,role='athlete')
 PersonalDataConsent.objects.create(user=athlete,text_version='audit-fictional',confirmation_method='demo_seed')
 federation=User.objects.filter(role_assignments__role='federation').first()
 group=TrainingGroup.objects.select_related('discipline','organization').first()
 request=SimpleNamespace(user=federation,session={'active_role':'federation'})
 enroll(request=request,athlete=athlete,group=group,starts_on=date(year-1,1,1))
 after=participation_report(year-1,year)
 after_training=training_report(year-1,year)
 result['d3_enrollment_probe']={
  'registry_delta':[a['unique_athletes']-b['unique_athletes'] for a,b in zip(after,before)],
  'training_delta':[a['unique_athletes']-b['unique_athletes'] for a,b in zip(after_training['rows'],before_training['rows'])],
  'rolled_back':True,
 }
 transaction.set_rollback(True)
print(json.dumps(result,ensure_ascii=False,indent=2))
