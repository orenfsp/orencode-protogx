from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.catalogs.models import Discipline
from apps.competitions.models import CoachAthleteLink, Competition, ProtocolPublication
from apps.competitions.services import age_on, audit, require_role
from apps.qualifications.models import SportRank, SportRankHistory

from .models import ProgressionRule


class ProgressionRuleInput(serializers.ModelSerializer):
    levels = serializers.ListField(child=serializers.CharField(max_length=100), allow_empty=False, max_length=20)
    class Meta:
        model = ProgressionRule
        fields = ["discipline", "target_rank", "version", "effective_from", "effective_until", "levels", "maximum_place", "required_results", "source_url", "source_version"]

    def validate(self, data):
        if data["maximum_place"] < 1 or data.get("required_results", 1) < 1 or (data.get("effective_until") and data["effective_until"] < data["effective_from"]):
            raise serializers.ValidationError("Некорректные пороги или даты")
        return data


def progression_for(athlete, discipline):
    today = timezone.localdate()
    rank = SportRankHistory.objects.filter(athlete=athlete,discipline=discipline,assigned_on__lte=today,valid_until__gte=today).order_by("-assigned_on","-pk").first()
    ranks = list(SportRank.values)
    next_index = ranks.index(rank.rank)+1 if rank else 0
    target = ranks[next_index] if next_index < len(ranks) else None
    rule = ProgressionRule.objects.filter(discipline=discipline,target_rank=target,effective_from__lte=today).filter(Q(effective_until=None)|Q(effective_until__gte=today)).order_by("-version").first() if target else None
    evidence=[]
    latest={}
    for p in ProtocolPublication.objects.filter(competition__discipline=discipline,competition__applications__athlete=athlete).distinct().select_related("competition").order_by("competition_id","-version"):
        latest.setdefault(p.competition_id,p)
    if rule:
        for p in latest.values():
            if p.competition.level not in rule.levels or p.competition.starts_at.date() < rule.effective_from or (rule.effective_until and p.competition.starts_at.date()>rule.effective_until):
                continue
            row=next((r for r in p.snapshot["rows"] if r["athlete_id"]==athlete.pk),None)
            if row and row["status"]=="classified" and row.get("place") and row["place"]<=rule.maximum_place:
                evidence.append({"publication":p.pk,"version":p.version,"competition":p.competition.title,"place":row["place"]})
    upcoming=[]
    for c in Competition.objects.filter(discipline=discipline,state="published",starts_at__gt=timezone.now(),registration_deadline__gt=timezone.now()).prefetch_related("age_groups"):
        age=age_on(athlete.date_of_birth,c.age_reference_date or c.starts_at.date()) if athlete.date_of_birth else None
        if age is not None and any(g.min_age<=age<=g.max_age for g in c.age_groups.all()) and rule and c.level in rule.levels:
            upcoming.append({"id":c.pk,"title":c.title,"date":c.starts_at.date().isoformat()})
    return {"athlete":athlete.pk,"discipline":discipline.pk,"current_rank":rank.get_rank_display() if rank else "Нет действующего разряда","next_rank":SportRank(target).label if target else "Следующая ступень отсутствует","rule":rule.pk if rule else None,"demonstration":not rule or not rule.source_verified,"source":rule.source_url if rule else "","source_version":rule.source_version if rule else "Нормативная проверка заблокирована","evidence":evidence,"missing":max(0,rule.required_results-len(evidence)) if rule else None,"upcoming":upcoming,"preliminary_only":True}


class ProgressionView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        role=require_role(request,"federation","coach","athlete")
        pairs=[]
        if role=="coach":
            pairs=[(link.athlete,link.discipline) for link in CoachAthleteLink.objects.filter(coach=request.user,status="confirmed").select_related("athlete","discipline")]
        else:
            athletes=User.objects.filter(role_assignments__role="athlete") if role=="federation" else [request.user]
            pairs=[(a,d) for a in athletes for d in Discipline.objects.filter(is_active=True)]
        pathways=[(a,d,progression_for(a,d)) for a,d in pairs]
        return Response({"items":[{"id":f"{a.pk}-{d.pk}","name":a.full_name,"discipline":d.name,"current_rank":p["current_rank"],"next_rank":p["next_rank"],"missing":p["missing"] if p["missing"] is not None else "Нет проверенных правил","upcoming":[f"{c['title']} ({c['date']})" for c in p["upcoming"]],"details":f"{'ДЕМОНСТРАЦИЯ' if p['demonstration'] else 'Предварительно'} · {p['source_version']}"} for a,d,p in pathways],"pathways":[p for a,d,p in pathways],"notice":"Личный путь — предварительная рекомендация. Демонстрационные правила ЕВСК не подтверждают право на разряд. Присвоение оформляется отдельным решением; подходящее событие не гарантирует допуск.","options":{"disciplines":[{"value":d.pk,"label":d.name} for d in Discipline.objects.all()]}})


class ProgressionRuleCreateView(APIView):
    @extend_schema(request=ProgressionRuleInput,responses={201:OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self,request):
        require_role(request,"federation")
        serializer=ProgressionRuleInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule=serializer.save(source_verified=False)
        audit(request.user,"progression.rule_created",rule)
        return Response({"id":rule.pk},status=201)
