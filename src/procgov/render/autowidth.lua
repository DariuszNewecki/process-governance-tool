-- autowidth.lua - size table columns by content instead of pandoc's equal split.
-- Every column is at least as wide as its longest word (so nothing breaks mid-word);
-- the rest follows the amount of text per column. Wide tables (7+ columns) assume a
-- smaller font and tighter padding (procgov/render/postprocess.py sets them).
local stringify = pandoc.utils.stringify

-- width of the widest word, in average-character units (capitals are wider)
local function words_max(s)
  local m = 0
  for w in s:gmatch("%S+") do
    local l = 0
    for _, c in utf8.codes(w) do
      local ch = utf8.char(c)
      l = l + ((ch:match("%u") or ch == "W" or ch == "M") and 1.35 or 1.0)
    end
    if l > m then m = l end
  end
  return m
end

function Table(tbl)
  local n = #tbl.colspecs
  if n == 0 then return nil end
  -- characters (Arial, mixed case) across the 16 cm text width, and cell padding in characters:
  -- 8 pt with tight padding for wide tables (procgov/render/postprocess.py), 10 pt otherwise
  local wide = n >= 7
  local line_chars = wide and 95 or 76
  local pad = wide and 2.4 or 3
  local maxl, sum, cnt, word = {}, {}, {}, {}
  for i = 1, n do maxl[i], sum[i], cnt[i], word[i] = 0, 0, 0, 0 end
  local function scan(rows)
    for _, row in ipairs(rows) do
      for i, cell in ipairs(row.cells) do
        if i <= n then
          local s = stringify(cell.contents)
          local l = utf8.len(s) or #s
          if l > maxl[i] then maxl[i] = l end
          local wm = words_max(s)
          if wm > word[i] then word[i] = wm end
          sum[i] = sum[i] + l; cnt[i] = cnt[i] + 1
        end
      end
    end
  end
  scan(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do scan(body.body) end
  local frac, total, wsum, weight = {}, 0, 0, {}
  for i = 1, n do
    local avg = cnt[i] > 0 and sum[i] / cnt[i] or 0
    weight[i] = math.max(0.5 * avg + 0.5 * math.min(maxl[i], 45), 1)
    wsum = wsum + weight[i]
  end
  for i = 1, n do
    frac[i] = math.max((word[i] * 1.12 + pad) / line_chars, weight[i] / wsum)  -- 1.15: bold headers, capitals
    total = total + frac[i]
  end
  for i = 1, n do
    tbl.colspecs[i] = { tbl.colspecs[i][1], frac[i] / total }
  end
  return tbl
end
