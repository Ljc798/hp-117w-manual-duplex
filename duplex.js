ObjC.import('Foundation');
ObjC.import('Quartz');
function openDocument(input) {
    var src=$.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(input));
    if (!src || src.isNil() || src.isLocked || !src.allowsPrinting || src.pageCount < 1) throw Error('This PDF cannot be opened for printing.');
    return src;
}
function prepare(input, dir, firstPage, lastPage) {
    var src=openDocument(input), n=Number(src.pageCount);
    var first=Number(firstPage), last=Number(lastPage);
    if (Math.floor(first)!==first || Math.floor(last)!==last || first<1 || last<first || last>n) throw Error('The selected page range is outside this PDF.');
    var selectedCount=last-first+1, odd=$.PDFDocument.alloc.init, even=$.PDFDocument.alloc.init;
    // Materialize order and rotation in the PDFs; AirPrint need not interpret page-set options.
    // The first selected page starts a new duplex sequence, even if its original PDF number is even.
    for(var i=0;i<selectedCount;i+=2) odd.insertPageAtIndex(src.pageAtIndex(first-1+i).copy, odd.pageCount);
    for(var j=(selectedCount%2===0?selectedCount-1:selectedCount-2);j>=1;j-=2) {
        var page=src.pageAtIndex(first-1+j).copy;
        page.rotation=(Number(page.rotation)+180)%360;
        even.insertPageAtIndex(page, even.pageCount);
    }
    if(!odd.writeToFile(dir+'/odd.pdf')) throw Error('Could not prepare the front pages.');
    if(even.pageCount>0 && !even.writeToFile(dir+'/even.pdf')) throw Error('Could not prepare the back pages.');
    return {pages:selectedCount,sheets:Math.ceil(selectedCount/2),start:first,end:last,removeLast:selectedCount%2===1 && selectedCount>1,odd:dir+'/odd.pdf',even:dir+'/even.pdf'};
}
function parsePrintRange(options, spoolPageCount) {
    var marker='com.apple.print.pageRange=';
    var text=String(options), at=text.indexOf(marker);
    if(at<0) return null;
    var value=text.slice(at+marker.length);
    var next=value.search(/\s+com\.apple\.print\./i);
    if(next>=0) value=value.slice(0,next);
    var nums=(value.match(/\d+/g)||[]).map(Number);
    var first, last;
    if(/\ball\b/i.test(value)) {
        first=1;
        last=nums.length ? nums[nums.length-1] : spoolPageCount;
    } else if(nums.length>=2) {
        first=nums[0];
        last=nums[1];
    } else if(nums.length===1) {
        if(nums[0]===spoolPageCount) { first=1; last=spoolPageCount; }
        else { first=nums[0]; last=nums[0]; }
    } else {
        return null;
    }
    if(first<1 || last<first || last-first+1!==spoolPageCount) return null;
    return {first:first,last:last};
}
function run(args) {
    if(args[0]==='--qr') {
        ObjC.import('AppKit'); ObjC.import('CoreImage');
        var filter=$.CIFilter.filterWithName('CIQRCodeGenerator');
        filter.setValueForKey($(args[1]).dataUsingEncoding($.NSUTF8StringEncoding),'inputMessage');
        var ci=filter.outputImage;
        var rep=$.NSBitmapImageRep.alloc.initWithCIImage(ci);
        if(!rep.representationUsingTypeProperties($.NSPNGFileType,$.NSDictionary.dictionary).writeToFileAtomically(args[2],true)) throw Error('QR generation failed');
        return 'OK';
    }
    if(args[0]==='--thumbnail') {
        ObjC.import('AppKit');
        var d=openDocument(args[1]), index=Number(args[3])-1;
        if(index<0 || index>=Number(d.pageCount) || Math.floor(index)!==index) throw Error('Invalid page');
        var img=d.pageAtIndex(index).thumbnailOfSizeForBox($.NSMakeSize(650,900),$.kPDFDisplayBoxMediaBox);
        var rep=$.NSBitmapImageRep.imageRepWithData(img.TIFFRepresentation);
        if(!rep.representationUsingTypeProperties($.NSPNGFileType,$.NSDictionary.dictionary).writeToFileAtomically(args[2],true)) throw Error('Could not render preview');
        return 'OK';
    }
    if(args[0]==='--extract') {
        var src=openDocument(args[1]), first=Number(args[3]), last=Number(args[4]);
        if(Math.floor(first)!==first || Math.floor(last)!==last || first<1 || last<first || last>Number(src.pageCount)) throw Error('Invalid page range');
        var out=$.PDFDocument.alloc.init;
        for(var i=first-1;i<last;i++) out.insertPageAtIndex(src.pageAtIndex(i).copy,out.pageCount);
        if(!out.writeToFile(args[2])) throw Error('Could not extract PDF pages');
        return String(Number(out.pageCount));
    }
    if(args[0]==='--parse-range') {
        var parsed=parsePrintRange(args[1],Number(args[2]));
        return parsed ? String(parsed.first)+'|'+String(parsed.last) : 'unknown';
    }
    if(args[0]==='--count') return String(Number(openDocument(args[1]).pageCount));
    if(args[0]==='--prepare') return JSON.stringify(prepare(args[1],args[2],args[3],args[4]));
    throw Error('Unknown duplex helper command.');
}
