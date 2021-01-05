def em_surround(string, regex_escape=False):
    if regex_escape:
        return r'<em class="font-italic">%s<\/em>' % string
    else:
        return '<em class="font-italic">%s</em>' % string
