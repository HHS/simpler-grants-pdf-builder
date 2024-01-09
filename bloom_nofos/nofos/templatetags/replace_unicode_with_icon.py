from django import template
from django.utils.safestring import mark_safe
import html


from bs4 import BeautifulSoup

register = template.Library()

uswds_arrow_upward_icon = '<img class="usa-icon usa-icon--list" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_upward.svg" alt="Report upward trend" />'
uswds_arrow_downward_icon = '<img class="usa-icon usa-icon--list" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_downward.svg" alt="Report downward trend" />'
uswds_check_box_outline_blank_icon = '<img class="usa-icon usa-icon--check_box_outline_blank" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/check_box_outline_blank.svg" alt="Checkbox" />'


@register.filter()
def replace_unicode_with_icon(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for td in soup.find_all("td"):
        if td:
            if "◻" in td.text:
                td.string = td.text.replace("◻", "")
                td.insert(
                    0, BeautifulSoup(uswds_check_box_outline_blank_icon, "html.parser")
                )
            else:
                ## TODO: don't require it to be in an li
                for li in td.find_all("li"):
                    if "↑" in li.text:
                        li.string = li.text.replace(
                            "↑",
                            str(BeautifulSoup(uswds_arrow_upward_icon, "html.parser")),
                        )
                        li["class"] = "usa-list__usa-icon__arrow-upward"
                    if "↓" in li.text:
                        li.string = li.text.replace(
                            "↓",
                            str(
                                BeautifulSoup(uswds_arrow_downward_icon, "html.parser")
                            ),
                        )
                        li["class"] = "usa-list__usa-icon__arrow-downward"

    return mark_safe(html.unescape(soup.prettify()))
