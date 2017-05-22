from __future__ import absolute_import, division

__author__ = "Erik Heidstra <ErikHeidstra@live.nl>"

import os, sys, time
import threading, subprocess
import Queue

from flask import request, make_response, send_file, url_for, jsonify
from tinydb import TinyDB, Query 
from random import randint

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
        # Because we use last modified, make sure we only get integers
        os.stat_float_times(False)

        # The actual render jobs
        self.renderJobs = Queue.Queue()

        # Prepare loks for render queue and database access
        self.dbLock = threading.Lock()

        self.preview_extension = "png"

        # Initialize tinydb
        self._prepareDatabase()

        # Cleanup the database and previews folder
        self.cleanup()

        # Begin watching for render jobs
        self._start_render_thread()

        # Fill the queue with any jobs we may have missed
        self._updateAllPreviews()

    def _prepareDatabase(self):
        self.dbLock.acquire()
        self.previews_database_path = os.path.join(self.get_plugin_data_folder(), "previews.json")
        self.previews_database = TinyDB(self.previews_database_path)
        self._previews_query = Query() # underscore for blueprintapi compatability
        self.dbLock.release()
    
    def _updateAllPreviews(self, subFolder = None):
        """
        Reads the entire preview database, checks if there are any outdated previews (last modified of preview
        is before last modified of gcode file) and updates these.
        """ 
        current_folder = self._settings.global_get_basefolder('uploads')

        if subFolder:
            current_folder = os.path.join(current_folder, subFolder)

        self._logger.debug('Scanning folder {0} for render jobs'.format(current_folder))

        for entry in os.listdir(current_folder):
            entry_path = os.path.join(current_folder, entry)
            entry_rel_path = entry

            if subFolder:
                entry_rel_path = subFolder + '/' + entry

            if os.path.isfile(entry_path):
                file_type = octoprint.filemanager.get_file_type(entry_rel_path)
                if(file_type):
                    if file_type[0] is "machinecode":
                        self._updatePreview(entry_path, entry_rel_path)
            else:
                self._updateAllPreviews(entry_rel_path)
   
    def _updatePreview(self, path, filename):
        """
        Checks if the preview is up to date with the gcode file (based on last modified) and re-renders if neceserry.
        """
        self.dbLock.acquire()
        db_entry = self.previews_database.get(self._previews_query.path == path)
        self.dbLock.release()

        
        modtime = os.path.getmtime(path)
        if db_entry is None or db_entry["modtime"] != modtime or not os.path.exists(db_entry["previewPath"]):
            self.render_gcode(path, filename, modtime)

    def cleanup(self):
        """
        Loop through database, remove items not found in upload or preview folder
        """
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
        if event == Events.UPLOAD:
            if "path" in payload:
                gcodePath = os.path.join(self._settings.global_get_basefolder('uploads'), payload["path"])
                self.render_gcode(gcodePath, payload["name"])
            else:
                self._logger.debug("File uploaded, but no metadata found to create the gcode preview")

    def is_blueprint_protected(self):
        return False

    def get_settings_defaults(self):
        return dict(
            maxPreviewFilesize=0
        )

    def render_gcode(self, path, filename, modtime = None):
        """
        Adds a render job to the render queue
        """
        if not os.path.exists(path):
            self._logger.debug("Could not find file to render: {0}".format(path))
            return

        if not modtime:
             modtime = os.path.getmtime(path)
        
        #TODO: Some error handling; or return a dummy preview
        maxFileSize = self._settings.get_int(["maxPreviewFileSize"])
        if maxFileSize > 0 and os.path.getsize(path) > maxFileSize:
            self._logger.warn("GCode file exceeds max preview file size: %s" % filename)
            return

        # Add the job to the render queue
        self.renderJobs.put({ "path": path, "filename": filename, "modtime": modtime})
        self._logger.debug("Render job enqueued: %s" % filename)
        

    @octoprint.plugin.BlueprintPlugin.route("/previewstatus/<path:filename>", methods=["GET"])
    def previewstatus(self, filename):
        """
        Allows to check whether a preview is available for a gcode file. 
        Query string arguments:
        filename: The gcode file to get the preview status for
        make: Whether or not to start rendering the preview, if there's no preview ready

        GET /previewstatus/<filename>
        """

        #TODO: Add support for other statusses, such as 'rendering failed', 'gcode too big', 'queued for rendering' etc
        
        if not filename:
            response = make_response('Invalid filename', 400)
        else:
            # First check in the database whether a preview is available
            self._logger.debug("Retrieving preview status for %s" % filename)
            self.dbLock.acquire()
            db_entry = self.previews_database.get(self._previews_query.filename == filename)
            self.dbLock.release()

            if not db_entry:
                response = make_response(jsonify({ 'status': 'notfound'}), 200)
            elif os.path.exists(db_entry["previewPath"]):
                response = make_response(jsonify({ 'status': 'ready', 'previewUrl' : db_entry["previewUrl"] }), 200)
            else:
                self._logger.debug("Preview file not found: %s" % db_entry["previewPath"])
                response = make_response(jsonify({ 'status': 'notfound'}), 200)

        return self._make_no_cache(response)

    @octoprint.plugin.BlueprintPlugin.route("/preview/<path:previewFilename>", methods=["GET"])
    def preview(self, previewFilename):
        """
        Retrieves a preview for a gcode file. Returns 404 if preview was not found
        GET /preview/file.gcode
        """
        if not previewFilename:
            response = make_response('Invalid filename', 400)
        else:
            self._logger.debug("Retrieving preview %s" % previewFilename)

            # Check the database for existing previews
            self.dbLock.acquire()
            db_entry = self.previews_database.get(self._previews_query.previewFilename == previewFilename)
            self.dbLock.release()

            # Return the preview file if it is found, otherwise 404
            if not db_entry or not os.path.exists(db_entry["previewPath"]):
                response = make_response('No preview ready', 404)
            else:
                response = send_file(db_entry["previewPath"])

        return response

    @octoprint.plugin.BlueprintPlugin.route("/allpreviews", methods=["GET"])
    def getAllPreviews(self):
        """
        Gets a list of all gcode files for which a preview is available. Useful for initial display 
        of a gcode file list. Removes the need for calling previewstatus a lot of times.
        """
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
        """"
        Start the daemon thread that watches the render job queue
        """
        t = threading.Thread(target=self._render_gcode_watch)
        t.setDaemon(True)
        t.start()
        
    def _render_gcode_watch(self):
        """"
        The actual rendering thread. Monitors the render queue, and initiates the render job.
        """
        while True:
            job = self.renderJobs.get() # Will block until a job becomes available
            self._logger.debug("Job found: {0}".format(job['filename']))
            t0 = time.time()
            self._render_gcode_worker(job['path'], job['filename'], job['modtime'])
            t1 = time.time()
            self._logger.info("Rendered preview for {filename} in {t:0.0f} s".format(filename=job['filename'], t=(t1-t0)))
            self.renderJobs.task_done()

    def _render_gcode_worker(self, path, filename, modtime):
        """
        Renders a preview for a gcode file and inserts a record into the preview database.
        """
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
             self._logger.debug('Not a valid file type: %s' % path)
             return

        if not os.path.exists(path):
            self._logger.debug('File doesn\'t exist: %s' % path)
            return 

        if filename.startswith("."): #TODO: Perform a more comprehensive hidden file check
            self._logger.debug('Hidden file: %s' % path)
            return

        # Notify the client about the render
        self._send_client_message("gcode_preview_rendering", { 
                                            "filename":  filename
                                            })

        # Get a filename for the preview. By including modtime, the previews may be cached by the browser
        imageDest = self._get_imagepath(filename, modtime)
       
        self._logger.debug("Image path: {}".format(imageDest["path"]))
       
        # This is where the magic happens
        self._logger.debug("Begin rendering");
        returncode = subprocess.call(["gcodeparser", path, imageDest["path"]])

        if returncode == 0:
            # Rendering succeeded
            self._logger.debug("Render complete: %s" % filename)
            url = '/plugin/gcoderender/preview/%s' % imageDest["filename"]
        else:
            # Rendering failed.
            # TODO: set url and path to a failed-preview-image
            self._logger.debug("Render failed: %s" % filename)
            url = '/plugin/gcoderender/preview/%s' % imageDest["filename"]

        # Query the database for any existing records of the gcode file. 
        # Then, update or insert record
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

        # Notify client the preview is ready
        self._send_client_message("gcode_preview_ready", { 
                                                            "filename":  filename,
                                                            "previewUrl": url
                                                            })

   

    def _make_no_cache(self, response):
        """
        Helper method to set no-cache headers. Not used anymore, as including modtime in filename allows browser caching
        """
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    def _get_image_folder(self):
        """
        Gets the folder to save the previews to
        """
        return self._settings.get_plugin_data_folder()

    def _get_imagepath(self, filename, modtime = None):
        """
        Creates a filename for the preview. Returns both filename and (full) path
        """

        # Strip any subfolders and find the basename of the file
        _, tail = os.path.split(filename)
        name, _ = os.path.splitext(tail)

        images_folder = self._get_image_folder()
        
        if not modtime:
            modtime = time.clock()

        new_filename = "{0}_{1}.{2}".format(name, modtime, self.preview_extension)

        image_path = os.path.join(images_folder, new_filename)

        return dict(path = image_path, filename = new_filename)
    
    def _send_client_message(self, message_type, data=None):
        """
        Notify the client
        """
        self._logger.debug("Sending client message with type: {type}, and data: {data}".format(type=message_type, data=data))
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=message_type, data=data))
