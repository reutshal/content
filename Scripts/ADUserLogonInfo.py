# Optional arguments and default values
attrs = 'name,displayname,lastlogon,lastlogoff,logoncount,badPasswordTime,badPwdCount,lastLogonTimestamp,pwdLastSet,whenCreated,whenChanged,memberOf'
if demisto.get(demisto.args(), 'attributes'):
    attrs += "," + demisto.args()['attributes']
userDN = ''
resp = ''
if demisto.get(demisto.args(), 'dn'):
    userDN = demisto.args()['dn']
elif demisto.get(demisto.args(), 'name'):
    resp = demisto.executeCommand( 'ad-search', { 'filter' : "(&(objectCategory=User)(name=" + demisto.args()['name'] + "))" } )
elif demisto.get(demisto.args(), 'email'):
    resp = demisto.executeCommand( 'ADGetUsersByEmail', { 'email' : demisto.args()['email'] } )
else:
    demisto.results( { 'Type' : entryTypes['error'], 'ContentsFormat' : formats['text'], 'Contents' : 'You must provide either dn, name or email as argument!' } )
    sys.exit(0)

if type(resp)==list and len( [ r for r in resp if isError(r) ] ) > 0 :
    demisto.results( { 'Type' : entryTypes['error'], 'ContentsFormat' : formats['text'], 'Contents' : 'Error returned by ad command: ' + r['Contents'] } )
    sys.exit(0)

if type(resp)==list and len(resp)==1 and type(resp[0])==dict and 'Contents' in resp[0] and type(resp[0]['Contents'])==list and len(resp[0]['Contents'])==1 and type(resp[0]['Contents'][0])==dict and 'dn' in resp[0]['Contents'][0]:
    userDN = resp[0]['Contents'][0]['dn']
else:
    demisto.results( { 'Type' : entryTypes['error'], 'ContentsFormat' : formats['text'], 'Contents' : 'Unexpected output from ad command.' } )
    sys.exit(0)

if userDN:
    filterstr = r"(&(objectClass=User)(distinguishedName=" + userDN + "))"
    resAD = demisto.executeCommand( 'ad-search', { 'filter' : filterstr, 'attributes' : attrs } )
    try:
        for m in resAD:
            if isError(m):
                continue
            for f in [ 'lastlogon' , 'lastlogoff' , 'pwdLastSet' , 'badPasswordTime' , 'lastLogonTimestamp' ]:
                if m['Contents'][0][f] == "0":
                    m['Contents'][0][f] = "N/A"
                else:
                    m['Contents'][0][f] = FormatADTimestamp( m['Contents'][0][f] )
            for f in [ 'whenChanged' , 'whenCreated' ]:
                m['Contents'][0][f] = PrettifyCompactedTimestamp( m['Contents'][0][f] )
        demisto.results ( resAD )
    except:
        demisto.results( { 'Type' : entryTypes['error'], 'ContentsFormat' : formats['text'], 'Contents' : 'Error occurred while parsing output from ad command. Invalid output:\n' + str( resAD ) }

else:
    demisto.results( { 'Type' : entryTypes['error'], 'ContentsFormat' : formats['text'], 'Contents' : 'User not found.' } )
