var fromRE = /<b>From:.*href="mailto:(.*)"/ig;
var from = fromRE.exec(incidents[0].details);
var res = [];
var rep = executeCommand('pipl-search', {email: from[1]});
Array.prototype.push.apply(res, rep);
res.push({Contents: 'no', Type: entryTypes.note, ContentsFormat: formats.text});
return res;
