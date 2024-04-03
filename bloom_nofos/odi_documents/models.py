from django.db import models

from django.db import models
from django.urls import reverse
from martor.models import MartorField

class ODIDocument(models.Model):
    title = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('documents:document_detail', args=[self.id])


class Section(models.Model):
    document = models.ForeignKey(ODIDocument, on_delete=models.CASCADE, related_name='sections')
    name = models.TextField("Section name", blank=True)
    body = MartorField()
    order = models.IntegerField()

    TAG_CHOICES = [
        ("h2", "Heading 2"),
        ("h3", "Heading 3"),
        ("h4", "Heading 4"),
        ("h5", "Heading 5"),
        ("h6", "Heading 6"),
    ]

    tag = models.CharField(max_length=2, choices=TAG_CHOICES, blank=True)

    class Meta:
        unique_together = ("document", "order")
        ordering = ['order']

    def __str__(self):
        return self.title