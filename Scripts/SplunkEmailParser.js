var body = args.body ? args.body : incidents[0].details;
var subject = args.subject ? args.subject : incidents[0].name;

function parseBody() {
    var lines = body.split(/\r*\n/);
    var header="";
    var content = "";
    for (var i =0;  i < lines.length; i++) {
      var line = lines[i];
      if (line.toLowerCase().indexOf("view results") >=0&& lines.length > i+3) {
        header = lines[i+1];
        content = lines[i+3];
        break;
      }
    }
    return {header: header,content: content};
}

function headerIndex(header, column) {
    lowerHeader = header.toLowerCase();
    lowerColumn = column.toLowerCase();
    columns = lowerHeader.split(/\s+/);
    for (var i = 0; i < columns.length; i++){
      if (columns[i]===lowerColumn) {
        var start = lowerHeader.indexOf(lowerColumn);
        var end = -1;
        if (columns.length > i+1 && columns[i + 1]!=="") {
           end = lowerHeader.indexOf(columns[i + 1], start);
        }
        return {start:start,end:end};
      }
    }
    return {start:-1,end:-1};
}

function getContent(content,start,end) {
    lastIndex = end ;
    if (lastIndex===-1) {
      lastIndex = content.length
    }
    if (start === -1) {
        return "";
    }
    return content.substring(start,lastIndex).trim();
}

function getField(field) {
    mail = parseBody();
    dataBounderies = headerIndex(mail.header,field);
    return getContent(mail.content,dataBounderies.start,dataBounderies.end);
}

var type = getField('sourcetype');
var details = getField('_raw');
var severity = getField('level');
var systems = getField('host');
var incName = subject;

return setIncident({
                        type: type,
                        details: details,
                        severity: severity,
                        incName: incName,
                        systems: systems
                    });