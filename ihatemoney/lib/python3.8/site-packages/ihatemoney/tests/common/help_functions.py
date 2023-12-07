from markupsafe import Markup


def em_surround(string, regex_escape=False):
    if regex_escape:
        return r'<em class="font-italic">%s<\/em>' % string
    else:
        return '<em class="font-italic">%s</em>' % string


def extract_link(data, start_prefix):
    base_index = data.find(start_prefix)
    start = data.find('href="', base_index) + 6
    end = data.find('">', base_index)
    link = Markup(data[start:end]).unescape()
    return link
