from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def replace_variable_keys_with_values(html_string, variables_dict):
    soup = BeautifulSoup(html_string, "html.parser")

    # Find all span elements with class 'md-curly-variable'
    var_spans = soup.find_all("span", class_="md-curly-variable")
    for span in var_spans:
        # Look for a variable that matches the label
        label = span.text.strip().strip("{}").strip()
        var_key, var_info = find_variable_by_label(variables_dict, label)

        # If a matching variable exists, replace the content
        if var_key:
            var_value = var_info.get("value", None)
            if var_value:
                # Update the span with the variable value
                span.string = var_value
                # Add the "md-curly-variable--value" class to the list of classes
                span["class"] = span.get("class", []) + ["md-curly-variable--value"]

    return mark_safe(str(soup))


def find_variable_by_label(variables_dict, label):
    for var_key, var_info in variables_dict.items():
        if var_info.get("label") == label:
            return var_key, var_info
    return None, None
