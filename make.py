#!/bin/python3

import os
import subprocess
import urllib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from distutils.dir_util import mkpath, copy_tree, remove_tree

# Execute the given command
def execute(args):
	if isinstance(args, str):
		args = args.split(" ")
	
	res = subprocess.run(args, text=True, capture_output=True)
	
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
	
	def __repr__(self):
		return self.title



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


# Gather details about all posts
def gatherPosts(rootPath):
	# Array of all posts
	posts = []
	# Map of tags to posts
	tags = {}
	
	# We assume every index.md file is a blog post
	for sourcePath in rootPath.glob("*/index.md"):
		sourceStr = str(sourcePath)
		
		relativePath = sourceStr[len(rootStr):]
		
		# Use the lua filter to get post details from the yaml metadata
		(title, author, keywords, description, date) = \
			execute(["pandoc", "-L", "filters/getpostdetails.lua", sourceStr]).strip().split("\n")
		keywords = frozenset(keywords.split(","))
		dateStr = date
		date = date.replace("th ", " ").replace("st ", " ").replace("rd ", " ")
		date = datetime.strptime(date, "%d %B %Y")
	
		wordCount = int(execute("pandoc -L filters/wordcount.lua " + sourceStr))
		timeToRead = wordCount // 220 # estimate 220 wpm reading speed
	
		postDetails = Post(
			path= relativePath[:-8], # remove /index.md to get relative directory
			time= str(timeToRead) + " mins",
			title= title,
			author= author,
			keywords= keywords,
			description= description,
			dateStr= dateStr,
			date= date,
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
def compile(sourcePath):
	sourceStr = str(sourcePath)
	# Get absolute source path, remove prefix of the rootDir, then swap extension from md to html
	targetPath = Path(outPath, str(sourcePath.resolve())[len(rootStr) + 1:-3] + ".html")
	targetStr = str(targetPath)
	
	mkpath(str(targetPath.parent.resolve()))
	
	print("Compiling " + sourceStr)
	args = [
		"pandoc",
		sourceStr,
		"-o", targetStr,
		"-f", "markdown+lists_without_preceding_blankline+emoji+backtick_code_blocks+fenced_code_attributes",
		"--standalone",
		"--highlight-style", "espresso",
		"--email-obfuscation", "references",
		"--indented-code-classes", "numberLines",
		"--mathml", "-L", "filters/math2svg.lua",
		"--template", "templates/post_temp.html",
		"--css", "/resources/styles.css",
		"--css", "/resources/post.css",
		"-L", "filters/lineallcode.lua",
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
	encoded = urllib.parse.quote(post.path, safe='/')
	tags = ", ".join(map(tagToLink, post.keywords))
	return """
	<div id='post'>
		<h4>
			<a href='{}'>{}</a>
		</h4>
		<small><span class='post-date'>{}</span> - <span class='post-tags'>{}</span></small>
		<p>{}</p>
	</div>
	""".format(encoded, post.title, post.dateStr, tags, post.description)
postsToHtml = {post: postToHtml(post) for post in posts}
allPostsHtml = "\n".join(postsToHtml.values())


# We need to add the tags html to the templates, they often contain it in the navbar
Path("templates/post_temp.html")\
	.write_text(\
		Path("templates/post.html")\
			.read_text()\
			.replace("$TAGS$", allTagsHtml)\
	)

# Do the index's templating
Path(outPath, "index.html")\
	.write_text(\
		Path("templates/index.html")\
			.read_text()\
			.replace("$TAGS$", allTagsHtml)\
			.replace("$POSTS$", allPostsHtml)\
	)


# Compile all markdown files
for file in rootPath.glob("*/*.md"):
	compile(file)


# We can now delete post_temp
Path("templates/post_temp.html").unlink()


tagTemplate = Path("templates/tag.html").read_text()\
	.replace("$TAGS$", allTagsHtml)

# Create pages for each tag
for (tag, posts) in tags.items():
	posts = "\n".join(map(lambda post: postsToHtml[post], posts))
	html = tagTemplate\
		.replace("$TAG$", tag)\
		.replace("$POSTS$", posts)
	outPath = Path(tagPath, "{}/index.html".format(tag))
	mkpath(str(outPath.parent))
	outPath.write_text(html)
