# Blog

Where I write stuff.

Hosted at [blog.binclub.dev](https://blog.binclub.dev).

## Technical

The blog is statically generated using [pandoc](https://pandoc.org) with some custom templates to convert the markdown blog files to html to be served.

Since the blog is completely statically generated (even code highlighting and mathjax expressions), no JavaScript is required to view the blog.
If JavaScript is present then a comment section can be loaded, but this is not necessary.

## Requirements

* pandoc
* nodejs
* mathjax-node-cli (npm package)

## More Info

A lot of these posts contain code samples. 

Some of them will rely upon [jasm](https://wiki.openjdk.java.net/display/CodeTools/asmtools) for assembling JVM class files.
A precompiled binary is provided in the root directory of this project.
To compile a .jasm file use `java -jar asmtools.jar jasm file.jasm`.
