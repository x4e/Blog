#!/usr/bin/python3

import os
import urllib
import atexit
import subprocess
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass
from distutils.dir_util import mkpath, copy_tree, remove_tree

# Execute the given command
def execute(args, input=None):
	if isinstance(args, str):
		args = args.split(" ")
	
	res = subprocess.run(args, input=input, text=True, capture_output=True)
	
	if res.returncode != 0:
		print(res.stderr)
		raise Exception("Running command " + str(args) + " encountered code " + str(res.returncode))
	
	return res.stdout

@dataclass(frozen=True, repr=False)
class Post(object):
	path: str
	time: str
	title: str
	author: str
	keywords: frozenset
	description: str
	dateStr: str
	date: datetime
	content: str
	
	def __repr__(self):
		return self.title


# A list of files to be deleted when the program executes
removeOnExit = []
def deleteRemoveOnExists():
	for remove in removeOnExit:
		if remove.exists():
			if remove.is_dir():
				remove_tree(remove)
			else:
				remove.unlink()
	removeOnExit.clear()
atexit.register(deleteRemoveOnExists)


pandoc = "pandoc"
if "PANDOC" in os.environ:
	pandoc = os.environ["PANDOC"]

rootPath = Path(".").resolve()
rootStr = str(rootPath)
outPath = Path("out").resolve()
resourcePath = Path("resources").resolve()
tagPath = Path(outPath, "tag").resolve()

if outPath.exists():
	remove_tree(outPath)
outPath.mkdir()


# Create a symlink in the out folder to the resources
Path(outPath, "resources").symlink_to(resourcePath, target_is_directory=True)


templates = ["index", "post", "tag", "404"]
mainTemplate = Path(rootPath, "templates/maintemplate.html").read_text()
for template in templates:
	origPath = Path(rootPath, "templates/{}.html".format(template))
	tmpPath = Path(rootPath, "templates/{}_tmp.html".format(template))
	removeOnExit.append(tmpPath)
	tmpPath.write_text(mainTemplate.replace("$BODY$", origPath.read_text()))


# Gather details about all posts
def gatherPosts(rootPath):
	# Array of all posts
	posts = []
	# Map of tags to posts
	tags = {}
	
	# We assume every index.md file is a blog post
	for sourcePath in rootPath.glob("*/index.md"):
		sourceStr = str(sourcePath)
		print("Indexing", sourceStr)
		
		relativePath = sourceStr[len(rootStr):]
		
		# Use the lua filter to get post details from the yaml metadata
		(title, author, keywords, description, date) = \
			execute([pandoc, "--lua-filter", "filters/getpostdetails.lua", sourceStr]).strip().split("\n")
		keywords = frozenset(keywords.split(","))
		dateStr = date
		date = date.replace("th ", " ").replace("st ", " ").replace("rd ", " ")
		date = datetime.strptime(date, "%d %B %Y")
	
		wordCount = int(execute([pandoc, "--lua-filter", "filters/wordcount.lua", sourceStr]))
		timeToRead = wordCount // 220 # estimate 220 wpm reading speed
		
		content = sourcePath.read_text()
		content = content[content.index("---", 3) + 3:].strip() # trim the header from the content
		
		postDetails = Post(
			path= relativePath[:-8], # remove /index.md to get relative directory
			time= str(timeToRead) + " mins",
			title= title,
			author= author,
			keywords= keywords,
			description= description,
			dateStr= dateStr,
			date= date,
			content= content,
		)
		
		posts.append(postDetails)
	
	# Sort posts based on the creation date
	posts = sorted(posts, key=lambda item: item.date, reverse=True)
	
	for post in posts:
		for keyword in post.keywords:
			if keyword not in tags:
				tags[keyword] = [post]
			else:
				tags[keyword].append(post)
	
	# Sort tags based on the number of posts that use them
	tags = dict(sorted(tags.items(), key=lambda item: len(item[1]), reverse=True))
	
	return (posts, tags)

