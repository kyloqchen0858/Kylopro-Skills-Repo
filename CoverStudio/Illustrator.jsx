#target illustrator
(function () {
    var directory = File($.fileName).parent;
    var destination = new Folder(directory.fsName + '/AI-' + new Date().getTime());
    if (!destination.create()) throw Error('Could not create output directory');
    var oldLevel = app.userInteractionLevel;
    var result = new File(destination.fsName + '/verification.txt');
    var table = new File(directory.fsName + '/layers.xml');
    var namesById = {};
    var plate = 'UV';
    var format = 'SVG';
    if (table.exists && table.open('r')) {
        var mapping = new XML(table.read());
        table.close();
        plate = String(mapping.@plate);
        format = String(mapping.@format);
        for each (var entry in mapping.object) namesById[String(entry.@id)] = String(entry.@name);
    }
    result.open('w');
    try {
        app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
        var names = ['ART', 'UV'];
        if (new File(directory.fsName + '/FOIL.svg').exists) names.push('FOIL');
        if (new File(directory.fsName + '/DEBOSS.svg').exists) names.push('DEBOSS');
        for (var i = 0; i < names.length; i++) {
            var document = app.open(new File(directory.fsName + '/' + names[i] + '.svg'));
            document.layers[0].name = names[i] === 'UV' ? plate : names[i];
            for (var j = 0; j < document.pageItems.length; j++) {
                var item = document.pageItems[j];
                if (namesById[item.name]) item.name = namesById[item.name];
            }
            var target = new File(destination.fsName + '/' + names[i] + '.ai');
            var options = new IllustratorSaveOptions();
            options.pdfCompatible = true;
            options.embedLinkedFiles = true;
            document.saveAs(target, options);
            document.close(SaveOptions.DONOTSAVECHANGES);
            var reopened = app.open(target);
            if (format === 'PDF') {
                reopened.saveAs(new File(destination.fsName + '/' + names[i] + '.pdf'), new PDFSaveOptions());
            }
            result.writeln(names[i] + ' reopened; paths=' + reopened.pathItems.length + ', text=' + reopened.textFrames.length);
            if (names[i] === 'UV' && reopened.pathItems.length) {
                var path = reopened.pathItems[0];
                path.selected = true;
                var start = path.left;
                path.translate(2, 0);
                var edited = new File(destination.fsName + '/UV-edit-test.ai');
                reopened.saveAs(edited, options);
                reopened.close(SaveOptions.DONOTSAVECHANGES);
                reopened = app.open(edited);
                if (Math.abs(reopened.pathItems[0].left - start - 2) > 0.05) throw Error('Edit verification failed');
                result.writeln('Moved UV path by 2pt; verified after reopen in separate test file.');
            }
            reopened.close(SaveOptions.DONOTSAVECHANGES);
        }
    } finally {
        result.close();
        app.userInteractionLevel = oldLevel;
    }
})();

