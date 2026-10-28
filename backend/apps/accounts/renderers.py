"""Russian HTTP error text; machine field names and successful payloads stay intact."""
import re

from rest_framework.renderers import JSONRenderer

ERRORS = {
    "Account already exists": "Учётная запись с таким адресом уже существует",
    "Invalid credentials": "Неверная электронная почта или пароль",
    "Consent is required": "Необходимо согласие на обработку персональных данных",
    "Unsupported consent version": "Эта версия согласия больше не поддерживается",
    "Date cannot be in the future": "Дата не может быть в будущем",
    "Date of birth cannot be in the future": "Дата рождения не может быть в будущем",
    "Guardian details and consent are required for a minor": "Для несовершеннолетнего нужны данные и согласие законного представителя",
    "Active role is not assigned": "Активная роль не назначена",
    "Active assigned role required": "Выберите назначенную роль с доступом к этому действию",
    "Active federation role required": "Выберите назначенную роль федерации",
    "Federation role required": "Необходима роль федерации",
    "Athletes can only apply for themselves": "Спортсмен может подать заявку только за себя",
    "Confirmed coach link is required": "Нужна подтверждённая связь тренера со спортсменом по этой дисциплине",
    "Judge is not assigned to this competition": "Судья не назначен на это соревнование",
    "Draft competition": "Черновик соревнования доступен только федерации",
    "Minimum age cannot exceed maximum age": "Минимальный возраст не может превышать максимальный",
    "Competition is not published": "Соревнование ещё не опубликовано",
    "Competition must be published": "Сначала опубликуйте соревнование",
    "Only a draft can be published": "Опубликовать можно только черновик",
    "Registration deadline must be in the future": "Срок приёма заявок должен быть в будущем",
    "Registration deadline has passed": "Срок подачи заявок истёк",
    "Applicant must have athlete role": "Заявитель должен иметь роль спортсмена",
    "Athlete role is required": "Необходима назначенная роль спортсмена",
    "Age group is not offered": "Эта возрастная группа не предусмотрена соревнованием",
    "Athlete date of birth is required": "Укажите дату рождения спортсмена",
    "Athlete is outside age group": "Возраст спортсмена не соответствует выбранной группе",
    "Personal data consent is required": "Требуется действующее согласие на обработку персональных данных",
    "Current personal-data consent is required": "Требуется действующее согласие на обработку персональных данных",
    "Verified guardian consent is required": "Согласие законного представителя должно пройти проверку",
    "Application already exists": "Заявка на это соревнование уже существует",
    "Only pending applications can be decided": "Решение можно принять только по заявке на рассмотрении",
    "Rejection reason is required": "Укажите причину отклонения",
    "Assigned user must be a judge": "Назначаемый пользователь должен иметь роль судьи",
    "Judge is already assigned": "Этот судья уже назначен",
    "Result is already validated": "Результат уже проверен",
    "Only approved applications can have results": "Результаты доступны только для одобренных заявок",
    "Unclassified result cannot carry place, score or metrics": "Для результата без классификации нельзя указывать место, баллы или показатели",
    "A classified result needs place or score": "Укажите место или баллы для классифицированного результата",
    "Place is already assigned; enable ties in competition rules to share a place": "Это место уже занято; одинаковые места должны быть разрешены положением",
    "Metrics must be an object": "Показатели должны быть объектом с именованными полями",
    "Unknown metric field": "Неизвестный показатель протокола",
    "Unknown protocol column": "Неизвестная колонка протокола",
    "Invalid metric definition": "Некорректное описание показателя",
    "Moderate all applications before publishing protocol": "Перед публикацией протокола рассмотрите все заявки",
    "Validate entered results before publication": "Перед публикацией проверьте внесённые результаты",
    "Every approved athlete needs current personal data consent": "Для каждого одобренного участника требуется действующее согласие на обработку данных",
    "Every approved minor needs verified guardian consent": "Для каждого несовершеннолетнего участника требуется проверенное согласие представителя",
    "A correction reason is required for a new protocol version": "Укажите причину выпуска новой версии протокола",
    "Competition setup is frozen after protocol publication": "После публикации протокола настройки соревнования зафиксированы",
    "Competition eligibility and template are frozen after the first application": "После первой заявки нельзя менять условия допуска и шаблон",
    "Age groups are frozen after the first application": "После первой заявки нельзя менять возрастные группы",
    "Stages are frozen after the first application": "После первой заявки нельзя менять этапы",
    "file_format must be pdf or docx": "Выберите формат PDF или DOCX",
    "Pending link requires confirmed or rejected status": "Ожидающую связь нужно подтвердить или отклонить",
    "Regulations must specify an age reference date": "Укажите дату определения возраста по положению",
    "Template discipline must match competition discipline": "Дисциплина шаблона должна совпадать с дисциплиной соревнования",
    "Template is configured for a different competition type": "Шаблон предназначен для другого типа соревнования",
    "Template is not effective on the competition date": "Шаблон не действует на дату соревнования",
    "End must follow start": "Окончание должно быть позже начала",
    "Registration must close before start": "Приём заявок должен завершиться до начала соревнования",
    "At least one age group is required": "Выберите хотя бы одну возрастную группу",
    "Hybrid competition requires stages": "Для смешанного формата укажите этапы",
    "Stages must fit competition dates": "Даты этапов должны входить в период соревнования",
    "Must be an integer": "Введите целое число",
    "Invalid age group": "Некорректная возрастная группа",
    "Choose between two and ten consecutive years": "Выберите от двух до десяти последовательных лет",
    "Profile already exists": "Профиль уже существует",
    "Unknown registry role": "Неизвестная роль в реестре",
    "Choose athlete, coach or judge": "Выберите спортсмена, тренера или судью",
    "Choose coach or judge": "Выберите тренера или судью",
    "Organization code is stable and cannot be changed": "Код организации зафиксирован и не может быть изменён",
    "Athlete is already selected": "Спортсмен уже включён в состав",
    "Membership is already removed": "Спортсмен уже исключён из состава",
    "Member ids must be integers": "Идентификаторы участников должны быть целыми числами",
    "All active members must be included exactly once": "Включите всех действующих участников ровно по одному разу",
    "A team must have at least one active member": "Добавьте хотя бы одного действующего участника",
    "Athlete is outside the selected age group or has an active restriction/invalid consent": "Спортсмен не проходит по возрасту, имеет действующее ограничение или не имеет необходимого согласия",
    "End must not precede start": "Окончание не может предшествовать началу",
    "Period overlaps an existing period": "Период пересекается с существующей записью",
    "Period conflicts with another record": "Период конфликтует с другой записью",
    "The period changed since it was loaded; refresh and retry": "Период изменился после загрузки. Обновите данные и повторите действие",
    "Athlete already belongs to this organization": "Спортсмен уже состоит в этой организации",
    "Future transfers are not supported": "Дата перевода не может быть в будущем",
    "Open period not found": "Открытый период не найден",
    "Not found.": "Запись не найдена",
}


def russian_error(value):
    if isinstance(value, dict):
        return {key: russian_error(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [russian_error(item) for item in value]
    if isinstance(value, str):
        if value in ERRORS:
            return ERRORS[value]
        if re.fullmatch(r"Metric \w+ is required", value):
            return "Заполните обязательный показатель протокола"
        if re.fullmatch(r"Invalid value for metric \w+", value):
            return "Некорректное значение показателя протокола"
        if re.search(r"[A-Za-z]{2,}\s+[A-Za-z]{2,}", value) and not re.search(r"[А-Яа-яЁё]", value):
            return "Действие недоступно. Проверьте введённые данные и права доступа."
    return value


class RussianJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response is not None and response.status_code >= 400:
            data = russian_error(data)
        return super().render(data, accepted_media_type, renderer_context)
