from django.contrib import admin

from .models import JudgeCategoryApplication, JudgeCategoryHistory, QualificationRule, RankApplication, SportRankHistory

admin.site.register(QualificationRule)
admin.site.register(RankApplication)
admin.site.register(SportRankHistory)
admin.site.register(JudgeCategoryApplication)
admin.site.register(JudgeCategoryHistory)
