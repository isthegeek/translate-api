import logging
import argparse
import base64
import json
import subprocess
import os

from flask import Flask, render_template, request
from werkzeug import secure_filename
from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
from pydub import AudioSegment

DISCOVERY_URL = ('https://{api}.googleapis.com/$discovery/rest?'
                 'version={apiVersion}')
app = Flask(__name__)

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = 'uploads/'
# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['wav'])

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('main_input_form.html')


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

@app.route('/submitted', methods=['POST'])
def main_input_form_submit():
    file = request.files['file']
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # Move the file form the temporal folder to
        # the upload folder we setup
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Redirect the user to the uploaded_file route, which
        # will basicaly show on the browser the uploaded file
        s = ['sox', '-v 0.98', 'uploads/'+filename, '--rate', '16k', '--bits','16', '--channels','1', 'audio.raw']
        subprocess.call(s)
        #subprocess.call(['sox -v 0.98', "uploads/" + filename ,''], shell=True)
        with open("audio.raw", 'rb') as speech:
            speech_content = base64.b64encode(speech.read())
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)
        service = discovery.build(
            'speech', 'v1beta1', http=http, discoveryServiceUrl=DISCOVERY_URL)
        service_request = service.speech().syncrecognize(
            body={
                'config': {
                    'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                    'sampleRate': 16000,  # 16 khz
                    'languageCode': 'en-US',  # a BCP-47 language tag
                },
                'audio': {
                    'content': speech_content.decode('UTF-8')
                    }
                })
        response = service_request.execute()
        print response
        return render_template(
          'main_input_form_submit.html',
          response=response)

if __name__ == "__main__":
    app.run(port=5003)
