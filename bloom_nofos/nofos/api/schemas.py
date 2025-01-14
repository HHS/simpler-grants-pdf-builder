from typing import List, Optional

from ninja import ModelSchema, Schema
from nofos.models import Nofo, Section, Subsection


class SubsectionSchema(ModelSchema):
    class Config:
        model = Subsection
        model_fields = [
            "name",
            "html_id",
            "order",
            "tag",
            "body",
            "callout_box",
            "html_class",
        ]
        model_fields_optional = ["html_class"]  # Fields that should have defaults


class SectionBaseSchema(ModelSchema):
    class Config:
        model = Section
        model_fields = ["name", "html_id", "order", "has_section_page"]


class SectionSchema(SectionBaseSchema):
    subsections: List[SubsectionSchema]


class NofoBaseSchema(ModelSchema):
    class Config:
        model = Nofo
        model_fields = [
            "id",
            "title",
            "filename",
            "short_name",
            "number",
            "opdiv",
            "agency",
            "tagline",
            "application_deadline",
            "subagency",
            "subagency2",
            "author",
            "subject",
            "keywords",
            "theme",
            "cover",
            "icon_style",
            "status",
            "cover_image",
            "cover_image_alt_text",
            "inline_css",
            "sole_source_justification",
        ]
        model_fields_optional = [
            "subagency",
            "subagency2",
            "author",
            "subject",
            "keywords",
            "cover_image",
            "cover_image_alt_text",
            "inline_css",
            "sole_source_justification",
        ]


class NofoSchema(NofoBaseSchema):
    sections: List[SectionSchema]


class ErrorSchema(Schema):
    message: str
    details: Optional[dict] = None


class SuccessSchema(Schema):
    nofo: NofoSchema
