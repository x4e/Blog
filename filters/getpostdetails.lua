local utils = require 'pandoc.utils'

local stringify = function (el)
	if el then
		if type(el) == "table" then
			return el.t
				and utils.stringify(el)
				or utils.stringify(pandoc.Span(el))
		end
		return el
	end
	return ""
end

local arrToStr = function(arr)
	if arr then
		str = ""
		for k, v in pairs(arr) do
			-- assumes that stringify(v) does not contain a ","
			str = str .. stringify(v) .. ","
		end
		-- Remove trailing comma
		if str ~= "" then
			str = str:sub(0, str:len()-1)
		end
		return str
	end
	return "[]"
end

function Meta(meta)
	print(stringify(meta.title))
	print(stringify(meta.author))
	print(arrToStr(meta.keywords))
	print(stringify(meta.description))
	print(stringify(meta.date))
	print(arrToStr(meta.resources))
	os.exit(0)
end