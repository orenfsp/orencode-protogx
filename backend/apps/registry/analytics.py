"""Calendar-year participation report; see docs/participation-methodology.md."""
from collections import defaultdict
from datetime import date, timedelta

from apps.competitions.models import AgeGroup
from apps.competitions.services import age_on

from .models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
)


def intersect(a, b):
    start, end = max(a[0], b[0]), min(a[1], b[1])
    return (start, end) if start <= end else None


def has_uncovered(intervals, periods):
    for start, end in intervals:
        clipped = sorted(value for p in periods if (value := intersect((start, end), (p.starts_on, p.ends_on or date.max))))
        cursor = start
        for left, right in clipped:
            if left > cursor:
                return True
            if right >= end:
                break
            cursor = max(cursor, right + timedelta(days=1))
        else:
            return True
    return False


def participation_report(start_year, end_year, *, organization=None, discipline=None, municipality=None, age_group=None):
    start, end = date(start_year, 1, 1), date(end_year, 12, 31)

    def load(model, related=None):
        queryset = model.objects.filter(starts_on__lte=end).filter(ends_on__isnull=True) | model.objects.filter(starts_on__lte=end, ends_on__gte=start)
        if related:
            queryset = queryset.select_related(related)
        groups = defaultdict(list)
        for item in queryset:
            groups[item.athlete_id].append(item)
        return groups

    participation = load(ParticipationPeriod, "athlete")
    histories = {
        "organizations": load(OrganizationPeriod, "organization"),
        "disciplines": load(DisciplinePeriod, "discipline"),
        "municipalities": load(MunicipalityPeriod),
    }
    filters = {"organizations": organization, "disciplines": discipline, "municipalities": municipality}
    age_groups = list(AgeGroup.objects.order_by("pk"))
    output = []
    previous = None
    for year in range(start_year, end_year + 1):
        bounds = (date(year, 1, 1), date(year, 12, 31))
        counts = {key: defaultdict(set) for key in (*histories, "age_groups")}
        unique, started, ceased = set(), set(), set()
        for athlete_id, periods in participation.items():
            intervals = [intersection for p in periods if (intersection := intersect((p.starts_on, p.ends_on or date.max), bounds))]
            if not intervals:
                continue
            born = periods[0].athlete.date_of_birth
            age = age_on(born, bounds[1]) if born and born <= bounds[1] else None
            matching_ages = [g for g in age_groups if age is not None and g.min_age <= age <= g.max_age]
            if age_group is not None and not any(g.pk == age_group for g in matching_ages):
                continue
            for kind, target in filters.items():
                if target is None:
                    continue
                choices = histories[kind].get(athlete_id, [])
                def key(p):
                    return p.organization_id if kind == "organizations" else p.discipline_id if kind == "disciplines" else p.municipality
                intervals = [intersection for interval in intervals for p in choices if key(p) == target if (intersection := intersect(interval, (p.starts_on, p.ends_on or date.max)))]
            if not intervals:
                continue
            unique.add(athlete_id)
            if any(p.starts_on.year == year for p in periods):
                started.add(athlete_id)
            if any(p.ends_on and p.ends_on.year == year for p in periods):
                ceased.add(athlete_id)
            for kind, by_athlete in histories.items():
                values = by_athlete.get(athlete_id, [])
                for p in values:
                    if any(intersect(interval, (p.starts_on, p.ends_on or date.max)) for interval in intervals):
                        label = p.organization.name if kind == "organizations" else p.discipline.name if kind == "disciplines" else p.municipality
                        identity = p.organization_id if kind == "organizations" else p.discipline_id if kind == "disciplines" else label
                        counts[kind][(str(identity), label)].add(athlete_id)
                if has_uncovered(intervals, values):
                    counts[kind][("", "Не указана")].add(athlete_id)
            for group in matching_ages:
                counts["age_groups"][(str(group.pk), group.name)].add(athlete_id)
            if not matching_ages:
                counts["age_groups"][("", "Не определена")].add(athlete_id)
        total = len(unique)
        output.append({"year": year, "unique_athletes": total, "started": len(started), "ceased": len(ceased), "change": None if previous is None else total - previous, "growth_percent": None if not previous else round((total - previous) * 100 / previous, 2), "breakdowns": {key: [{"name": label, "participants": len(ids)} for (_, label), ids in sorted(values.items(), key=lambda item: (item[0][1], item[0][0]))] for key, values in counts.items()}})
        previous = total
    return output
