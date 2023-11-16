from django.db import models
from martor.models import MartorField


class Nofo(models.Model):
    title = models.TextField(blank=True)
    short_name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title


# TODO default lambda
# order = models.IntegerField(default=lambda: Section.objects.latest("order") + 1)
class Section(models.Model):
    nofo = models.ForeignKey(Nofo, on_delete=models.CASCADE, related_name="sections")
    name = models.TextField("Section name")
    order = models.IntegerField(null=True)

    class Meta:
        unique_together = ("nofo", "order")

    def __str__(self):
        return self.name


class Subsection(models.Model):
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="subsections"
    )
    name = models.TextField("Subsection name")
    order = models.IntegerField(null=True)

    class Meta:
        unique_together = ("section", "order")

    TAG_CHOICES = [
        ("h2", "Heading 2"),
        ("h3", "Heading 3"),
        ("h4", "Heading 4"),
        ("h5", "Heading 5"),
        ("h6", "Heading 6"),
    ]
    tag = models.CharField(
        max_length=2,
        choices=TAG_CHOICES,
    )

    body = MartorField("Content of subsection", blank=True)

    def __str__(self):
        return self.name
