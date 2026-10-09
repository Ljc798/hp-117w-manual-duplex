"""Install the Finder service; inputs are passed as separate shell arguments."""
import plistlib
import shlex
import sys
import uuid
from pathlib import Path
app, python = sys.argv[1:]
name = 'HP 117w 打印 — 打开网页'
contents = Path.home() / 'Library/Services' / (name + '.workflow') / 'Contents'
contents.mkdir(parents=True, exist_ok=True)
script = shlex.quote(python) + ' ' + shlex.quote(app + '/Contents/Resources/mobile.py') + ' enqueue "$@"'
action = {
    'AMAccepts': {'Container': 'List', 'Optional': False, 'Types': ['com.apple.cocoa.string']},
    'AMProvides': {'Container': 'List', 'Types': ['com.apple.cocoa.string']},
    'AMActionVersion': '2.0.3', 'AMApplication': ['Automator'],
    'AMParameterProperties': {k: {} for k in ('COMMAND_STRING','CheckedForUserDefaultShell','inputMethod','shell','source')},
    'ActionBundlePath': '/System/Library/Automator/Run Shell Script.action',
    'ActionName': 'Run Shell Script', 'BundleIdentifier': 'com.apple.RunShellScript',
    'Class Name': 'RunShellScriptAction', 'CFBundleVersion': '2.0.3',
    'ActionParameters': {'COMMAND_STRING': script, 'CheckedForUserDefaultShell': True, 'inputMethod': 1, 'shell': '/bin/zsh', 'source': ''},
    'CanShowWhenRun': True, 'CanShowSelectedItemsWhenRun': False,
    'Category': ['AMCategoryUtilities'], 'UnlocalizedApplications': ['Automator'],
    'InputUUID': str(uuid.uuid4()), 'OutputUUID': str(uuid.uuid4()), 'UUID': str(uuid.uuid4()),
    'isViewVisible': 1, 'arguments': {},
}
metadata = {
    'applicationBundleID': 'com.apple.finder', 'applicationPath': '/System/Library/CoreServices/Finder.app',
    'serviceApplicationBundleID': 'com.apple.finder', 'serviceApplicationPath': '/System/Library/CoreServices/Finder.app',
    'inputTypeIdentifier': 'com.apple.Automator.fileSystemObject',
    'serviceInputTypeIdentifier': 'com.apple.Automator.fileSystemObject',
    'outputTypeIdentifier': 'com.apple.Automator.nothing', 'serviceOutputTypeIdentifier': 'com.apple.Automator.nothing',
    'processesInput': False, 'serviceProcessesInput': False, 'presentationMode': 15,
    'useAutomaticInputType': False, 'workflowTypeIdentifier': 'com.apple.Automator.servicesMenu',
}
(contents / 'document.wflow').write_bytes(plistlib.dumps({'AMApplicationBuild':'527','AMApplicationVersion':'2.10','AMDocumentVersion':'2','actions':[{'action':action,'isViewVisible':1}],'connectors':{},'workflowMetaData':metadata}))
(contents / 'Info.plist').write_bytes(plistlib.dumps({'NSServices':[{'NSMenuItem':{'default':name},'NSMessage':'runWorkflowAsService','NSRequiredContext':{'NSApplicationIdentifier':'com.apple.finder'},'NSSendFileTypes':['com.adobe.pdf','org.openxmlformats.wordprocessingml.document'],'NSIconName':'NSActionTemplate'}]}))
print('Installed Finder action: ' + str(contents.parent))
