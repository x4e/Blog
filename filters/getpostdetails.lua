local utils = require 'pandoc.utils'

local stringifyInlines = function (el)
	if el then
		return el.t
			and utils.stringify(el)
			or utils.stringify(pandoc.Span(el))
	end
	return ""
end

function Meta(meta)
	print(stringifyInlines(meta.title))
	print(stringifyInlines(meta.author))
	print(stringifyInlines(meta.keywords))
	print(stringifyInlines(meta.description))
	print(stringifyInlines(meta.date))
	os.exit(0)
end