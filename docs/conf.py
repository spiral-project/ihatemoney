# -*- coding: utf-8 -*-
import sys, os
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'I hate money'
copyright = u'2011, The \'I hate money\' team'

version = '1.0'
release = '1.0'

exclude_patterns = ['_build']
pygments_style = 'sphinx'

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pelican'
html_theme_options = { 'nosidebar': True }
