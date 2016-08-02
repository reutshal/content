//Script to query carbon black servers:
//type must be either 'process' or 'binary'
//can provide query & number of rows to return

function formatresults(rows, columns) {
    var table = [];
    for (var index in rows) {
        var row = rows[index];
        if (typeof (row) === "object") {
            tablerow = {};
            for (var name in row) {
                var value = row[name];
                if (typeof (value) === "object") {
                    value = JSON.stringify(value);
                }
                var columnIndex = columns.indexOf(name);
                var columnName;
                if (columnIndex !== -1) {
                    columnName = columnIndex.toString() + ". " + name;
                } else {
                    columnName = name;
                }
                tablerow[columnName] = value;
            }
            table.push(tablerow);
        }
    }
    return table;
}

var output = [];
var searchType = args.type ? args.type : 'process';
if ((searchType !== 'process') && (searchType !== 'binary')) {
    output.push({ContentsFormat: formats.text, Type: entryTypes.error, Contents: "Error! type must be 'process' or 'binary"});
} else {
    var res = [];
    var columns = [];
    if (searchType === 'process') {
        columns = ["hostname", "username", "process_pid", "path", "process_md5", "start", "os_type", "parent_pid", "sensor_id"];
    } else {
        columns = ["md5", "observed_filename", "original_filename", "is_executable_image", "endpoint", "signed", "os_type"];
    }
    myArgs = {
      start: args.start ? args.start : '0',
      rows: args.rows ? args.rows : '20'
    };
    if(args.query)
        myArgs.query = args.query;
    res = executeCommand('cb-' + searchType, myArgs);
    var table = formatresults(res[0].Contents.results, columns);
    output.push({ContentsFormat: formats.table, Type: entryTypes.note, Contents: table});
}
return output;
