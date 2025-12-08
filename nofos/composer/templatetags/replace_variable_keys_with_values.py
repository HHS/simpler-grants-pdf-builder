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
        # check if the span has data-variable-key attribute, use that to match variable if exists
        if "data-variable-key" in span.attrs:
            var_key = span["data-variable-key"]
            var_info = variables_dict.get(var_key, {})
        # Otherwise, try to match by label inside the curly braces
        else:
            label = span.text.strip().strip("{}").strip()
            var_key, var_info = find_variable_by_label(variables_dict, label)

        # If a matching variable exists, replace the content
        if var_key:
            # Add the variable key as a data attribute for future updates
            span["data-variable-key"] = var_key

            var_value = var_info.get("value", None)
            if var_value:
                # Update the span with the variable value
                span.string = var_value
    return mark_safe(str(soup))


def find_variable_by_label(variables_dict, label):
    for var_key, var_info in variables_dict.items():
        if var_info.get("label") == label:
            return var_key, var_info
    return None, None
