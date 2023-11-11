from django.db import models


class Post(models.Model):
    title = models.TextField()
    body = models.TextField()

    def __str__(self):
        return self.title


class Section(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    name = models.TextField()
    tag = models.CharField(max_length=4)

    def __str__(self):
        return self.name


class Subsection(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    name = models.TextField()
    tag = models.CharField(max_length=4)
    body = models.TextField()

    def __str__(self):
        return self.title
