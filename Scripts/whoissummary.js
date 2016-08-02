// A simple example script for parsing WHOIS data

// Regexp for matching "<key>: <value>" pattern
var re = /^([a-zA-Z\s]+):\s(.+)$/;

function stringStartsWith (string, prefix) {
    return string.slice(0, prefix.length) == prefix;
}

var res = executeCommand('whois', {'using-brand': 'whois', 'query':args.query});
var lines = res[0].Contents.split('\n');

var out = '';
for (var i=0; i < lines.length; ++i) {
    var str = lines[i];
    str.trim();
    if (str.length === 0) {
        continue;
    }

    // Skip '%' lines
    if (stringStartsWith(str, '%')) {
        continue;
    }

    // Stop when reaching the "last update" line
    if (stringStartsWith(str, '>>> Last update')) {
        break;
    }

    // See if the line matches the regex
    if (re.test(str)) {
        out += str + '\n';
    }
}

return out;
