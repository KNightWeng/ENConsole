#!/usr/bin/env python
#
# To run, first set this environment variable to point to the Evernote API python bindings you downloaded from Evernote:
#   export PYTHONPATH=/path/to/evernote/python/api
#
import os, sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(PROJECT_ROOT, 'lib') )

import config
import hashlib
import time
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors
import getpass
import mimetypes
 
#
# NOTE: You must change the consumer key and consumer secret to the 
#       key and secret that you received from Evernote
#
consumerKey = "fill me in with your API key"
consumerSecret = "fill me in with your API secret"
 
evernoteHost = "www.evernote.com"
userStoreUri = "https://" + evernoteHost + "/edam/user"
noteStoreUriBase = "https://" + evernoteHost + "/edam/note/"
 
#if len(sys.argv) < 3:
#    print "Arguments:  <username> <password>";
#    exit(1)
 
username = raw_input("Evernote username: ")
password = getpass.getpass("Evernote password: ")
 
userStoreHttpClient = THttpClient.THttpClient(userStoreUri)
userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
userStore = UserStore.Client(userStoreProtocol)
 
versionOK = userStore.checkVersion("Python EDAMTest",
                                   UserStoreConstants.EDAM_VERSION_MAJOR,
                                   UserStoreConstants.EDAM_VERSION_MINOR)
 
if not versionOK:
  print "EDAM protocol is not up to date."
  exit(1)
 
# Authenticate the user
try :
    authResult = userStore.authenticate(username, password,
                                        consumerKey, consumerSecret)
except Errors.EDAMUserException as e:
    # See http://www.evernote.com/about/developer/api/ref/UserStore.html#Fn_UserStore_authenticate
    parameter = e.parameter
    errorCode = e.errorCode
    errorText = Errors.EDAMErrorCode._VALUES_TO_NAMES[errorCode]
    
    print "Authentication failed (parameter: " + parameter + " errorCode: " + errorText + ")"
    
    if errorCode == Errors.EDAMErrorCode.INVALID_AUTH:
        if parameter == "consumerKey":
            if consumerKey == "en-edamtest":
                print "You must replace the variables consumerKey and consumerSecret with the values you received from Evernote."
            else:
                print "Your consumer key was not accepted by", evernoteHost
            print "If you do not have an API Key from Evernote, you can request one from http://www.evernote.com/about/developer/api"
        elif parameter == "username":
            print "You must authenticate using a username and password from", evernoteHost
            if evernoteHost != "www.evernote.com":
                print "Note that your production Evernote account will not work on", evernoteHost
                print "You must register for a separate test account at https://" + evernoteHost + "/Registration.action"
        elif parameter == "password":
            print "The password that you entered is incorrect"
 
    print ""
    exit(1)
 
user = authResult.user
authToken = authResult.authenticationToken
print "Authentication was successful for", user.username
#print "Authentication token = ", authToken
 
noteStoreUri =  noteStoreUriBase + user.shardId
noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
noteStore = NoteStore.Client(noteStoreProtocol)
 
notebooks = noteStore.listNotebooks(authToken)
#print "Found ", len(notebooks), " notebooks:"
for notebook in notebooks:
#    print "  * ", notebook.name
  if notebook.defaultNotebook:
    defaultNotebook = notebook
#
#print
#print "Creating a new note in default notebook: ", defaultNotebook.name
#print
 
tags = raw_input("Tags (separated by commas): ").split(',')
 
for arg in sys.argv[1:]:
  print "Uploading", arg, "...",
  sys.stdout.flush()
  filedata = open( arg, 'rb').read()
  md5 = hashlib.md5()
  md5.update(filedata)
  hashHex = md5.hexdigest()
 
  data = Types.Data()
  data.size = len(filedata)
  data.bodyHash = hashHex
  data.body = filedata
 
  resource = Types.Resource()
  resource.mime = mimetypes.guess_type( arg)[0]
  resource.data = data
 
  note = Types.Note()
  note.notebookGuid = defaultNotebook.guid
  note.title = arg
  note.content = '<?xml version="1.0" encoding="UTF-8"?>'
  note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml.dtd">'
  note.content += '<en-note>'
  note.content += '<en-media type="' + resource.mime + '" hash="' + hashHex + '"/>'
  note.content += '</en-note>'
  note.created = int(time.time() * 1000)
  note.updated = note.created
  note.resources = [ resource ]
  note.tagNames = tags
 
  createdNote = noteStore.createNote(authToken, note)
 
  print "DONE"
