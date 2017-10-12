import bisect

from graphite.compat import HttpResponse
from graphite.util import json
from graphite.storage import STORE

def tagSeries(request):
  if request.method != 'POST':
    return HttpResponse(status=405)

  path = request.POST.get('path')
  if not path:
    return HttpResponse(
      json.dumps({'error': 'no path specified'}),
      content_type='application/json',
      status=400
    )

  return HttpResponse(
    json.dumps(STORE.tagdb.tag_series(path)) if STORE.tagdb else 'null',
    content_type='application/json'
  )

def delSeries(request):
  if request.method != 'POST':
    return HttpResponse(status=405)

  path = request.POST.get('path')
  if not path:
    return HttpResponse(
      json.dumps({'error': 'no path specified'}),
      content_type='application/json',
      status=400
    )

  return HttpResponse(
    json.dumps(STORE.tagdb.del_series(path)) if STORE.tagdb else 'null',
    content_type='application/json'
  )

def findSeries(request):
  if request.method not in ['GET', 'POST']:
    return HttpResponse(status=405)

  queryParams = request.GET.copy()
  queryParams.update(request.POST)

  exprs = []
  # Normal format: ?expr=tag1=value1&expr=tag2=value2
  if len(queryParams.getlist('expr')) > 0:
    exprs = queryParams.getlist('expr')
  # Rails/PHP/jQuery common practice format: ?expr[]=tag1=value1&expr[]=tag2=value2
  elif len(queryParams.getlist('expr[]')) > 0:
    exprs = queryParams.getlist('expr[]')

  if not exprs:
    return HttpResponse(
      json.dumps({'error': 'no tag expressions specified'}),
      content_type='application/json',
      status=400
    )

  return HttpResponse(
    json.dumps(STORE.tagdb.find_series(exprs) if STORE.tagdb else [],
               indent=(2 if queryParams.get('pretty') else None),
               sort_keys=bool(queryParams.get('pretty'))),
    content_type='application/json'
  )

def tagList(request):
  if request.method != 'GET':
    return HttpResponse(status=405)

  return HttpResponse(
    json.dumps(STORE.tagdb.list_tags(tagFilter=request.GET.get('filter')) if STORE.tagdb else [],
               indent=(2 if request.GET.get('pretty') else None),
               sort_keys=bool(request.GET.get('pretty'))),
    content_type='application/json'
  )

def tagDetails(request, tag):
  if request.method != 'GET':
    return HttpResponse(status=405)

  return HttpResponse(
    json.dumps(STORE.tagdb.get_tag(tag, valueFilter=request.GET.get('filter')) if STORE.tagdb else None,
               indent=(2 if request.GET.get('pretty') else None),
               sort_keys=bool(request.GET.get('pretty'))),
    content_type='application/json'
  )

def autoComplete(request):
  if request.method not in ['GET', 'POST']:
    return HttpResponse(status=405)

  queryParams = request.GET.copy()
  queryParams.update(request.POST)

  exprs = []
  # Normal format: ?expr=tag1=value1&expr=tag2=value2
  if len(queryParams.getlist('expr')) > 0:
    exprs = queryParams.getlist('expr')
  # Rails/PHP/jQuery common practice format: ?expr[]=tag1=value1&expr[]=tag2=value2
  elif len(queryParams.getlist('expr[]')) > 0:
    exprs = queryParams.getlist('expr[]')

  if not exprs:
    return HttpResponse(
      json.dumps({'error': 'no tag expressions specified'}),
      content_type='application/json',
      status=400
    )

  result = {}

  if STORE.tagdb:
    searchedTags = set([STORE.tagdb.parse_tagspec(expr)[0] for expr in exprs])
    for path in STORE.tagdb.find_series(exprs):
      tags = STORE.tagdb.parse(path).tags
      for tag in tags:
        if tag in searchedTags:
          continue
        value = tags[tag]
        if tag not in result:
          result[tag] = [value]
          continue
        if value in result[tag]:
          continue
        if value >= result[tag][-1]:
          if len(result[tag]) >= 100:
            continue
          result[tag].append(value)
        else:
          bisect.insort_left(result[tag], value)
        if len(result[tag]) > 100:
          del result[tag][-1]

    result = {tag: result[tag] for tag in sorted(result.keys())[:100]}

  return HttpResponse(
    json.dumps(result,
               indent=(2 if queryParams.get('pretty') else None),
               sort_keys=bool(queryParams.get('pretty'))),
    content_type='application/json'
  )