# Compile a markdown file at sourcePath
def compileMarkdown(sourcePath, allTagsHtml):
	sourceStr = str(sourcePath)
	# Get absolute source path, remove prefix of the rootDir, then swap extension from md to html
	targetPath = Path(outPath, str(sourcePath.resolve())[len(rootStr) + 1:-3] + ".html")
	targetStr = str(targetPath)
	
	mkpath(str(targetPath.parent.resolve()))
	
	print("Compiling", sourceStr)
	args = [
		pandoc,
		sourceStr,
		"-o", targetStr,
		"-f", "markdown+lists_without_preceding_blankline+emoji+backtick_code_blocks+fenced_code_attributes",
		"-V", "TAGS={}".format(allTagsHtml),
		"--standalone",
		"--highlight-style", "espresso",
		"--email-obfuscation", "references",
		"--indented-code-classes", "numberLines",
		"--mathml", "--lua-filter", "filters/math2svg.lua",
		"--template", "templates/post_tmp.html",
		"--css", "/resources/styles.css",
		"--css", "/resources/post.css",
		"--lua-filter", "filters/lineallcode.lua",
	]
	execute(args)

# First gather information about all the posts
posts, tags = gatherPosts(rootPath)


# Generate html representation of every tag
def tagToLink(tag):
	encoded = urllib.parse.quote(tag, safe='/')
	return "<a href='/tag/{}'>{}</a>".format(encoded, tag)
tagsToHtml = {tag: "<li>{} ({})</li>".format(tagToLink(tag), len(tags[tag])) for tag in tags.keys()}
allTagsHtml = "\n".join(tagsToHtml.values())

# Generate html representation of every post
def postToHtml(post):
	# encode any non ascii chars
	encodedTitle = post.title.encode('ascii', 'xmlcharrefreplace').decode()
	encodedDesc = post.description.encode('ascii', 'xmlcharrefreplace').decode()
	encodedPath = urllib.parse.quote(post.path, safe='/')
	tags = ", ".join(map(tagToLink, post.keywords))
	return """
	<div id='post'>
		<h4>
			<a href='{}'>{}</a>
		</h4>
		<small><span class='post-date'>{}</span> - <span class='post-tags'>{}</span></small>
		<p>{}</p>
	</div>
	""".format(encodedPath, encodedTitle, post.dateStr, tags, encodedDesc)
postsToHtml = {post: postToHtml(post) for post in posts}
allPostsHtml = "\n".join(postsToHtml.values())


# index.html
indexTemplate = Path(rootPath, "templates/index_tmp.html").resolve()
indexOut = Path(outPath, "index.html").resolve()
print("Compiling", str(indexTemplate))
execute([
	pandoc,
	"-o", str(indexOut),
	"-V", "TAGS={}".format(allTagsHtml),
	"-V", "POSTS={}".format(allPostsHtml),
	"-V", "pagetitle=x4e's blog",
	"-V", "description=Posts about reverse engineering",
	"-V", "keywords=x4e, blog, reverse engineering",
	"--standalone",
	"--highlight-style", "espresso",
	"--email-obfuscation", "references",
	"--indented-code-classes", "numberLines",
	"--template", str(indexTemplate),
	"--css", "/resources/styles.css",
	"--css", "/resources/index.css",
], input="")

# 404.html
notFoundTemplate = Path(rootPath, "templates/404_tmp.html").resolve()
notFoundOut = Path(outPath, "404.html").resolve()
print("Compiling", str(notFoundTemplate))
execute([
	pandoc,
	"-o", str(notFoundOut),
	"-V", "TAGS={}".format(allTagsHtml),
	"-V", "POSTS={}".format(allPostsHtml),
	"-V", "pagetitle=404 not found",
	"-V", "description=Posts about reverse engineering",
	"-V", "keywords=x4e, blog, reverse engineering",
	"--standalone",
	"--highlight-style", "espresso",
	"--email-obfuscation", "references",
	"--indented-code-classes", "numberLines",
	"--template", str(notFoundTemplate),
	"--css", "/resources/styles.css",
	"--css", "/resources/index.css",
], input="")


