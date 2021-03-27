#!/bin/python3

import os
import subprocess
import urllib
from pathlib import Path
from distutils.dir_util import mkpath, copy_tree, remove_tree
from datetime.datetime import strptime

# Execute the given command
def execute(args):
	if isinstance(args, str):
		args = args.split(" ")
	
	res = subprocess.run(args, text=True, capture_output=True)
	
	if res.returncode != 0:
		print(res.stderr)
		raise Exception("Running command " + str(args) + " encountered code " + str(res.returncode))
	
	return res.stdout




rootPath = Path(".").resolve()
rootStr = str(rootPath)
outPath = Path("out").resolve()
resourcePath = Path("resources").resolve()
tagPath = Path(outPath, "tag").resolve()

if outPath.exists():
	remove_tree(outPath)
	outPath.mkdir()


# Copy resources into the out folder
copy_tree(resourcePath, str(Path(outPath, "resources")))


def compile(posts, tags, sourcePath):
	sourceStr = str(sourcePath)
	# Get absolute source path, remove prefix of the rootDir, then swap extension from md to html
	targetPath = Path(outPath, str(sourcePath.resolve())[len(rootStr) + 1:-3] + ".html")
	targetStr = str(targetPath)
	
	mkpath(str(targetPath.parent.resolve()))
	
	# For now we assume all index.md files are blog posts
	if sourceStr.endswith("/index.md"):
		
		(title, author, keywords, description, date) = \
			execute("pandoc -L filters/getpostdetails.lua " + sourceStr).strip().split("\n")
		keywords = keywords.split(",")
		dateStr = date
		date = date.replace("th ", " ").replace("st ", " ").replace("rd ", " ")
		date = strptime(date, "%-d %B %Y")
		
		wordCount = int(execute("pandoc -L filters/wordcount.lua " + sourceStr))
		timeToRead = wordCount // 220 # estimate 220 wpm reading speed
		
		postDetails = {
			"path": targetStr[:-9], # remove /index.html to get relative directory
			"time": str(timeToRead) + " mins",
			"title": title,
			"author": author,
			"keywords": keywords,
			"description": description,
			"dateStr"; dateStr,
			"date": date,
		}
		
		posts.append(postDetails)
		
		for keyword in keywords:
			if keyword not in tags:
				tags[keyword] = [postDetails]
			else:
				tags[keyword].append(postDetails)
	
	print("Making " + sourceStr)
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
		"--template", "templates/post.html",
		"--css", "/resources/styles.css",
		"-L", "filters/lineallcode.lua",
	]
	execute(args)

# First compile all the posts
posts = []
tags = {}
for file in rootPath.glob("*/*.md"):
	compile(posts, tags, file)

# Sort posts based on the creation date
posts = sorted(posts, key=lambda item: item["date"])

# Sort tags based on the number of posts that use them
tags = dict(sorted(tags.items(), key=lambda item: len(item[1]), reverse=True))


# Now create index
def createIndex(tags):
	template = open("templates/index.html").read()
	
	def tagToHtml(tag):
		encoded = urllib.parse.quote(tag, safe='')
		return "<li><a href='/tag/{}'>{}</a> ({})</li>".format(encoded, tag, len(tags[tag]))
	tagsHtml = "\n".join(map(tagToHtml, tags.keys()))
	template = template.replace("$TAGS$", tagsHtml)
	
	# First generate a list of all posts
	def postToHtml(post):
		return "<div id='post'><h4><a href='/{}'>{}</a></h4><p>{}</p></div>".format(post["path"], post["title"], post["description"])
	postHtml = "\n".join(map(postToHtml, posts))
	template = template.replace("$POSTS$", postHtml)
	
	return template

def addPostsToIndex(index, posts):
	

def createIndex(posts):

index = createIndex(posts)
Path(outPath, "index.html").write_text(index)


# Create pages for each tag
def tagPage(tag, posts):
	return "<>"

for (tag, posts) in tags.items():
	html = tagPage(tag, posts)
	encoded = urllib.parse.quote(tag, safe='')
	outPath = Path(tagPath, "{}/index.html".format(encoded))
	mkpath(str(outPath.parent))
	outPath.write_text(tagPage(tag, posts))
