use scripting additions

property queueName : "REPLACE_WITH_YOUR_CUPS_QUEUE_NAME"
property titleText : "HP 117w Manual Duplex"
property printerLabel : "Your Printer Name"
property mobilePython : "/opt/homebrew/bin/python3"
property currentMode : "duplex"
property logFileName : "HP 117w Manual Duplex Print Log.xlsx"

on run argv
	set chosenPDF to «event sysostdf» given «class prmp»:"Choose a PDF for HP 117w manual duplex printing", «class ftyp»:{"com.adobe.pdf"}
	my processPDFs({chosenPDF}, "")
end run

on open theFiles
	my processPDFs(theFiles, "")
end open

on mobileAsk(messageText, noteMode, buttonNames)
	set helperPath to POSIX path of (path to resource "mobile.py")
	set commandText to quoted form of mobilePython & " " & quoted form of helperPath & " ask " & quoted form of messageText & " " & quoted form of noteMode
	repeat with buttonName in buttonNames
		set commandText to commandText & " " & quoted form of (buttonName as text)
	end repeat
	return do shell script commandText
end mobileAsk

on askUser(messageText, buttonText)
	set replyText to my mobileAsk(messageText, "plain", {"Cancel", buttonText})
	if paragraph 1 of replyText is "Cancel" then error number -128
end askUser

on askForNote(pdfName)
	set replyText to my mobileAsk("Add an optional note for this print:" & return & pdfName, "note", {"Skip Note", "Save Record"})
	if paragraph 1 of replyText is "Skip Note" then return ""
	if (count of paragraphs of replyText) < 2 then return ""
	set firstBreak to offset of return in replyText
	return text (firstBreak + 1) thru -1 of replyText
end askForNote

on pendingJobs()
	return «event sysoexec» "/usr/bin/lpstat -W not-completed -o " & quoted form of queueName
end pendingJobs

on waitForQueue(stageName)
	set helperPath to POSIX path of (path to resource "mobile.py")
	set replyText to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " wait " & quoted form of queueName & " " & quoted form of stageName
	if replyText is "Cancel" then error number -128
end waitForQueue

on waitForFinalPass(waitMessage)
	my waitForQueue("back_wait")
	set resultText to my mobileAsk(waitMessage, "plain", {"Confirm Printed", "Report Problem", "Cancel"})
	if paragraph 1 of resultText is "Cancel" then error number -128
	if paragraph 1 of resultText is "Report Problem" then error "Some pages did not print successfully. Use Print history on your phone to reprint the missing pages on fresh paper."
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
	set helperPath to POSIX path of (path to resource "mobile.py")
	do shell script quoted form of mobilePython & " " & quoted form of helperPath & " record " & quoted form of pdfName & " " & pageCount & " " & sheetCount & " " & quoted form of statusText & " " & quoted form of noteText
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

on showControlPage(mobileURL)
	if application "Google Chrome" is running then
		tell application "Google Chrome"
			repeat with browserWindow in windows
				set tabNumber to 0
				repeat with browserTab in tabs of browserWindow
					set tabNumber to tabNumber + 1
					if URL of browserTab starts with mobileURL then
						set active tab index of browserWindow to tabNumber
						set minimized of browserWindow to false
						set index of browserWindow to 1
						activate
						return
					end if
				end repeat
			end repeat
		end tell
	end if
	if application "Safari" is running then
		tell application "Safari"
			repeat with browserWindow in windows
				repeat with browserTab in tabs of browserWindow
					if URL of browserTab starts with mobileURL then
						set current tab of browserWindow to browserTab
						set miniaturized of browserWindow to false
						set index of browserWindow to 1
						activate
						return
					end if
				end repeat
			end repeat
		end tell
	end if
	open location mobileURL
end showControlPage

on processPDFs(theFiles, optionsText)
	if (count of theFiles) is not 1 then error "Choose one PDF at a time."
	set helperPath to POSIX path of (path to resource "mobile.py")
	set keepAwakePID to ""
	set sourcePath to POSIX path of (item 1 of theFiles)
	set ownerPID to do shell script "echo $PPID"
	set currentMode to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " begin " & quoted form of sourcePath & " " & quoted form of queueName & " " & quoted form of printerLabel & " " & ownerPID
	try
		set mobileURL to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " start"
		my showControlPage(mobileURL)
		set keepAwakePID to do shell script "/usr/bin/caffeinate -i >/dev/null 2>&1 & echo $!"
		my processMobilePDFs(theFiles, optionsText)
	on error errorText number errorNumber
		if keepAwakePID is not "" then do shell script "/bin/kill " & keepAwakePID & " >/dev/null 2>&1 || true"
		do shell script quoted form of mobilePython & " " & quoted form of helperPath & " finish"
		error errorText number errorNumber
	end try
	if keepAwakePID is not "" then do shell script "/bin/kill " & keepAwakePID & " >/dev/null 2>&1 || true"
	do shell script quoted form of mobilePython & " " & quoted form of helperPath & " finish"