# Compile all markdown files
for file in rootPath.glob("*/*.md"):
	compileMarkdown(file, allTagsHtml)

# Create pages for each tag
for (tag, tagPosts) in tags.items():
	postsHtml = "\n".join(map(lambda post: postsToHtml[post], tagPosts))
	tagOutPath = Path(tagPath, "{}/index.html".format(tag)).resolve()
	mkpath(str(tagOutPath.parent))
	execute([
		pandoc,
		"-o", str(tagOutPath),
		"-V", "TAGS={}".format(allTagsHtml),
		"-V", "TAG={}".format(tag),
		"-V", "POSTS={}".format(postsHtml),
		"-V", "pagetitle=Posts tagged with {}".format(tag),
		"-V", "description=All posts with {} tag".format(tag),
		"-V", "keywords=x4e, blog, reverse engineering, {}".format(tag),
		"--standalone",
		"--highlight-style", "espresso",
		"--email-obfuscation", "references",
		"--indented-code-classes", "numberLines",
		"--template", "templates/tag_tmp.html",
		"--css", "/resources/styles.css",
		"--css", "/resources/index.css",
	], input="")

from xml.dom import minidom

def createText(document, elementName, text, **kwargs):
	out = document.createElement(elementName)
	if text != None:
		out.appendChild(document.createTextNode(text))
	for key in kwargs:
		out.setAttribute(key, kwargs[key])
	return out

xmlOut = Path(outPath, "feed.xml").resolve()
print("Compiling", xmlOut)
xml = minidom.Document()
atom = createText(xml, "feed", None, xmlns="http://www.w3.org/2005/Atom")
atom.xmlns = "http://www.w3.org/2005/Atom"

atom.appendChild(createText(xml, "id", "https://blog.binclub.dev"))
atom.appendChild(createText(xml, "title", "x4e's blog"))
atom.appendChild(createText(xml, "subtitle", "Posts about reverse engineering"))
atom.appendChild(createText(xml, "updated", str(date.today())))
atom.appendChild(createText(xml, "link", None, href="https://blog.binclub.dev", rel="alternate"))
atom.appendChild(createText(xml, "link", None, href="https://blog.binclub.dev/feed.xml", rel="self"))
atom.appendChild(createText(xml, "category", None, term="x4e"))
atom.appendChild(createText(xml, "category", None, term="blog"))
atom.appendChild(createText(xml, "category", None, term="reverse engineering"))

author = xml.createElement("author")
author.appendChild(createText(xml, "name", "x4e"))
author.appendChild(createText(xml, "email", "x4e_x4e@protonmail.com"))
author.appendChild(createText(xml, "uri", "https://blog.binclub.dev"))
atom.appendChild(author)

for post in posts:
	uri = "https://blog.binclub.dev{}".format(post.path)
	item = xml.createElement("entry")
	item.appendChild(createText(xml, "id", uri))
	item.appendChild(createText(xml, "title", post.title))
	item.appendChild(createText(xml, "published", str(post.date)))
	item.appendChild(createText(xml, "updated", str(post.date)))
	item.appendChild(createText(xml, "summary", post.description))
	item.appendChild(createText(xml, "link", None, href=uri, rel="alternate"))
	item.appendChild(createText(xml, "language", "en-GB"))
	for keyword in post.keywords:
		item.appendChild(createText(xml, "category", None, term=keyword))
	atom.appendChild(item)
	
	content = post.content
	content.replace("\n", "<br>\n")
	cdata = xml.createCDATASection(content)
	contentNode = createText(xml, "content", None, type="text/markdown", src=uri)
	contentNode.appendChild(cdata)
	item.appendChild(contentNode)

xml.appendChild(atom)
xmlOut.write_text(xml.toprettyxml(indent ="\t"))
