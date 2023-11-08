from django.db import models


class BaseModel(models.Model):
    def get_fields(self):
        return [
            (field.name, getattr(self, field.name))
            for field in self._meta.fields
            if field.name not in ["id", "document"]
        ]

    class Meta:
        abstract = True


class Document(BaseModel):
    shortTitle = models.CharField("short title", max_length=256)
    title = models.CharField(max_length=256)
    number = models.CharField(max_length=128)


class Organization(BaseModel):
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
    )
    agency = models.CharField(max_length=128)
    officeOrBureau = models.CharField(max_length=128)
    division = models.CharField(max_length=128, blank=True)


class Overview(BaseModel):
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
    )
    summary = models.TextField()
    questions = models.TextField(blank=True)
    nofo_type = models.CharField("type", max_length=128)
    eligible_applications = models.TextField()
    expected_awards = models.CharField(max_length=128)
    expected_funding = models.CharField(max_length=128)
    expected_funding_per_recipient = models.TextField()
    cost_share_or_match_requirement = models.TextField()
    performance_period = models.CharField(max_length=128, blank=True)
    program_description = models.TextField()
    application_deadline = models.CharField(max_length=128, blank=True)


class Section(BaseModel):
    section_title = models.CharField(max_length=256)
    body = models.TextField()
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
