#!/bin/python3

import os
import subprocess
from pathlib import Path

rootPath = Path(".")

def execute(args):
	if isinstance(args, str):
		args = args.split(" ")
	res = subprocess.run(args, check=True, text=True, capture_output=True)
	if res.returncode != 0:
		raise Exception("Running command " + str(args) + " encountered code " + str(res.returncode))
	return res.stdout

def compile(posts, sourcePath):
	sourceStr = str(sourcePath)
	targetStr = sourceStr[:-3] + ".html" # switch extension from md to html
	targetPath = Path(targetStr)
	
	postDetails = execute("pandoc -L filters/getpostdetails.lua " + sourceStr).split("\n")
	wordCount = int(execute("pandoc -L filters/wordcount.lua " + sourceStr))
	timeToRead = wordCount // 220
	
	if sourceStr.endswith("/index.md"):
		posts.append({
			"path": sourceStr[:-9], # remove /index.html to get relative directory
			"time": str(timeToRead) + " mins",
			"title": postDetails[0],
			"author": postDetails[1],
			"keywords": postDetails[2],
			"description": postDetails[3],
			"date": postDetails[4],
		})
	
	if targetPath.exists():
		targetPath.unlink() # delete target file if it already exists
	
	print("Making " + sourceStr)
	args = [
		"pandoc",
		sourceStr,
		"-o", targetStr,
		"-t", "markdown+lists_without_preceding_blankline+emoji",
		"--standalone",
		"--highlight-style", "espresso",
		"--email-obfuscation", "references",
		"--mathml", "-L", "filters/math2svg.lua",
		"--template", "templates/post.html",
		"--css", "/resources/styles.css",
	]
	execute(args)

# First compile all the posts
posts = []
for file in rootPath.glob("*/*.md"):
	compile(posts, file)

# Now create index
def createIndex(posts):
	template = open("templates/index.html").read()
	
	def postToHtml(post):
		return "<div id='post'><h4><a href='" + post["path"] + "'>" + post["title"] + "</a></h4><p>" + post["description"] + "</p>"
	
	posts = map(postToHtml, posts)
	html = "\n".join(posts)
	
	return template.replace("$$POSTS$$", html)

index = createIndex(posts)
open("index.html", "w").write(index)

print(posts)
