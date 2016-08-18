from __future__ import absolute_import, division

import os, sys, time
import threading
import Queue

from flask import request, make_response, send_file, url_for, jsonify
from tinydb import TinyDB, Query 
from random import randint

from octoprint_gcoderender.rendering.renderer import *

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
from octoprint.server.util import noCachingResponseHandler
from octoprint.events import Events

class GCodeRenderPlugin(octoprint.plugin.StartupPlugin, 
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.EventHandlerPlugin,
                        octoprint.plugin.BlueprintPlugin
):
    def initialize(self):
        os.stat_float_times(False)

        self.renderJobs = Queue.Queue()
        self.queueLock = threading.Lock()
        self.dbLock = threading.Lock()

        self.preview_extension = "png"

        if sys.platform == "win32":
            self.preview_extension = "bmp"

        self.renderJobsWatch = []

        self._prepareDatabase()

        self.cleanup()

        self._start_render_thread()

    def _prepareDatabase(self):
        self.dbLock.acquire()
        self.previews_database_path = os.path.join(self.get_plugin_data_folder(), "previews.json")
        self.previews_database = TinyDB(self.previews_database_path)
        self._previews_query = Query() # underscore for blueprintapi compatability
        self.dbLock.release()
    
    def _updateAllPreviews(self):
        uploads_folder = self._settings.global_get_basefolder('uploads')

        # TODO: Recursive
        for entry in os.listdir(uploads_folder):
            entry_path = os.path.join(uploads_folder, entry)

            if os.path.isfile(entry_path):
                file_type = octoprint.filemanager.get_file_type(entry)
                if(file_type):
                    if file_type[0] is "machinecode":
                        self._updatePreview(entry_path, entry)
   
    def _updatePreview(self, path, filename):
        self.dbLock.acquire()
        db_entry = self.previews_database.get(self._previews_query.path == path)
        self.dbLock.release()
        modtime = os.path.getmtime(path)
        if db_entry is None or db_entry["modtime"] != modtime or not os.path.exists(db_entry["previewPath"]):
            self.render_gcode(path, filename, modtime)

    def cleanup(self):
        #Loop through database, remove items not found in upload or preview folder
        self.dbLock.acquire()
        db_entries = self.previews_database.all()
        for db_entry in db_entries:
            if not os.path.exists(db_entry["previewPath"]) or not os.path.exists(db_entry["path"]):
                self.previews_database.remove(eids=[db_entry.eid])
                self._logger.debug("Removed from preview database: %s" % db_entry["filename"])
        

        #Loop through images, remove items not found in db
        image_folder = self._get_image_folder()
        for entry in os.listdir(image_folder):
            entry_path = os.path.join(image_folder, entry)

            if entry_path.endswith(self.preview_extension) and \
                not self.previews_database.contains(self._previews_query.previewPath == entry_path):
                try:
                    os.remove(entry_path)
                    self._logger.debug("Removed preview %s" % entry_path)
                except Exception:
                    self._logger.debug("Could not remove preview %s" % entry_path)
        self.dbLock.release()

    def on_event(self, event, payload, *args, **kwargs):
        if event == Events.UPDATED_FILES:
            self._updateAllPreviews()

    def is_blueprint_protected(self):
        return False

    def get_settings_defaults(self):
        return dict(
            maxPreviewFilesize=0
        )

    def render_gcode(self, path, filename, modtime = None):
        if not os.path.exists(path):
            return

        if not modtime:
             modtime = os.path.getmtime(path)
        
        #TODO: Some error handling; or return a dummy preview
        maxFileSize = self._settings.get_int(["maxPreviewFileSize"])
        if maxFileSize > 0 and os.path.getsize(path) > maxFileSize:
            self._logger.warn("GCode file exceeds max preview file size: %s" % filename)
            return

        self.queueLock.acquire()
        if not filename in self.renderJobsWatch:
            self.renderJobsWatch.append(filename) # No need to remove them for now. Should be no occassion in which render file is removed.
            self.renderJobs.put({ "path": path, "filename": filename, "modtime": modtime})
            self._logger.debug("Render job enqueued: %s" % filename)
        else:
            self._logger.debug("Already enqueued: %s" % filename)
        self.queueLock.release()
        

    @octoprint.plugin.BlueprintPlugin.route("/previewstatus", methods=["GET"])
    def previewstatus(self):
        filename = request.args.get('filename') 
        make = request.args.get('make') == 'true'

        if not filename:
            response = make_response('Invalid filename', 400)
        else:
            self._logger.debug("Retrieving preview status for %s" % filename)
            self.dbLock.acquire()
            db_entry = self.previews_database.get(self._previews_query.filename == filename)
            self.dbLock.release()

            if not db_entry:
                if make:
                    gcodePath = os.path.join(self._settings.global_get_basefolder('uploads'), filename)
                    self.render_gcode(gcodePath, filename)
                    response = make_response(jsonify({ 'status': 'rendering'}), 200)
                else:
                    response = make_response(jsonify({ 'status': 'notfound'}), 200)
            elif os.path.exists(db_entry["previewPath"]):
                response = make_response(jsonify({ 'status': 'ready', 'previewUrl' : db_entry["previewUrl"] }), 200)
            else:
                self._logger.debug("Preview file not found: %s" % db_entry["previewPath"])
                response = make_response(jsonify({ 'status': 'notfound'}), 200)

        return self._make_no_cache(response)

    @octoprint.plugin.BlueprintPlugin.route("/preview/<previewFilename>", methods=["GET"])
    def preview(self, previewFilename):
        if not previewFilename:
            response = make_response('Invalid filename', 400)
        else:
            self._logger.debug("Retrieving preview %s" % previewFilename)

            self.dbLock.acquire()
            db_entry = self.previews_database.get(self._previews_query.previewFilename == previewFilename)
            self.dbLock.release()

            if not db_entry or not os.path.exists(db_entry["previewPath"]):
                response = make_response('No preview ready', 404)
            else:
                response = send_file(db_entry["previewPath"])

        return response

    @octoprint.plugin.BlueprintPlugin.route("/allpreviews", methods=["GET"])
    def getAllPreviews(self):
        self.dbLock.acquire()
        db_entries = self.previews_database.all()
        self.dbLock.release()

        previews = []
        for db_entry in db_entries:
            if os.path.exists(db_entry["previewPath"]):
                previews.append({ "filename": db_entry["filename"], "previewUrl" : db_entry["previewUrl"] })

        response = make_response(jsonify({ "previews" : previews }))

        return self._make_no_cache(response)
        

    def _start_render_thread(self):
        t = threading.Thread(target=self._render_gcode_watch)
        t.setDaemon(True)
        t.start()
        
    def _render_gcode_watch(self):
        if sys.platform == "win32" or sys.platform == "darwin":
            self.render = RendererOpenGL()
        else:
            self.render = RendererOpenGLES()

        self.render.initialize(bedWidth = 365, bedDepth = 350, partColor = (67/255, 74/255, 84/255), bedColor = (0.75, 0.75, 0.75), width = 250, height = 250)
        
        while True:
            self.queueLock.acquire()
            if not self.renderJobs.empty():
                job = self.renderJobs.get()
                self._logger.debug("Job found: %s" % job['filename'])
                self.queueLock.release()
                self._render_gcode_worker(job['path'], job['filename'], job['modtime'])
                self.queueLock.acquire()
                self.renderJobsWatch.remove(job['filename'])
                self.renderJobs.task_done()

            self.queueLock.release()
            time.sleep(0.5) #TODO: find another way to reduce CPU

    def _render_gcode_worker(self, path, filename, modtime):
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
             self._logger.debug('Not a valid file type: %s' % path)
             return

        if not os.path.exists(path):
            self._logger.debug('File doesn\'t exist: %s' % path)
            return 

        if filename.startswith("."): #TODO: Perform a more comprehensive hidden file check
            self._logger.debug('Hidden file: %s' % path)
            return

        self._send_client_message("gcode_preview_rendering", { 
                                            "filename":  filename
                                            })
        imageDest = self._get_imagepath(filename, modtime)
       
        self._logger.debug("Image path: {}".format(imageDest["path"]))
        
        self.render.renderModel(path, True)
        self.render.save(imageDest["path"])

        self._logger.debug("Render complete: %s" % filename)
        url = '/plugin/gcoderender/preview/%s' % imageDest["filename"]

        self.dbLock.acquire()
        db_entry = self.previews_database.get(self._previews_query.path == path)
      
        if not db_entry:
            self.previews_database.insert({ 
                    "filename" : filename, 
                    "path": path, 
                    "modtime" : modtime, 
                    "previewUrl" : url,
                    "previewFilename" : imageDest["filename"],
                    "previewPath" : imageDest["path"]
                })
        else:
            try:
                os.remove(db_entry["previewPath"])
            except Exception:
                self._logger.debug("Could not delete preview %s" % db_entry["previewPath"])

            self.previews_database.update({ 
                    "modtime" : modtime, 
                    "previewUrl" : url,
                    "previewPath" : imageDest["path"], 
                    "previewFilename" : imageDest["filename"]
                }
                , self._previews_query.path == path)
         
        self.dbLock.release()  
        self._send_client_message("gcode_preview_ready", { 
                                                            "filename":  filename,
                                                            "previewUrl": url
                                                            })

   

    def _make_no_cache(self, response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    def _get_image_folder(self):
        return self._settings.get_plugin_data_folder()

    def _get_imagepath(self, filename, modtime = None):
        name, _ = os.path.splitext(filename)

        images_folder = self._get_image_folder()
        
        if not modtime:
            modtime = time.clock()

        new_filename = "{0}_{1}.{2}".format(name, modtime, self.preview_extension)


        image_path = os.path.join(images_folder, new_filename)

        return dict(path = image_path, filename = new_filename)
    
    def _send_client_message(self, message_type, data=None):
        self._logger.debug("Sending client message with type: {type}, and data: {data}".format(type=message_type, data=data))
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=message_type, data=data))
