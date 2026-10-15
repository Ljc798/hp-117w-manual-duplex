function run(argv) {
    var url=argv[0], tokenPath=argv[1], descriptors=JSON.parse(argv[2]);
    var browsers=[], matches=[];
    descriptors.forEach(function(d) {
        var app=Application(d.pid);
        var windows=app.windows();
        browsers.push({app:app,kind:d.kind,windows:windows});
        windows.forEach(function(w) {
            w.tabs().forEach(function(tab,index) {
                var address=d.kind==='chrome'?tab.url():tab.url();
                if(address && address.indexOf(':8717'+tokenPath)>=0)
                    matches.push({app:app,kind:d.kind,window:w,tab:tab,index:index+1});
            });
        });
    });
    if(matches.length) {
        var keep=matches[0];
        // Close only duplicate tabs for this same local print controller.
        for(var i=matches.length-1;i>0;i--) matches[i].tab.close();
        if(keep.kind==='chrome') {keep.window.activeTabIndex=keep.index;keep.window.minimized=false;}
        else {keep.window.currentTab=keep.tab;keep.window.miniaturized=false;}
        keep.window.index=1;
        keep.app.activate();
        return 'reused';
    }
    if(browsers.length) {
        var browser=browsers[0], app=browser.app;
        if(browser.kind==='chrome') {
            var window=browser.windows.length?browser.windows[0]:app.Window().make();
            if(browser.windows.length) {var tab=app.Tab({url:url});window.tabs.push(tab);window.activeTabIndex=window.tabs().length;}
            else window.activeTab.url=url;
            window.minimized=false;window.index=1;
        } else {
            var document=app.Document({url:url});app.documents.push(document);
        }
        app.activate();return 'created';
    }
    return 'no-browser';
}
