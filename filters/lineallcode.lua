--- Adds lines to all code blocks even if not specified in the attributes

function CodeBlock(el)
	table.insert(el.attr.classes, "numberLines")
	return el
end
