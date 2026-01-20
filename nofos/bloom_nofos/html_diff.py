import difflib

from bs4 import BeautifulSoup
from diff_match_patch import diff_match_patch

STRUCTURAL_TAGS = {"table", "thead", "tbody", "tr", "ul", "ol"}
DIFFABLE_TAGS = {"p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "div"}
BLOCK_WRAPPER_UNSAFE_TAGS = {"li", "td", "th", "tr", "thead", "tbody"}


def has_diff(diff_string):
    return "<ins>" in diff_string or "<del>" in diff_string


def html_diff(original_html, modified_html):
    # Input validation
    if original_html is None:
        original_html = ""
    if modified_html is None:
        modified_html = ""

    # Handle identical content early
    if original_html == modified_html:
        return original_html

    dmp = diff_match_patch()

    # Treat as plain text if no tags
    if not original_html.strip().startswith(
        "<"
    ) and not modified_html.strip().startswith("<"):
        return diff_plaintext_normalize_whitespace(original_html, modified_html, dmp)

    soup1 = BeautifulSoup(original_html, "html.parser")
    soup2 = BeautifulSoup(modified_html, "html.parser")

    tags1 = extract_diffable_nodes(soup1)
    tags2 = extract_diffable_nodes(soup2)

    return "".join(diff_node_lists(tags1, tags2, dmp))


def diff_plaintext_normalize_whitespace(text1, text2, dmp):
    # Normalize whitespace (collapse internal, trim ends)
    normalized_text1 = " ".join(text1.split())
    normalized_text2 = " ".join(text2.split())

    if normalized_text1 == normalized_text2:
        return normalized_text1

    return diff_text_nodes(normalized_text1, normalized_text2, dmp)


def diff_node_lists(nodes1, nodes2, dmp):
    seq1 = [get_node_text(n) for n in nodes1]
    seq2 = [get_node_text(n) for n in nodes2]
    matcher = difflib.SequenceMatcher(None, seq1, seq2)

    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for n1, n2 in zip(nodes1[i1:i2], nodes2[j1:j2]):
                result.append(diff_tags(n1, n2, dmp))
        elif tag == "replace":
            for n1, n2 in zip(nodes1[i1:i2], nodes2[j1:j2]):
                result.append(diff_tags(n1, n2, dmp))
            # Handle extras
            for n1 in nodes1[i1 + (j2 - j1) : i2]:
                result.append(wrap_any(n1, "del"))
            for n2 in nodes2[j1 + (i2 - i1) : j2]:
                result.append(wrap_any(n2, "ins"))
        elif tag == "delete":
            for n1 in nodes1[i1:i2]:
                result.append(wrap_any(n1, "del"))
        elif tag == "insert":
            for n2 in nodes2[j1:j2]:
                result.append(wrap_any(n2, "ins"))

    return result


def diff_tags(tag1, tag2, dmp):
    if isinstance(tag1, str) or isinstance(tag2, str):
        return diff_text_nodes(str(tag1), str(tag2), dmp)

    if tag1.name != tag2.name:
        return wrap_tag(tag1, "del") + wrap_tag(tag2, "ins")

    children1 = [c for c in tag1.children if not is_empty_string(c)]
    children2 = [c for c in tag2.children if not is_empty_string(c)]

    if (
        is_structural_tag(tag1)
        or is_structural_tag(tag2)
        or has_diffable_children(tag1)
        or has_diffable_children(tag2)
    ):
        return f"<{tag2.name}>{''.join(diff_node_lists(children1, children2, dmp))}</{tag2.name}>"

    return diff_leaf(tag1, tag2, dmp)


def diff_leaf(tag1, tag2, dmp):
    diffs = dmp.diff_main(tag1.get_text(), tag2.get_text())
    dmp.diff_cleanupSemantic(diffs)

    content = ""
    for op, data in diffs:
        if op == 0:
            content += data
        elif op == -1:
            content += f"<del>{data}</del>"
        elif op == 1:
            content += f"<ins>{data}</ins>"

    return f"<{tag2.name}>{content}</{tag2.name}>"


def wrap_tag(tag, wrapper):
    if tag.name in BLOCK_WRAPPER_UNSAFE_TAGS:
        # Special handling for <tr> - wrap each child cell individually
        # because <tr><ins>...</ins></tr> is invalid HTML and may get reformatted by the browser
        if tag.name == "tr":
            wrapped_children = []
            for child in tag.children:
                if hasattr(child, "name") and child.name in ("td", "th"):
                    wrapped_children.append(
                        f"<{child.name}><{wrapper}>{child.decode_contents()}</{wrapper}></{child.name}>"
                    )
                else:
                    # Handle text nodes or other content
                    wrapped_children.append(str(child))
            return f"<{tag.name}>{''.join(wrapped_children)}</{tag.name}>"
        else:
            return f"<{tag.name}><{wrapper}>{tag.decode_contents()}</{wrapper}></{tag.name}>"
    else:
        return f"<{wrapper}>{str(tag)}</{wrapper}>"


def wrap_any(node, wrapper):
    if hasattr(node, "name"):
        return wrap_tag(node, wrapper)
    return f"<{wrapper}>{str(node)}</{wrapper}>"


def diff_text_nodes(text1, text2, dmp):
    diffs = dmp.diff_main(str(text1), str(text2))
    dmp.diff_cleanupSemantic(diffs)

    out = ""
    for op, data in diffs:
        if op == 0:
            out += data
        elif op == -1:
            out += f"<del>{data}</del>"
        elif op == 1:
            out += f"<ins>{data}</ins>"
    return out


def get_node_text(node):
    if isinstance(node, str):
        return node.strip()
    return node.get_text(strip=True)


def is_empty_string(node):
    return isinstance(node, str) and node.strip() == ""


def has_diffable_children(tag):
    return any(getattr(child, "name", None) in DIFFABLE_TAGS for child in tag.children)


def is_structural_tag(tag):
    if tag.name in STRUCTURAL_TAGS:
        return True
    return any(
        getattr(child, "name", None) in STRUCTURAL_TAGS for child in tag.children
    )


def extract_diffable_nodes(soup):
    result = []

    def walk(node):
        if isinstance(node, str):
            return
        if node.name in STRUCTURAL_TAGS or node.name in DIFFABLE_TAGS:
            result.append(node)
            return
        for child in node.children:
            walk(child)

    for top in soup.contents:
        walk(top)

    return result
