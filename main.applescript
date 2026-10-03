use scripting additions

property queueName : "REPLACE_WITH_YOUR_CUPS_QUEUE_NAME"
property titleText : "HP 117w Manual Duplex"
property printerLabel : "Your Printer Name"
property logFileName : "HP 117w Manual Duplex Print Log.xlsx"

on run argv
	set chosenPDF to «event sysostdf» given «class prmp»:"Choose a PDF for HP 117w manual duplex printing", «class ftyp»:{"com.adobe.pdf"}
	my processPDFs({chosenPDF}, "")
end run

on open theFiles
	my processPDFs(theFiles, "")
end open

on askUser(messageText, buttonText)
	activate
	«event sysodisA» titleText given «class mesS»:messageText, «class as A»:«constant EAlTinfA», «class btns»:{"Cancel", buttonText}, «class dflt»:buttonText, «class cbtn»:"Cancel"
end askUser

on askForNote(pdfName)
	activate
	try
		set dialogResult to «event sysodlog» ("Optional note for " & pdfName & ":") given «class dtxt»:"", «class appr»:titleText, «class btns»:{"Skip Note", "Save Record"}, «class dflt»:"Save Record"
		if «class bhit» of dialogResult is "Skip Note" then return ""
		return «class ttxt» of dialogResult
	on error errorText number errorNumber
		if errorNumber is -128 then return ""
		error errorText number errorNumber
	end try
end askForNote

on pendingJobs()
	return «event sysoexec» "/usr/bin/lpstat -W not-completed -o " & quoted form of queueName
end pendingJobs

on waitForFinalPass(waitMessage)
	set pendingText to my pendingJobs()
	repeat while pendingText is not ""
		try
			«event sysodisA» titleText given «class mesS»:waitMessage, «class as A»:«constant EAlTinfA», «class btns»:{"Check Again"}, «class dflt»:"Check Again"
		on error errorText number errorNumber
			if errorNumber is not -128 then error errorText number errorNumber
		end try
		set pendingText to my pendingJobs()
		set waitMessage to "Print Center still shows an unfinished job. Wait until all pages have printed, then click Check Again."
	end repeat
	return true
end waitForFinalPass

on printPDF(pdfPath, jobTitle)
	set replyText to «event sysoexec» "/usr/bin/lp -d " & quoted form of queueName & " -n 1 -t " & quoted form of jobTitle & " -o sides=one-sided -o media=A4 -o fit-to-page -o number-up=1 -o page-set=all -o outputorder=normal -o orientation-requested=3 -o mirror=false -o ColorModel=Gray -- " & quoted form of pdfPath
	if replyText does not contain "request id is " then error "The print system did not confirm submission. Check Print Center before trying again."
end printPDF

on printLogPath()
	return (POSIX path of («event earsffdr» «constant afdrdocs»)) & logFileName
end printLogPath

on appendPrintLog(pdfName, pageCount, sheetCount, statusText, noteText)
	set logPath to my printLogPath()
	set excelWasRunning to false
	try
		set excelWasRunning to application "Microsoft Excel.app" is running
	on error
		set excelWasRunning to true
	end try
	try
		tell application "Microsoft Excel.app"
			set originalVisibility to true
			set createdWorkbook to false
			try
				set originalVisibility to visible
			end try
			set logWorkbook to missing value
			repeat with candidateWorkbook in every «class X141»
				try
					if («class 1773» of candidateWorkbook) is logPath then
						set logWorkbook to candidateWorkbook
						exit repeat
					end if
				end try
			end repeat
			if logWorkbook is missing value then
				set visible to false
				set logWorkbook to «event smXL1169» given «class WbFN»:logPath
				set createdWorkbook to true
			end if
			set logSheet to «class XwSH» 1 of logWorkbook
			set logRegion to «class 1542» of «class X117» "A1" of logSheet
			set nextRow to (count of every «class crow» of logRegion) + 1
			set rowAddress to "A" & (nextRow as text) & ":G" & (nextRow as text)
			set «class DPVu» of «class X117» rowAddress of logSheet to {{«event misccurd», pdfName, pageCount, sheetCount, printerLabel, statusText, noteText}}
			save logWorkbook
			if createdWorkbook then close logWorkbook saving no
			if excelWasRunning then
				set visible to originalVisibility
			else
				quit
			end if
		end tell
	on error errorText number errorNumber
		try
			tell application "Microsoft Excel.app"
				if excelWasRunning then
					set visible to originalVisibility
				else
					quit
				end if
			end tell
		end try
		error "Could not save the print record to " & logPath & ". " & errorText number errorNumber
	end try
end appendPrintLog

