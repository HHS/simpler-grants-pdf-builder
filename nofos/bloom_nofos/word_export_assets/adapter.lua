-- Bounded adapter: intentionally suppress wrapper HTML title; preserve explicit
-- Builder export break spans. No CSS layout emulation or content rewriting.
function Meta(meta)
  meta.title = nil
  return meta
end
function Span(el)
  if el.classes:includes('page-break') then
    return pandoc.RawInline('openxml', '<w:r><w:br w:type="page"/></w:r>')
  end
end
function Header(el)
  if el.classes:includes('page-break-before') then
    return {pandoc.RawBlock('openxml', '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'), el}
  end
end
