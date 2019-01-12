#!/usr/bin/python

import sys
import socket
import time
import subprocess
import os

HOST = ''   # hostname
PORT = 15047    # port
MAX_REQUESTS = 1    # maximum number of requests to listen for
MAX_INCOMING_BYTES = 4096   # maximum amount of data in bytes
server_address = (HOST, PORT)

# initialize the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    print('\nInitializing test server on address <HOST, PORT>:')
    print(server_address)
    print

    # bind initialized server socket to server address
    server_socket.bind(server_address)
except Exception as e:
    print('Failed to bind socket, try again after system exits :)...\n')
    sys.exit(1)

while True:
    validCgi = True
    uri = ''
    stdout = ''

    print('Awaiting New Connection...\n')

    # listen for incoming connections infinitely and accept incoming requests
    server_socket.listen(MAX_REQUESTS)
    socket_to_client, client_address = server_socket.accept()

    print('Socket to client was opened at address <HOST, PORT>:')
    print(client_address)
    print

    # receive incoming data from client and decode the stream of incoming data bytes
    incoming_data = socket_to_client.recv(MAX_INCOMING_BYTES)
    request = bytes.decode(incoming_data)

    # get the request method from the client's request
    request_method = request.split(' ')[0]

    if(request_method == 'GET') or (request_method == 'POST'):
        # get the webpage and uri from the request
        webpage = request.split(' ')
        webpage = webpage[1]

        input_line = webpage.split('?')
        webpage = input_line[0]
            
        # default page is index.html, remove the leading forward-slash
        if webpage == '/':
            webpage = '/index.html'
        webpage = webpage.strip('/')

        try:
            # read the contents of the requested webpage
            webpage_handle = open(webpage, 'rb')
            response = webpage_handle.read()
            webpage_handle.close()
        
            # set the header
            response_header = 'HTTP/1.1 200 OK\n'
        except Exception as e:
            # handle an I/O Exception that is thrown if the file can't be opened
            print('Error 404.. File not found.\n')
            validCgi = False
            response_header = 'HTTP/1.1 404 Not Found\n'
            response = "<html><body><p>Error 404: FILE NOT FOUND</p></body></html>"


        # set the rest of the header
        date = time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())
        response_header += 'Date: ' + date + '\n'
        response_header += "Server: CJ's-Test-Server\n"

        # if the webpage is a valid cgi script...
        if webpage.endswith('.cgi') and validCgi == True:

            if request_method == 'GET':
                # set the query string environ var to the uri in the parent process
                # subProcess (fork) call to run cgi script in the child process, get the output from the call as stdout
                if len(input_line) > 1:
                    uri = input_line[1]
                    os.environ['QUERY_STRING'] = uri
                p = subprocess.Popen(webpage, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            elif request_method == 'POST':
                # parse the request and set the content length environ var, get the uri from the last line of the request
                # echo the last line to the stdin of the subProcess call, get the output from the call as stdout
                request_body = request.split('\n')
                os.environ['CONTENT_LENGTH'] = request_body[3].split(':')[1].strip()
                last_line = request_body[len(request_body) - 1].strip()
                stdin_str = subprocess.Popen(['echo', last_line], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                p = subprocess.Popen(webpage, stdin=stdin_str.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # get the output of the run and the errors if any
            (stdout, stderr) = p.communicate()

            # if its a cgi script, empty the response and process the stdout
            response = ''
            set_cookie = ''
            stdout = stdout.split('\n')

            # get the content type and set cookie from the stdout and add to the header
            content_type = stdout[0]
            if len(stdout) > 1:
                set_cookie = stdout[1]

            if content_type is not '':
                content_type += '\n'
                response_header += content_type

            if set_cookie is not '':
                set_cookie += '\n'
                response_header += set_cookie
                # add the cookie to the http cookie environ var
                os.environ['HTTP_COOKIE'] = set_cookie.split(':')[1].strip()

            # build the rest of the response from the stdout
            stdout = stdout[2:]
            for line in stdout:
                response += line

        # finish building the header, encode it and build the server response with it
        response_header += 'Connection: close\n\n'
        server_response = response_header.encode()
        server_response += response

        # send the response to the client and close the connection
        socket_to_client.send(server_response)
        print('Closing socket to client...\n')
        socket_to_client.close()
    else:
        print('Unkown HTTP request method: ', request_method)
