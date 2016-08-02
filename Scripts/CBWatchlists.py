# args: id - Optional - only show the watchlist with this specific ID
cols = ['name','search_query','id','enabled','search_timestamp','last_hit','last_hit_count','total_hits']
fullcols = ['alliance_id', 'date_added', 'enabled', 'from_alliance', 'group_id', 'id', 'index_type', 'last_hit', 'last_hit_count', 'name', 'readonly', 'search_query', 'search_timestamp', 'total_hits', 'total_tags']
res = []
resCmd1 = demisto.executeCommand("cb-watchlist-get", {"watchlist-id" : demisto.args()["id"]} if "id" in demisto.args() else {})
for entry in resCmd1:
    if isError(entry):
        res.append(entry)
    else:
        matches = entry["Contents"]
        if matches:
            if type(matches)==dict:
                matches = [matches]
            filtered_matches = [{ k: m[k] for k in cols if k in m } for m in matches]
            res.append(  { "Type" : entryTypes["note"], "ContentsFormat" : formats["table"], "Contents" : filtered_matches } )
        else:
            res.append(  { "Type" : entryTypes["note"], "ContentsFormat" : formats["text"], "Contents" : "No matches." } )
demisto.results(res)
