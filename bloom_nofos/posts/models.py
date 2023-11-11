from django.db import models
from martor.models import MartorField


class Post(models.Model):
    title = models.TextField()

    def __str__(self):
        return self.title


class Section(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="sections")
    name = models.TextField()

    def __str__(self):
        return self.name


class Subsection(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    name = models.TextField()

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

    body = MartorField(blank=True)

    def __str__(self):
        return self.name
