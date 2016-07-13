from __future__ import absolute_import, division

import os, sys, time
import threading
import Queue

from flask import make_response, send_file, url_for, jsonify
from random import randint

from octoprint_gcoderender.rendering.renderer import *

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
from octoprint.server.util import noCachingResponseHandler

class GCodeRenderPlugin(octoprint.plugin.StartupPlugin, 
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.BlueprintPlugin
):
    def initialize(self):
        octoprint.server.analysisQueue.register_finish_callback(self._on_analysis)
        self.renderJobs = Queue.Queue()
        self.queueLock = threading.Lock()
        self._start_render_thread()
        
    def is_blueprint_protected(self):
        return False

    def _on_analysis(self, entry, result):
        print "G-Code preview render started"
        result["preview"] = "test123"
   
    def render_gcode_hook(self, path, file_object, links=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
        #TODO: Check if item is not already in queue
        #TODO: Better not have it during preprocessing (as it is executed before copying the file)
        #self.queueLock.acquire()
        #self.renderJobs.put({ "path": path, "filename": file_object.filename})
        #self._logger.info("Render job enqueued: %s" % file_object.filename)
        #self.queueLock.release()
        pass

    def render_gcode(self, path, filename):
        #TODO: Check if item is not already in queue
        self.queueLock.acquire()
        self.renderJobs.put({ "path": path, "filename": filename})
        self._logger.info("Render job enqueued: %s" % filename)
        self.queueLock.release()

    @octoprint.plugin.BlueprintPlugin.route("/previewstatus/<filename>/<make>", methods=["GET"])
    def previewstatus(self, filename, make):
        if not filename:
            response = make_response('Invalid filename', 400)
        else:
            self._logger.info("Retrieving preview info for %s" % filename)
            imagePath = self._get_imagepath(filename)
            if not imagePath:
                response = make_response(jsonify({ 'status': 'gcodenotfound'}), 200)
            elif os.path.exists(imagePath):
                self._logger.info("Returning %s" % imagePath)
                url = url_for('plugin.gcoderender.preview', filename = filename)
                response = make_response(jsonify({ 'status': 'ready', 'url' : url }), 200)
            else:
                if make:
                    gcodePath = os.path.join(self._settings.global_get_basefolder('uploads'), filename)
                    self.render_gcode(gcodePath, filename)
                    response = make_response(jsonify({ 'status': 'rendering'}), 200)
                else:
                    self._logger.info("Not found")
                    response = make_response(jsonify({ 'status': 'notfound'}), 200)

        return self._make_no_cache(response)

    @octoprint.plugin.BlueprintPlugin.route("/preview/<filename>", methods=["GET"])
    def preview(self, filename):
        if not filename:
            response = make_response('Invalid filename', 400)
        else:
            self._logger.info("Retrieving preview for %s" % filename)
            imagePath = self._get_imagepath(filename)
            if os.path.exists(imagePath):
                self._logger.info("Returning %s" % imagePath)
                response = send_file(imagePath)
            else:
                self._logger.info("Not found")
                response = make_response('No preview ready', 404)

        return self._make_no_cache(response)

    @octoprint.plugin.BlueprintPlugin.route("/allpreviews", methods=["GET"])
    def getAllPreviews(self):
        image_folder = self._get_image_folder()
        entries = os.listdir(image_folder)
        previews = []
        for entry in entries:
            name, _ = os.path.splitext(entry)
            previews.append("%s.gcode" % name)

        response = make_response(jsonify({ "previews" : previews }))

        return self._make_no_cache(response)
        

    def _start_render_thread(self):
        # TODO ensure a job isn't running twice simultaneously
        t = threading.Thread(target=self._render_gcode_watch)
        t.setDaemon(True)
        t.start()
        
    def _render_gcode_watch(self):
        if sys.platform == "win32" or sys.platform == "darwin":
            self.render = RendererWindows()
        else:
            self.render = RendererLinux()

        self.render.initialize(bedWidth = 365, bedDepth = 350, partColor = (67/255, 74/255, 84/255), bedColor = (0.75, 0.75, 0.75), width = 250, height = 250)
        
        while True:
            self.queueLock.acquire()
            if not self.renderJobs.empty():
                job = self.renderJobs.get()
                path, filename = job
                self._logger.info("Job found: %s" % job['filename'])
                self._render_gcode_worker(job['path'], job['filename'])
            self.queueLock.release()
            time.sleep(0.5) #TODO: find another way to reduce CPU

    def _render_gcode_worker(self, path, filename):
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
             return

        if not os.path.exists(path):
            return

        self._send_client_message("gcode_preview_rendering", { 
                                            "filename":  filename
                                            })

        imagePath = self._get_imagepath(filename)
       
        self._logger.info("Image path: {}".format(imagePath))
        
        self.render.renderModel(path, True)
        self.render.save(imagePath)
        #render.close()

        self._logger.info("Render complete")
        # Threading issues: url_for('plugin.gcoderender.preview', filename = filename)
        url = '/plugin/gcoderender/preview/%s' % filename
         
        self._send_client_message("gcode_preview_ready", { 
                                                            "filename":  filename,
                                                            "url": url
                                                            })


   

    def _make_no_cache(self, response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    def _get_image_folder(self):
        return self._settings.get_plugin_data_folder()

    def _get_imagepath(self, filename):
        name, _ = os.path.splitext(filename)

        images_folder = self._get_image_folder()
        
        if sys.platform == "win32":
            imagePath = os.path.join(images_folder, "%s.bmp" % name)
        else:
            imagePath = os.path.join(images_folder, "%s.png" % name)

        return imagePath
    
    def _send_client_message(self, message_type, data=None):
        self._logger.debug("Sending client message with type: {type}, and data: {data}".format(type=message_type, data=data))
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=message_type, data=data))
