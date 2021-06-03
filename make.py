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
		print("CMD:")
		cmdStr = "\""
		for arg in args:
			cmdStr += arg + "\" \""
		cmdStr = cmdStr[:-2]
		print(cmdStr)
		print("STDOUT:")
		print(res.stdout)
		print("STDERR:")
		print(res.stderr)
		raise Exception("Running command " + str(args) + " encountered code " + str(res.returncode))
	
	return res.stdout

def parseLuaArr(text):
	if not text or text == "[]":
		return []
	else:
		return text.split(",")

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
	resources: frozenset
	unlisted: bool
	
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


DATETIME_FORMAT = "%Y-%m-%dT%T%zZ"

pandoc = "pandoc"
# Check if there is a pandoc binary in the current folder
if Path("./pandoc").exists():
	pandoc = "./pandoc"
# Also allow overriding by env variables
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


templates = ["index", "posts", "post", "tag", "404"]
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
		(title, author, keywords, description, date, resources, unlisted) = \
			execute([pandoc, "--lua-filter", "filters/getpostdetails.lua", sourceStr]).strip().split("\n")
		keywords = frozenset(parseLuaArr(keywords))
		resources = frozenset(parseLuaArr(resources))
		dateStr = date
		date = date.replace("th ", " ").replace("st ", " ").replace("rd ", " ")
		date = datetime.strptime(date, "%d %B %Y")
		unlisted = unlisted == "true"
	
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
			resources= resources,
			unlisted= unlisted
		)
		
		posts.append(postDetails)
		
		# Create symlinks to the resources
		if resources:
			# Remove the beginning "/" as this will resolve as root on a filesystem
			relPath = postDetails.path[1:]
			targetPath = Path(outPath, relPath)
			mkpath(str(targetPath.parent.resolve()))
			mkpath(str(targetPath.resolve()))
			
			for resource in resources:
				resPath = Path(sourcePath.parent, resource)
				resSymPath = Path(targetPath, resource)
				resSymPath.symlink_to(resPath, target_is_directory=False)
	
	# Sort posts based on the creation date
	posts = sorted(posts, key=lambda item: item.date, reverse=True)
	
	for post in posts:
		if post.unlisted:
			continue
		
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
	
	print("Compiling", sourceStr, "to", targetStr)
	args = [
		pandoc,
		sourceStr,
		"-o", targetStr,
		"-f", "commonmark_x+yaml_metadata_block",
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
print("Generating tag links")
def tagToLink(tag):
	encoded = urllib.parse.quote(tag, safe='/')
	return "<a href='/tag/{}'>{}</a>".format(encoded, tag)
tagsToHtml = {tag: "{} ({})".format(tagToLink(tag), len(tags[tag])) for tag in tags.keys()}
allTagsHtml = ", ".join(tagsToHtml.values())

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
postsToHtml = {post: postToHtml(post) for post in posts if not post.unlisted}
allPostsHtml = "\n".join(postsToHtml.values())


def compileTemplate(templateName, css=[], title="x4e's website"):
	templatePath = Path(rootPath, "templates/{}_tmp.html".format(templateName)).resolve()
	if templateName == "index":
		templateOut = Path(outPath, "{}.html".format(templateName)).resolve()
	else:
		templateOut = Path(outPath, "{}/index.html".format(templateName)).resolve()
	mkpath(str(templateOut.parent))
	
	print("Compiling", str(templatePath))
		
	command = [
		pandoc,
		"-o", str(templateOut),
		"-V", "TAGS={}".format(allTagsHtml),
		"-V", "POSTS={}".format(allPostsHtml),
		"-V", "pagetitle={}".format(title),
		"-V", "description=Posts about reverse engineering",
		"-V", "keywords=x4e, blog, reverse engineering",
		"--standalone",
		"--highlight-style", "espresso",
		"--email-obfuscation", "references",
		"--indented-code-classes", "numberLines",
		"--template", str(templatePath),
		"--css", "/resources/styles.css",
	]
	
	for sheet in css:
		command.append("--css")
		command.append("/resources/{}.css".format(sheet))
	
	execute(command, input="")


# index.html
compileTemplate("index", ["index"])

# 404.html
compileTemplate("404", title="404 Not Found")

# posts.html
compileTemplate("posts", title="x4e's blog posts")

# Compile all markdown files
for file in rootPath.glob("*/*.md"):
	compileMarkdown(file, allTagsHtml)

print("Compiling tags")
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

atom.appendChild(createText(xml, "id", "https://blog.binclub.dev/"))
atom.appendChild(createText(xml, "title", "x4e's blog"))
atom.appendChild(createText(xml, "subtitle", "Posts about reverse engineering"))
atom.appendChild(createText(xml, "updated", date.today().strftime(DATETIME_FORMAT)))
atom.appendChild(createText(xml, "link", None, href="https://blog.binclub.dev/", rel="alternate"))
atom.appendChild(createText(xml, "link", None, href="https://blog.binclub.dev/feed.xml", rel="self"))
atom.appendChild(createText(xml, "category", None, term="x4e"))
atom.appendChild(createText(xml, "category", None, term="blog"))
atom.appendChild(createText(xml, "category", None, term="reverse engineering"))

author = xml.createElement("author")
author.appendChild(createText(xml, "name", "x4e"))
author.appendChild(createText(xml, "email", "x4e_x4e@protonmail.com"))
author.appendChild(createText(xml, "uri", "https://blog.binclub.dev/"))
atom.appendChild(author)

for post in posts:
	uri = "https://blog.binclub.dev{}".format(post.path)
	item = xml.createElement("entry")
	item.appendChild(createText(xml, "id", uri))
	item.appendChild(createText(xml, "title", post.title))
	item.appendChild(createText(xml, "published", post.date.strftime(DATETIME_FORMAT)))
	item.appendChild(createText(xml, "updated", post.date.strftime(DATETIME_FORMAT)))
	item.appendChild(createText(xml, "summary", post.description))
	item.appendChild(createText(xml, "link", None, href=uri, rel="alternate"))
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
