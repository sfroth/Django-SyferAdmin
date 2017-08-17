"""
Supports the responsive embedding of web video URLs (currently YouTube and Vimeo are supported)
Based on https://github.com/chrisdev/python-markdown-flex-video

Youtube Test Example:

>>> s = "http://www.youtube.com/watch?v=E88d4e1gYh0&feature=g-logo-xit"
>>> markdown.markdown(s, ['flex_video']) #doctest: +NORMALIZE_WHITESPACE
	u'<p>\\n<div class="flex-video">\\n<iframe frameborder="0" height="315" src="http://www.youtube.com/v/E88d4e1gYh0&amp;feature=g-logo-xit" width="420"></iframe>\\n</div>\\n</p>'

>>> markdown.markdown(s, ['flex_video(orientation=widescreen)']) #doctest: +NORMALIZE_WHITESPACE
	u'<p>\\n<div class="flex-video">\\n<iframe frameborder="0" height="315" src="http://www.youtube.com/v/E88d4e1gYh0&amp;feature=g-logo-xit" width="560"></iframe>\\n</div>\\n</p>'
"""

import markdown

try:
	from markdown.util import etree
except:
	from markdown import etree

from ..media import Video as MediaVideo

version = "0.0.1"


class VideoExtension(markdown.Extension):
	"Actual extension used by markdown"

	def add_inline(self, md, name, klass, re):
		pattern = klass(re)
		pattern.md = md
		pattern.ext = self
		md.inlinePatterns.add(name, pattern, "<reference")

	def extendMarkdown(self, md, md_globals):
		self.add_inline(md, 'vimeo', Video,
			r'!\[[^\]]*\]\((https?://(www.|)vimeo\.com/(?P<vimeoid>\d+))\)\S*')
		self.add_inline(md, 'youtube', Video,
			r'!\[[^\]]*\]\((https?://(www\.)?youtu(be\.com/watch\?\S*v=|\.be/)(?P<youtubeargs>[A-Za-z0-9#_&=-]+))\)\S*')


class Video(markdown.inlinepatterns.Pattern):
	def handleMatch(self, m):
		return video(MediaVideo(url=m.group(2)).video.url('iframe_url'))


def video(url):
	"""
	<div class="video">
		<iframe width="420" height="315" src="http://www.youtube.com/embed/9otNWTHOJi8" frameborder="0" allowfullscreen></iframe>
	</div>
	"""
	obj = etree.Element('div')
	obj.set('class', "video")
	iframe = etree.Element('iframe')
	iframe.set('src', url)
	iframe.set('frameborder', "0")
	obj.append(iframe)
	return obj


def makeExtension(configs=None):
	return VideoExtension(configs=configs)
