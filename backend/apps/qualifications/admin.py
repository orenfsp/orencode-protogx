from django.contrib import admin

from .models import (
    JudgeCategoryApplication,
    JudgeCategoryHistory,
    QualificationCorrection,
    QualificationRule,
    RankApplication,
    SportRankHistory,
)

admin.site.register(QualificationRule)


class ReadOnlyRecordsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (RankApplication, SportRankHistory, JudgeCategoryApplication, JudgeCategoryHistory, QualificationCorrection):
    admin.site.register(model, ReadOnlyRecordsAdmin)