on processPDFs(theFiles, optionsText)
	set tempDir to ""
	set firstAttempted to false
	set firstSubmitted to false
	set secondAttempted to false
	set secondSubmitted to false
	set finalPassFinished to false
	set didFail to false
	set failureText to ""
	set failureNumber to 0
	set pdfName to ""
	set pageCount to 0
	set sheetCount to 0
	set noteText to ""
	set printStatus to ""
	set logSaved to false
	set logErrorText to ""
	set logPath to my printLogPath()
	try
		if (count of theFiles) is not 1 then error "Choose one PDF at a time."
		set workerPath to POSIX path of («event sysorpth» "duplex.js")
		set pdfPath to POSIX path of (item 1 of theFiles)
		set pdfName to name of («event sysonfo4» (item 1 of theFiles))
		set tempDir to «event sysoexec» "/usr/bin/mktemp -d -t hp117w-duplex"
		set pageCount to («event sysoexec» "/usr/bin/osascript -l JavaScript " & quoted form of workerPath & " --count " & quoted form of pdfPath) as integer
		set sheetCount to (pageCount + 1) div 2
		set oddCount to (pageCount mod 2 is 1) and pageCount > 1
		set prepareResult to «event sysoexec» "/usr/bin/osascript -l JavaScript " & quoted form of workerPath & " --prepare " & quoted form of pdfPath & " " & quoted form of tempDir & " 1 " & (pageCount as text)
		set firstPassDescription to "First: every other page of the supplied PDF, in ascending order."
		set intro to "File: " & pdfName & return & "Printer: " & printerLabel & return & "Pages in the supplied PDF: 1–" & pageCount & "." & return & "A4, black and white, one copy, one page per side." & return & return & pageCount & " pages / " & sheetCount & " sheets." & return & firstPassDescription & return & "Pause: reload and click Continue on this Mac." & return & "Last: remaining pages in reverse order, rotated 180 degrees."
		if oddCount then set intro to intro & return & return & "Odd number of pages: set aside the last sheet before reloading. Its back stays blank."
		if pageCount is 1 then set intro to "File: " & pdfName & return & "Printer: " & printerLabel & return & "Pages in the supplied PDF: 1." & return & "A4, black and white, one copy." & return & return & "Only one side will print."
		set intro to intro & return & return & "Nothing prints until you click Print First Side."
		my askUser(intro, "Print First Side")
		if my pendingJobs() is not "" then error "The printer has unfinished jobs. Wait for them to finish and start this helper again. This helper has not printed anything."
		set firstAttempted to true
		my printPDF(tempDir & "/odd.pdf", "HP117w manual duplex - odd pages")
		set firstSubmitted to true
		if pageCount > 1 then
			set reloadText to "Wait until all " & sheetCount & " odd-page sheets have completely printed." & return & return
			if oddCount then set reloadText to reloadText & "Set aside the last sheet; keep its back blank." & return & return
			set reloadText to reloadText & "Reload the printed stack as in your working preset test: do not flip, rotate, or rearrange it. Place no unused sheets ahead of it." & return & return & "Click Continue only after every first-side page printed successfully and the stack is reloaded. The remaining pages will print in reverse order, rotated 180 degrees." & return & return & "If the first pass failed or was cancelled, click Cancel here."
			repeat
				my askUser(reloadText, "Continue")
				if my pendingJobs() is "" then exit repeat
				my askUser("Print Center still shows unfinished jobs. Wait until the printer finishes.", "Check Again")
			end repeat
			set secondAttempted to true
			my printPDF(tempDir & "/even.pdf", "HP117w manual duplex - even pages")
			set secondSubmitted to true
		end if
		if pageCount is 1 then
			set finalPassMessage to "Wait until the single page has completely printed. The print log note will appear afterward."
		else
			set finalPassMessage to "Wait until all " & sheetCount & " final-side sheets have completely printed. The print log note will appear afterward."
		end if
		set finalPassFinished to my waitForFinalPass(finalPassMessage)
	on error errorText number errorNumber
		set didFail to true
		set failureText to errorText
		set failureNumber to errorNumber
	end try

	if tempDir is not "" then «event sysoexec» "/bin/rm -rf " & quoted form of tempDir

	if didFail then
		if firstAttempted then
			set noteText to my askForNote(pdfName)
			if secondSubmitted and finalPassFinished then
				set printStatus to "Printed"
			else if secondSubmitted then
				set printStatus to "Both sides submitted; completion unconfirmed"
			else if secondAttempted then
				set printStatus to "Partial: second side not confirmed"
			else if firstSubmitted and pageCount is 1 and finalPassFinished then
				set printStatus to "Printed"
			else if firstSubmitted and pageCount is 1 then
				set printStatus to "Single side submitted; completion unconfirmed"
			else if firstSubmitted then
				set printStatus to "Partial: first side only"
			else
				set printStatus to "First-side submission not confirmed"
			end if
			try
				my appendPrintLog(pdfName, pageCount, sheetCount, printStatus, noteText)
				set logSaved to true
			on error logError
				set logErrorText to logError
			end try
		end if

		if failureNumber is -128 then
			if logSaved then
				set failureText to "The print was cancelled before the job finished. I logged it as: " & printStatus & return & return & logPath
				set didFail to true
			else if logErrorText is not "" then
				set failureText to "The print was cancelled before the job finished. I could not save its print record." & return & logErrorText
			else
				set didFail to false
			end if
		else if logSaved then
			if firstSubmitted then set failureText to failureText & return & return & "One or both sides may already have printed. Check Print Center and your paper before restarting."
			set failureText to failureText & return & return & "Recorded as: " & printStatus & return & logPath
		else if logErrorText is not "" then
			set failureText to failureText & return & return & "The print record could not be saved." & return & logErrorText
		end if

		if didFail then my askUser(failureText, "OK")
		return
	end if

	if firstSubmitted then
		set printStatus to "Printed"
		set noteText to my askForNote(pdfName)
		try
			my appendPrintLog(pdfName, pageCount, sheetCount, printStatus, noteText)
			set logSaved to true
		on error logError
			set logErrorText to logError
		end try
		if logSaved then
			set completionText to "Print completed and recorded." & return & pdfName & return & return & "Would you like to open the Excel log?" & return & logPath
			activate
			set completionChoice to «event sysodlog» completionText given «class appr»:titleText, «class btns»:{"Not Now", "Open Excel"}, «class dflt»:"Not Now"
			if «class bhit» of completionChoice is "Open Excel" then
				try
					«event sysoexec» "/usr/bin/open " & quoted form of logPath
				on error openError
					my askUser("The print was logged, but the log could not be opened." & return & logPath & return & return & openError, "OK")
				end try
			end if
		else
			my askUser("The print job was submitted, but the record could not be saved." & return & logPath & return & return & logErrorText, "OK")
		end if
	end if
end processPDFs
