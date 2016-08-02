import re
import urllib2
import ssl
#import os

strURLRegex = r'(?i)(?:(?:https?|ftp):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])'

filtered = ['http://schemas.microsoft.com/office/2004/12/omml', 'http://www.w3.org/TR/REC-html40']
res = []
cleanUrls = []

url = demisto.get(demisto.args(), 'url')
if not url:
    url = demisto.incidents()[0]['details']

subject = demisto.get(demisto.args(), 'subject')
if not subject:
    subject = demisto.incidents()[0]['name']

body = """\
Hi whitelisting team,
We've received the following request to whitelist the below. Here are the details we have about the URL."""

suffix = """\


Cheers,
Your friendly security team"""

def ads(html,termlist):
    results = {}
    tags = re.findall("<[^/][^>]*>",html)
    for item in termlist.split('\n'):
        if not item.strip():
            continue
        if item.startswith('!') or item.startswith('[Adbl') or item.startswith('@@'):
            continue
        if item.startswith('###'):
            item = item[3:]
        if item.startswith('||'):
            item = item[2:item.find("^$")]
        for t in tags:
            if item in t:
                results[item] = (results[item] + 1) if item in results else 1
    return results

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

#os.environ["http_proxy"] = ""
#os.environ["https_proxy"] = ""

easylist = urllib2.urlopen('https://easylist.github.io/easylist/easylist.txt', context=ctx).read()

for m in re.finditer(strURLRegex, url, re.I):
    u = m.group(0)
    if u in filtered:
        continue
    if u in cleanUrls:
        continue
    if 'mailto:' in u:
        continue
    cleanUrls.append(u)
    rep = demisto.executeCommand('url', {'url': u})
    for entry in rep:
        if entry['Type'] != entryTypes['error'] and entry['ContentsFormat'] == formats['json']:
            c = entry['Contents']
            if entry['Brand'] == brands['xfe']:
                body += \
                    '\n\nURL: ' + demisto.gets(c, 'url.result.url') + \
                    '\nA: ' + demisto.gets(c, 'resolution.A') + \
                    '\nAAAA: ' + demisto.gets(c, 'resolution.AAAA') + \
                    '\nContry: ' + demisto.gets(c, 'country') + \
                    '\nCategories: ' + demisto.gets(c, 'url.result.cats') + \
                    '\nScore: ' + demisto.gets(c, 'url.result.score') + \
                    '\nMalwareCount: ' + demisto.gets(c, 'malware.count') + \
                    '\nProvider: ' + providers['xfe'] + \
                    '\nProviderLink: ' + 'https://exchange.xforce.ibmcloud.com/url/' + demisto.gets(c, 'url.result.url')
            if entry['Brand'] == brands['vt']:
                body += \
                    '\n\nURL: ' + demisto.gets(c, 'url') + \
                    '\nScanDate: ' + demisto.gets(c, 'scan_date') + \
                    '\nPositives: ' + demisto.gets(c, 'positives') + \
                    '\nTotal: ' + demisto.gets(c, 'total') + \
                    '\nProvider: ' + providers['vt'] + \
                    '\nProviderLink ' + demisto.gets(c, 'permalink')

    # Now, get the number of ads and external links
    html =  urllib2.urlopen(u, context=ctx).read()
    hits = ads(html, easylist)
    score = sum(hits.values())
    body += '\n\nTotal ads score is: ' + str(score)
    body += '\nTotal number of links is: ' + str(len(re.findall(strURLRegex, html, re.I)))

body += suffix
demisto.results(demisto.executeCommand('send-mail', {'to': demisto.args()['recipient'], 'subject': subject, 'body': body + '\n\n--------------------\n\n' + url}))
