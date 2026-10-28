import json
from django.db.models import Count
from apps.catalogs.models import Discipline
from apps.competitions.models import Competition, Application, Result, ProtocolPublication
from apps.registry.models import DisciplinePeriod
rows=[]
for d in Discipline.objects.order_by('pk'):
 rows.append({'code':d.code,'competitions':Competition.objects.filter(discipline=d).count(),'applications':Application.objects.filter(competition__discipline=d).count(),'results':Result.objects.filter(application__competition__discipline=d).count(),'publications':ProtocolPublication.objects.filter(competition__discipline=d).count(),'registry_periods':DisciplinePeriod.objects.filter(discipline=d).count()})
print(json.dumps(rows,ensure_ascii=True,indent=2))
print('competition_years', list(Competition.objects.dates('starts_at','year').values_list('starts_at__year',flat=True).distinct()))