end processPDFs

on processMobilePDFs(theFiles, optionsText)
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
		set helperPath to POSIX path of (path to resource "mobile.py")
		set pdfPath to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " source"
		set helperPath to POSIX path of (path to resource "mobile.py")
		set pdfName to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " name"
		if pdfName ends with ".pdf.pdf" then set pdfName to text 1 thru ((count of pdfName) - 4) of pdfName
		set tempDir to «event sysoexec» "/usr/bin/mktemp -d -t hp117w-duplex"
		set pageCount to («event sysoexec» "/usr/bin/osascript -l JavaScript " & quoted form of workerPath & " --count " & quoted form of pdfPath) as integer
		set sheetCount to (pageCount + 1) div 2
		if currentMode is "single" then set sheetCount to pageCount
		set oddCount to (pageCount mod 2 is 1) and pageCount > 1 and currentMode is not "single"

		set firstPassDescription to "First: every other page of the supplied PDF, in ascending order."
		set intro to "File: " & pdfName & return & "Printer: " & printerLabel & return & "Pages in the supplied PDF: 1–" & pageCount & "." & return & "A4, black and white, one copy, one page per side." & return & return & pageCount & " pages / " & sheetCount & " sheets." & return & firstPassDescription & return & "Pause: reload and tap Continue on your iPhone." & return & "Last: remaining pages in reverse order, rotated 180 degrees."
		if oddCount then set intro to intro & return & return & "Odd number of pages: set aside the last sheet before reloading. Its back stays blank."
		if pageCount is 1 then set intro to "File: " & pdfName & return & "Printer: " & printerLabel & return & "Pages in the supplied PDF: 1." & return & "A4, black and white, one copy." & return & return & "Only one side will print."
		set intro to intro & return & return & "Nothing prints until you click Print First Side."
		my askUser(intro, "Print First Side")
		set currentMode to do shell script quoted form of mobilePython & " " & quoted form of helperPath & " mode"
		set pageCount to (do shell script "/usr/bin/osascript -l JavaScript " & quoted form of workerPath & " --count " & quoted form of pdfPath) as integer
		set sheetCount to (pageCount + 1) div 2
		if currentMode is "single" then set sheetCount to pageCount
		set oddCount to (pageCount mod 2 is 1) and pageCount > 1 and currentMode is not "single"
		set prepareResult to «event sysoexec» "/usr/bin/osascript -l JavaScript " & quoted form of workerPath & " --prepare " & quoted form of pdfPath & " " & quoted form of tempDir & " 1 " & (pageCount as text)
		if my pendingJobs() is not "" then error "The printer has unfinished jobs. Wait for them to finish and start this helper again. This helper has not printed anything."
		set firstAttempted to true
		if currentMode is "single" then
			my printPDF(pdfPath, "HP117w reprint - single-sided pages")
		else
			my printPDF(tempDir & "/odd.pdf", "HP117w manual duplex - odd pages")
		end if
		set firstSubmitted to true
		if pageCount > 1 and currentMode is not "single" then
			my waitForQueue("front_wait")
			set reloadText to "Wait until all " & sheetCount & " front-side sheets have completely printed." & return & return
			if oddCount then set reloadText to reloadText & "Odd number of pages: set aside the last sheet and leave its back blank." & return & return
			set reloadText to reloadText & "Reload the printed stack using your previously tested method: do not flip, rotate, or rearrange it. Place no unused sheets ahead of it." & return & return & "Continue only after every front side has printed successfully and the stack is reloaded. Back sides will print in reverse order, rotated 180 degrees." & return & return & "If the first pass failed or was cancelled, tap Cancel remaining steps."
			repeat
				my askUser(reloadText, "Continue")
				if my pendingJobs() is "" then exit repeat
				my waitForQueue("front_wait")
			end repeat
			set secondAttempted to true
			my printPDF(tempDir & "/even.pdf", "HP117w manual duplex - even pages")
			set secondSubmitted to true
		end if
		if pageCount is 1 or currentMode is "single" then
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
			else if firstSubmitted and (pageCount is 1 or currentMode is "single") and finalPassFinished then
				set printStatus to "Printed"
			else if firstSubmitted and (pageCount is 1 or currentMode is "single") then
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
			set completionChoice to my mobileAsk(completionText, "plain", {"Not Now", "Open Excel"})
			if paragraph 1 of completionChoice is "Open Excel" then
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
end processMobilePDFs
