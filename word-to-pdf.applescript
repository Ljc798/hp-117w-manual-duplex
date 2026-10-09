on run argv
    set inputPath to item 1 of argv
    set outputPath to item 2 of argv
    with timeout of 180 seconds
        tell application "Microsoft Word"
            open (POSIX file inputPath) confirm conversions false read only true add to recent files false
            set convertedDocument to active document
            try
                save as convertedDocument file name outputPath file format format PDF add to recent files false
            on error errorText number errorNumber
                close convertedDocument saving no
                error errorText number errorNumber
            end try
            close convertedDocument saving no
        end tell
    end timeout
end run
